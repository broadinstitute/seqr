
import copy
import json
import logging
import redis
import sys

from xbrowse.core.constants import GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38, ANNOTATION_GROUPS_MAP, \
    ANNOTATION_GROUPS_MAP_INTERNAL
from xbrowse.core.genomeloc import get_chr_pos
import settings
import time

from xbrowse import genomeloc
from xbrowse.core.variant_filters import VariantFilter
from xbrowse import Variant

import datastore
from pprint import pformat

import elasticsearch
import elasticsearch_dsl
from elasticsearch_dsl import Q

from xbrowse.utils.basic_utils import _encode_name

logger = logging.getLogger()

GENOTYPE_QUERY_MAP = {

    'ref_ref': 0,
    'ref_alt': 1,
    'alt_alt': 2,

    'has_alt': {'$gte': 1},
    'has_ref': {'$in': [0,1]},

    'not_missing': {'$gte': 0},
    'missing': -1,
}


# TODO move these to a different module
polyphen_map = {
    'D': 'probably_damaging',
    'P': 'possibly_damaging',
    'B': 'benign',
    '.': None,
    '': None
}

sift_map = {
    'D': 'damaging',
    'T': 'tolerated',
    '.': None,
    '': None
}

fathmm_map = {
    'D': 'damaging',
    'T': 'tolerated',
    '.': None,
    '': None
}

muttaster_map = {
    'A': 'disease_causing',
    'D': 'disease_causing',
    'N': 'polymorphism',
    'P': 'polymorphism',
    '.': None,
    '': None
}

def _add_genotype_filter_to_variant_query(db_query, genotype_filter):
    """
    Add conditions to db_query from the genotype filter
    Edits in place, returns True if successful
    """
    for indiv_id, genotype in genotype_filter.items():
        key = 'genotypes.%s.num_alt' % indiv_id
        db_query[key] = GENOTYPE_QUERY_MAP[genotype]
    return True


def _add_index_fields_to_variant(variant_dict, annotation=None):
    """
    Add fields to the vairant dictionary that you want to index on before load it
    """
    if annotation:
        variant_dict['db_freqs'] = annotation['freqs']
        variant_dict['db_tags'] = annotation['annotation_tags']
        variant_dict['db_gene_ids'] = annotation['gene_ids']


class ElasticsearchDatastore(datastore.Datastore):

    def __init__(self, annotator):
        self.liftover_grch38_to_grch37 = None
        self.liftover_grch37_to_grch38 = None

        self._annotator = annotator

        self._es_client = elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME)

        self._redis_client = None
        if settings.REDIS_SERVICE_HOSTNAME:
            try:
                self._redis_client = redis.StrictRedis(host=settings.REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
                self._redis_client.ping()
            except redis.exceptions.TimeoutError as e:
                logger.warn("Unable to connect to redis: " + str(e))
                self._redis_client = None
            
    def get_elasticsearch_variants(
            self,
            project_id,
            family_id=None,
            variant_filter=None,
            genotype_filter=None,
            variant_id_filter=None,
            quality_filter=None,
            indivs_to_consider=None,
            include_all_consequences=False,
            user=None,
            max_results_limit=settings.VARIANT_QUERY_RESULTS_LIMIT,
        ):
        from xbrowse_server.base.models import Individual
        from xbrowse_server.mall import get_reference

        cache_key = "%s___%s___%s" % (
            project_id,
            family_id,
            json.dumps([
                variant_filter.toJSON() if variant_filter else None,
                genotype_filter,
                quality_filter,
                variant_id_filter,
                indivs_to_consider,
                include_all_consequences,
            ])
        )

        cached_results = self._redis_client and self._redis_client.get(cache_key)
        if cached_results is not None:
            variant_results = json.loads(cached_results)
            return [Variant.fromJSON(variant_json) for variant_json in variant_results]

        if indivs_to_consider is None:
            if genotype_filter:
                indivs_to_consider = genotype_filter.keys()
            else:
                indivs_to_consider = []

        if family_id is not None:
            family_individual_ids = [i.indiv_id for i in Individual.objects.filter(family__family_id=family_id).only("indiv_id")]
        else:
            family_individual_ids = [i.indiv_id for i in Individual.objects.filter(family__project__project_id=project_id).only("indiv_id")]

        from xbrowse_server.base.models import Project, Family
        from pyliftover import LiftOver

        query_json = self._make_db_query(genotype_filter, variant_filter)

        try:
            if self.liftover_grch38_to_grch37 is None:
                self.liftover_grch38_to_grch37 = LiftOver('hg38', 'hg19')

            if self.liftover_grch37_to_grch38 is None:
                self.liftover_grch37_to_grch38 = None # LiftOver('hg19', 'hg38')
        except Exception as e:
            logger.info("WARNING: Unable to set up liftover. Is there a working internet connection? " + str(e))

        if family_id is None:
            project = Project.objects.get(project_id=project_id)
            elasticsearch_index = project.get_elasticsearch_index()
            logger.info("Searching in project elasticsearch index: " + str(elasticsearch_index))
        else:
            family = Family.objects.get(project__project_id=project_id, family_id=family_id)
            elasticsearch_index = family.get_elasticsearch_index()
            project = family.project
            logger.info("Searching in family elasticsearch index: " + str(elasticsearch_index))

        if family_id is not None and len(family_individual_ids) > 0:
            # figure out which index to use
            # TODO add caching
            matching_indices = []
            mapping = self._es_client.indices.get_mapping(str(elasticsearch_index)+"*")

            if family_individual_ids:
                indiv_id = _encode_name(family_individual_ids[0])
                for index_name, index_mapping in mapping.items():
                    if indiv_id+"_num_alt" in index_mapping["mappings"]["variant"]["properties"]:
                        matching_indices.append(index_name)

            if not matching_indices:
                if not family_individual_ids:
                    logger.error("no individuals found for family %s" % (family_id))
                elif not mapping:
                    logger.error("no es mapping found for found with prefix %s" % (elasticsearch_index))
                else:
                    logger.error("%s not found in %s:\n%s" % (indiv_id, elasticsearch_index, pformat(index_mapping["mappings"]["variant"]["properties"])))
            else:
                logger.info("matching indices: " + str(elasticsearch_index))
                elasticsearch_index = ",".join(matching_indices)

        s = elasticsearch_dsl.Search(using=self._es_client, index=str(elasticsearch_index)+"*") #",".join(indices))

        if variant_id_filter is not None:
            variant_id_filter_term = None
            for variant_id in variant_id_filter:
                q_obj = Q('term', **{"variantId": variant_id})
                if variant_id_filter_term is None:
                    variant_id_filter_term = q_obj
                else:
                    variant_id_filter_term |= q_obj
            s = s.filter(variant_id_filter_term)

        if indivs_to_consider:
            atleast_one_nonref_genotype_filter = None
            for sample_id in indivs_to_consider:
                encoded_sample_id = _encode_name(sample_id)
                q = Q('range', **{encoded_sample_id+"_num_alt": {'gte': 1}})
                if atleast_one_nonref_genotype_filter is None:
                    atleast_one_nonref_genotype_filter = q
                else:
                    atleast_one_nonref_genotype_filter |= q

            s = s.filter(atleast_one_nonref_genotype_filter)

        if quality_filter is not None and indivs_to_consider:
            #'vcf_filter': u'pass', u'min_ab': 17, u'min_gq': 46
            min_ab = quality_filter.get('min_ab')
            if min_ab is not None:
                min_ab /= 100.0   # convert to fraction
            min_gq = quality_filter.get('min_gq')
            vcf_filter = quality_filter.get('vcf_filter')
            for sample_id in indivs_to_consider:
                encoded_sample_id = _encode_name(sample_id)

                #'vcf_filter': u'pass', u'min_ab': 17, u'min_gq': 46
                if min_ab:
                    s = s.filter(
                        ~Q('term', **{encoded_sample_id+"_num_alt": 1}) |
                        Q('range', **{encoded_sample_id+"_ab": {'gte': min_ab}}))
                    #logger.info("### ADDED FILTER: " + str({encoded_sample_id+"_ab": {'gte': min_ab}}))
                if min_gq:
                    s = s.filter('range', **{encoded_sample_id+"_gq": {'gte': min_gq}})
                    #logger.info("### ADDED FILTER: " + str({encoded_sample_id+"_gq": {'gte': min_gq}}))
                if vcf_filter is not None:
                    s = s.filter(~Q('exists', field='filters'))
                    #logger.info("### ADDED FILTER: " + str(~Q('exists', field='filters')))

        # parse variant query
        annotation_groups_map = ANNOTATION_GROUPS_MAP_INTERNAL if user and user.is_staff else ANNOTATION_GROUPS_MAP

        for key, value in query_json.items():
            if key == 'db_tags':
                so_annotations = query_json.get('db_tags', {}).get('$in', [])

                # handle clinvar filters
                selected_so_annotations_set = set(so_annotations)

                all_clinvar_filters_set = set(annotation_groups_map.get("clinvar", {}).get("children", []))
                selected_clinvar_filters_set = all_clinvar_filters_set & selected_so_annotations_set

                all_hgmd_filters_set = set(annotation_groups_map.get("hgmd", {}).get("children", []))
                selected_hgmd_filters_set = all_hgmd_filters_set & selected_so_annotations_set

                vep_consequences = list(selected_so_annotations_set - selected_clinvar_filters_set - selected_hgmd_filters_set)
                consequences_filter = Q("terms", transcriptConsequenceTerms=vep_consequences)

                if selected_clinvar_filters_set:
                    clinvar_clinical_significance_terms = set()
                    for clinvar_filter in selected_clinvar_filters_set:
                        # translate selected filters to the corresponding clinvar clinical consequence terms
                        if clinvar_filter == "pathogenic":
                            clinvar_clinical_significance_terms.update(["Pathogenic", "Pathogenic/Likely_pathogenic"])
                        elif clinvar_filter == "likely_pathogenic":
                            clinvar_clinical_significance_terms.update(["Likely_pathogenic", "Pathogenic/Likely_pathogenic"])
                        elif clinvar_filter == "benign":
                            clinvar_clinical_significance_terms.update(["Benign", "Benign/Likely_benign"])
                        elif clinvar_filter == "likely_benign":
                            clinvar_clinical_significance_terms.update(["Likely_benign", "Benign/Likely_benign"])
                        elif clinvar_filter == "vus_or_conflicting":
                            clinvar_clinical_significance_terms.update([
                                "Conflicting_interpretations_of_pathogenicity",
                                "Uncertain_significance",
                                "not_provided",
                                "other"])
                        else:
                            raise ValueError("Unexpected clinvar filter: " + str(clinvar_filter))

                    consequences_filter = consequences_filter | Q("terms", clinvar_clinical_significance=list(clinvar_clinical_significance_terms))

                if selected_hgmd_filters_set:
                    hgmd_class = set()
                    for hgmd_filter in selected_hgmd_filters_set:
                        # translate selected filters to the corresponding hgmd clinical consequence terms
                        if hgmd_filter == "disease_causing":
                            hgmd_class.update(["DM"])
                        elif hgmd_filter == "likely_disease_causing":
                            hgmd_class.update(["DM?"])
                        elif hgmd_filter == "hgmd_other":
                            hgmd_class.update(["DP", "DFP", "FP", "FTV"])
                        else:
                            raise ValueError("Unexpected hgmd filter: " + str(hgmd_filter))

                    consequences_filter = consequences_filter | Q("terms", hgmd_class=list(hgmd_class))

                if 'intergenic_variant' in vep_consequences:
                    # for many intergenic variants VEP doesn't add any annotations, so if user selected 'intergenic_variant', also match variants where transcriptConsequenceTerms is emtpy
                    consequences_filter = consequences_filter | ~Q('exists', field='transcriptConsequenceTerms')

                s = s.filter(consequences_filter)
                #logger.info("==> transcriptConsequenceTerms: %s" % str(vep_consequences))

            if key.startswith("genotypes"):
                sample_id = ".".join(key.split(".")[1:-1])
                encoded_sample_id = _encode_name(sample_id)
                genotype_filter = value
                #logger.info("==> genotype filter: " + str(genotype_filter))
                if type(genotype_filter) == int or type(genotype_filter) == basestring:
                    #logger.info("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": genotype_filter}))
                    s = s.filter('term', **{encoded_sample_id+"_num_alt": genotype_filter})

                elif '$gte' in genotype_filter:
                    genotype_filter = {k.replace("$", ""): v for k, v in genotype_filter.items()}
                    s = s.filter('range', **{encoded_sample_id+"_num_alt": genotype_filter})
                    #logger.info("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": genotype_filter}))
                elif "$in" in genotype_filter:
                    num_alt_values = genotype_filter['$in']
                    q = Q('term', **{encoded_sample_id+"_num_alt": num_alt_values[0]})
                    #logger.info("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": num_alt_values[0]}))
                    for num_alt_value in num_alt_values[1:]:
                        q = q | Q('term', **{encoded_sample_id+"_num_alt": num_alt_value})
                        #logger.info("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": num_alt_value}))
                    s = s.filter(q)

            if key == "db_gene_ids":
                db_gene_ids = query_json.get('db_gene_ids', {})

                exclude_genes = db_gene_ids.get('$nin', [])
                gene_ids = exclude_genes or db_gene_ids.get('$in', [])

                if exclude_genes:
                    s = s.exclude("terms", geneIds=gene_ids)
                else:
                    s = s.filter("terms",  geneIds=gene_ids)
                #logger.info("==> %s %s" % ("exclude" if exclude_genes else "include", "geneIds: " + str(gene_ids)))

            if key == "$or" and type(value) == list:
                q_terms = None
                for region_filter in value:
                    xpos_filters = region_filter.get("$and", {})

                    # for example: $or : [{'$and': [{'xpos': {'$gte': 12345}}, {'xpos': {'$lte': 54321}}]}]
                    xpos_filters_dict = {}
                    for xpos_filter in xpos_filters:
                        xpos_filter_setting = xpos_filter["xpos"]  # for example {'$gte': 12345} or {'$lte': 54321}
                        xpos_filters_dict.update(xpos_filter_setting)

                    xpos_filter_setting = {k.replace("$", ""): v for k, v in xpos_filters_dict.items()}
                    q = Q('range', **{"xpos": xpos_filter_setting})
                    if q_terms is None:
                        q_terms = q
                    else:
                        q_terms |= q
                if q_terms is not None:
                    s = s.filter(q_terms)

                #logger.info("==> xpos range: " + str({"xpos": xpos_filter_setting}))

            af_key_map = {
                "db_freqs.AF": "AF",
                "db_freqs.1kg_wgs_phase3": "g1k_POPMAX_AF",
                "db_freqs.exac_v3": "exac_AF_POPMAX",
                "db_freqs.topmed": "topmed_AF",
                "db_freqs.gnomad_exomes": "gnomad_exomes_AF_POPMAX",
                "db_freqs.gnomad_genomes": "gnomad_genomes_AF_POPMAX",
                "db_freqs.gnomad-exomes2": "gnomad_exomes_AF_POPMAX",
                "db_freqs.gnomad-genomes2": "gnomad_genomes_AF_POPMAX",
            }

            if key in af_key_map:
                filter_key = af_key_map[key]
                af_filter_setting = {k.replace("$", ""): v for k, v in value.items()}
                s = s.filter(Q('range', **{filter_key: af_filter_setting}) | ~Q('exists', field=filter_key))
                #logger.info("==> %s: %s" % (filter_key, af_filter_setting))

            ac_key_map = {
                "db_acs.AF": "AC",
                "db_acs.1kg_wgs_phase3": "g1k_AC",
                "db_acs.exac_v3": "exac_AC",
                "db_acs.topmed": "topmed_AC",
                "db_acs.gnomad_exomes": "gnomad_exomes_AC",
                "db_acs.gnomad_genomes": "gnomad_genomes_AC",
                "db_acs.gnomad-exomes2": "gnomad_exomes_AC",
                "db_acs.gnomad-genomes2": "gnomad_genomes_AC",
            }

            if key in ac_key_map:
                filter_key = ac_key_map[key]
                ac_filter_setting = {k.replace("$", ""): v for k, v in value.items()}
                s = s.filter(Q('range', **{filter_key: ac_filter_setting}) | ~Q('exists', field=filter_key))

            hemi_key_map = {
                "db_hemi.exac_v3": "exac_AC_Hemi",
                "db_hemi.gnomad_exomes": "gnomad_exomes_Hemi",
                "db_hemi.gnomad_genomes": "gnomad_genomes_Hemi",
                "db_hemi.gnomad-exomes2": "gnomad_exomes_Hemi",
                "db_hemi.gnomad-genomes2": "gnomad_genomes_Hemi",
            }

            if key in hemi_key_map:
                filter_key = hemi_key_map[key]
                hemi_filter_setting = {k.replace("$", ""): v for k, v in value.items()}
                s = s.filter(Q('range', **{filter_key: hemi_filter_setting}) | ~Q('exists', field=filter_key))

            hom_key_map = {
                "db_hom.exac_v3": "exac_AC_Hom",
                "db_hom.gnomad_exomes": "gnomad_exomes_Hom",
                "db_hom.gnomad_genomes": "gnomad_genomes_Hom",
                "db_hom.gnomad-exomes2": "gnomad_exomes_Hom",
                "db_hom.gnomad-genomes2": "gnomad_genomes_Hom",
            }

            if key in hom_key_map:
                filter_key = hom_key_map[key]
                hom_filter_setting = {k.replace("$", ""): v for k, v in value.items()}
                s = s.filter(Q('range', **{filter_key: hom_filter_setting}) | ~Q('exists', field=filter_key))

            #s = s.sort("xpos")

        #logger.info("=====")
        #logger.info("FULL QUERY OBJ: " + pformat(s.__dict__))
        #logger.info("FILTERS: " + pformat(s.to_dict()))

        # https://elasticsearch-py.readthedocs.io/en/master/helpers.html#elasticsearch.helpers.scan
        start = time.time()

        s = s.params(size=max_results_limit + 1)
        #if not include_all_consequences:
        #    s = s.source(exclude=["sortedTranscriptConsequences"])
        response = s.execute()
        logger.info("=====")

        logger.info("TOTAL: %s. Query took %s seconds" % (response.hits.total, time.time() - start))

        if response.hits.total > max_results_limit + 1:
            raise Exception("This search matched too many variants. Please set additional filters and try again.")

        #print(pformat(response.to_dict()))

        project = Project.objects.get(project_id=project_id)

        #gene_list_map = project.get_gene_list_map()

        reference = get_reference()

        #for i, hit in enumerate(response.hits):
        variant_results = []
        for i, hit in enumerate(s.scan()):  # preserve_order=True
            #logger.info("HIT %s: %s %s %s" % (i, hit["variantId"], hit["geneIds"], pformat(hit.__dict__)))
            #print("HIT %s: %s" % (i, pformat(hit.to_dict())))
            filters = ",".join(hit["filters"] or []) if "filters" in hit else ""
            genotypes = {}
            all_num_alt = []
            for individual_id in family_individual_ids:
                encoded_individual_id = _encode_name(individual_id)
                num_alt = int(hit["%s_num_alt" % encoded_individual_id]) if ("%s_num_alt" % encoded_individual_id) in hit else -1
                if num_alt is not None:
                    all_num_alt.append(num_alt)

                alleles = []
                if num_alt == 0:
                    alleles = [hit["ref"], hit["ref"]]
                elif num_alt == 1:
                    alleles = [hit["ref"], hit["alt"]]
                elif num_alt == 2:
                    alleles = [hit["alt"], hit["alt"]]
                elif num_alt == -1 or num_alt == None:
                    alleles = []
                else:
                    raise ValueError("Invalid num_alt: " + str(num_alt))

                genotypes[individual_id] = {
                    'ab': hit["%s_ab" % encoded_individual_id] if ("%s_ab" % encoded_individual_id) in hit else None,
                    'alleles': map(str, alleles),
                    'extras': {
                        'ad': hit["%s_ab" % encoded_individual_id] if ("%s_ad" % encoded_individual_id) in hit else None,
                        'dp': hit["%s_dp" % encoded_individual_id] if ("%s_dp" % encoded_individual_id) in hit else None,
                        #'pl': '',
                    },
                    'filter': filters or "pass",
                    'gq': hit["%s_gq" % encoded_individual_id] if ("%s_gq" % encoded_individual_id in hit and hit["%s_gq" % encoded_individual_id] is not None) else '',
                    'num_alt': num_alt,
                }

            if all([num_alt <= 0 for num_alt in all_num_alt]):
                #logger.info("Filtered out due to genotype: " + str(genotypes))
                #print("Filtered all_num_alt <= 0 - Result %s: GRCh38: %s:%s,  cadd: %s  %s - %s" % (i, hit["contig"], hit["start"], hit["cadd_PHRED"] if "cadd_PHRED" in hit else "", hit["transcriptConsequenceTerms"], all_num_alt))
                continue

            vep_annotation = json.loads(str(hit['sortedTranscriptConsequences'])) if 'sortedTranscriptConsequences' in hit else None

            if project.genome_version == GENOME_VERSION_GRCh37:
                grch38_coord = None
                if self.liftover_grch37_to_grch38:
                    grch38_coord = self.liftover_grch37_to_grch38.convert_coordinate("chr%s" % hit["contig"].replace("chr", ""), int(hit["start"]))
                    if grch38_coord and grch38_coord[0]:
                        grch38_coord = "%s-%s-%s-%s "% (grch38_coord[0][0], grch38_coord[0][1], hit["ref"], hit["alt"])
                    else:
                        grch38_coord = None
            else:
                grch38_coord = hit["variantId"]

            if project.genome_version == GENOME_VERSION_GRCh38:
                grch37_coord = None
                if self.liftover_grch38_to_grch37:
                    grch37_coord = self.liftover_grch38_to_grch37.convert_coordinate("chr%s" % hit["contig"].replace("chr", ""), int(hit["start"]))
                    if grch37_coord and grch37_coord[0]:
                        grch37_coord = "%s-%s-%s-%s "% (grch37_coord[0][0], grch37_coord[0][1], hit["ref"], hit["alt"])
                    else:
                        grch37_coord = None
            else:
                grch37_coord = hit["variantId"]

            result = {
                #u'_id': ObjectId('596d2207ff66f729285ca588'),
                'alt': str(hit["alt"]) if "alt" in hit else None,
                'annotation': {
                    'fathmm': fathmm_map.get(hit["dbnsfp_FATHMM_pred"].split(';')[0]) if "dbnsfp_FATHMM_pred" in hit and hit["dbnsfp_FATHMM_pred"] else None,
                    'muttaster': muttaster_map.get(hit["dbnsfp_MutationTaster_pred"].split(';')[0]) if "dbnsfp_MutationTaster_pred" in hit and hit["dbnsfp_MutationTaster_pred"] else None,
                    'polyphen': polyphen_map.get(hit["dbnsfp_Polyphen2_HVAR_pred"].split(';')[0]) if "dbnsfp_Polyphen2_HVAR_pred" in hit and hit["dbnsfp_Polyphen2_HVAR_pred"] else None,
                    'sift': sift_map.get(hit["dbnsfp_SIFT_pred"].split(';')[0]) if "dbnsfp_SIFT_pred" in hit and hit["dbnsfp_SIFT_pred"] else None,

                    'GERP_RS': hit["dbnsfp_GERP_RS"] if "dbnsfp_GERP_RS" in hit else None,
                    'phastCons100way_vertebrate': hit["dbnsfp_phastCons100way_vertebrate"] if "dbnsfp_phastCons100way_vertebrate" in hit else None,

                    'cadd_phred': hit["cadd_PHRED"] if "cadd_PHRED" in hit else None,
                    'dann_score': hit["dbnsfp_DANN_score"] if "dbnsfp_DANN_score" in hit else None,
                    'revel_score': hit["dbnsfp_REVEL_score"] if "dbnsfp_REVEL_score" in hit else None,
                    'eigen_phred': hit["eigen_Eigen_phred"] if "eigen_Eigen_phred" in hit else (hit["dbnsfp_Eigen_phred"] if "dbnsfp_Eigen_phred" in hit else None),
                    'mpc_score': hit["mpc_MPC"] if "mpc_MPC" in hit else None,

                    'annotation_tags': list(hit["transcriptConsequenceTerms"] or []) if "transcriptConsequenceTerms" in hit else None,
                    'coding_gene_ids': list(hit['codingGeneIds'] or []),
                    'gene_ids': list(hit['geneIds'] or []),
                    'vep_annotation': vep_annotation,
                    'vep_group': str(hit['mainTranscript_major_consequence'] or ""),
                    'vep_consequence': str(hit['mainTranscript_major_consequence'] or ""),
                    'main_transcript': {k.replace('mainTranscript_', ''): hit[k] for k in dir(hit) if k.startswith('mainTranscript_')},
                    'worst_vep_annotation_index': 0,
                    'worst_vep_index_per_gene': {str(hit['mainTranscript_gene_id']): 0},
                },
                'chr': hit["contig"],
                'coding_gene_ids': list(hit['codingGeneIds'] or []),
                'gene_ids': list(hit['geneIds'] or []),
                'coverage': {
                    'gnomad_exome_coverage': float(hit["gnomad_exome_coverage"] or -1) if "gnomad_exome_coverage" in hit else -1,
                    'gnomad_genome_coverage': float(hit["gnomad_genome_coverage"] or -1) if "gnomad_genome_coverage" in hit else -1,
                },
                'pop_counts': {
                    'AC': int(hit['AC'] or 0) if 'AC' in hit else None,
                    'AN': int(hit['AN'] or 0) if 'AN' in hit else None,

                    '1kg_AC': int(hit['g1k_AC'] or 0) if 'g1k_AC' in hit else None,
                    '1kg_AN': int(hit['g1k_AN'] or 0) if 'g1k_AN' in hit else None,

                    'exac_v3_AC': int(hit["exac_AC_Adj"] or 0) if "exac_Adj_AC" in hit else None,
                    'exac_v3_Het': int(hit["exac_AC_Het"] or 0) if "exac_AC_Het" in hit else None,
                    'exac_v3_Hom': int(hit["exac_AC_Hom"] or 0) if "exac_AC_Hom" in hit else None,
                    'exac_v3_Hemi': int(hit["exac_AC_Hemi"] or 0) if "exac_AC_Hemi" in hit else None,

                    'gnomad_exomes_AC': int(hit["gnomad_exomes_AC"] or 0) if "gnomad_exomes_AC" in hit else None,
                    'gnomad_exomes_Hom': int(hit["gnomad_exomes_Hom"] or 0) if "gnomad_exomes_Hom" in hit else None,
                    'gnomad_exomes_Hemi': int(hit["gnomad_exomes_Hemi"] or 0) if "gnomad_exomes_Hemi" in hit else None,
                    'gnomad_exomes_AN': int(hit["gnomad_exomes_AN"] or 0) if "gnomad_exomes_AN" in hit else None,

                    'gnomad_genomes_AC': int(hit["gnomad_genomes_AC"] or 0) if "gnomad_genomes_AC" in hit else None,
                    'gnomad_genomes_Hom': int(hit["gnomad_genomes_Hom"] or 0) if "gnomad_genomes_Hom" in hit else None,
                    'gnomad_genomes_Hemi': int(hit["gnomad_genomes_Hemi"] or 0) if "gnomad_genomes_Hemi" in hit else None,
                    'gnomad_genomes_AN': int(hit["gnomad_genomes_AN"] or 0) if "gnomad_genomes_AN" in hit else None,

                    'topmed_AC': float(hit["topmed_AC"] or 0) if "topmed_AC" in hit else None,
                    'topmed_Het': float(hit["topmed_Het"] or 0) if "topmed_Het" in hit else None,
                    'topmed_Hom': float(hit["topmed_Hom"] or 0) if "topmed_Hom" in hit else None,
                    'topmed_AN': float(hit["topmed_AN"] or 0) if "topmed_AN" in hit else None,
                },
                'db_freqs': {
                    'AF': float(hit["AF"] or 0.0) if "AF" in hit else None,
                    '1kg_wgs_AF': float(hit["g1k_AF"] or 0.0) if "g1k_AF" in hit else None,
                    '1kg_wgs_popmax_AF': float(hit["g1k_POPMAX_AF"] or 0.0) if "g1k_POPMAX_AF" in hit else None,
                    'exac_v3_AF': float(hit["exac_AF"] or 0.0) if "exac_AF" in hit else (hit["exac_AC_Adj"]/float(hit["exac_AN_Adj"]) if "exac_AC_Adj" in hit and "exac_AN_Adj"in hit and int(hit["exac_AN_Adj"] or 0) > 0 else None),
                    'exac_v3_popmax_AF': float(hit["exac_AF_POPMAX"] or 0.0) if "exac_AF_POPMAX" in hit else None,
                    'gnomad_exomes_AF': float(hit["gnomad_exomes_AF"] or 0.0) if "gnomad_exomes_AF" in hit else None,
                    'gnomad_exomes_popmax_AF': float(hit["gnomad_exomes_AF_POPMAX"] or 0.0) if "gnomad_exomes_AF_POPMAX" in hit else None,
                    'gnomad_genomes_AF': float(hit["gnomad_genomes_AF"] or 0.0) if "gnomad_genomes_AF" in hit else None,
                    'gnomad_genomes_popmax_AF': float(hit["gnomad_genomes_AF_POPMAX"] or 0.0) if "gnomad_genomes_AF_POPMAX" in hit else None,
                    'topmed_AF': float(hit["topmed_AF"] or 0.0) if "topmed_AF" in hit else None,
                },
                #'popmax_populations': {
                #    'exac_popmax': hit["exac_POPMAX"] or None,
                #    'gnomad_exomes_popmax': hit["gnomad_exomes_POPMAX"] or None,
                #    'gnomad_genomes_popmax': hit["gnomad_genomes_POPMAX"] or None,
                #},
                'db_gene_ids': list((hit["geneIds"] or []) if "geneIds" in hit else []),
                'db_tags': str(hit["transcriptConsequenceTerms"] or "") if "transcriptConsequenceTerms" in hit else None,
                'extras': {
                    'clinvar_variant_id': hit['clinvar_variation_id'] if 'clinvar_variation_id' in hit and hit['clinvar_variation_id'] else None,
                    'clinvar_allele_id': hit['clinvar_allele_id'] if 'clinvar_allele_id' in hit and hit['clinvar_allele_id'] else None,
                    'clinvar_clinsig': hit['clinvar_clinical_significance'].lower() if ('clinvar_clinical_significance' in hit) and hit['clinvar_clinical_significance'] else None,
                    'hgmd_class': hit['hgmd_class'] if 'hgmd_class' in hit and user and user.is_staff else None,
                    'hgmd_accession': hit['hgmd_accession'] if 'hgmd_accession' in hit else None,
                    'genome_version': project.genome_version,
                    'grch37_coords': grch37_coord,
                    'grch38_coords': grch38_coord,
                    'alt_allele_pos': 0,
                    'orig_alt_alleles': map(str, [a.split("-")[-1] for a in hit["originalAltAlleles"]]) if "originalAltAlleles" in hit else None
                },
                'genotypes': genotypes,
                'pos': long(hit['start']),
                'pos_end': str(hit['end']),
                'ref': str(hit['ref']),
                'vartype': 'snp' if len(hit['ref']) == len(hit['alt']) else "indel",
                'vcf_id': None,
                'xpos': long(hit["xpos"]),
                'xposx': long(hit["xpos"]),
            }

            result["annotation"]["freqs"] = result["db_freqs"]
            result["annotation"]["pop_counts"] = result["pop_counts"]
            result["annotation"]["db"] = "elasticsearch"

            result["extras"]["svlen"] = hit["SVLEN"] if "SVLEN" in hit else None
            result["extras"]["svtype"] = hit["SVTYPE"] if "SVTYPE" in hit else None


            logger.info("Result %s: GRCh37: %s GRCh38: %s:,  cadd: %s  %s - gene ids: %s, coding gene_ids: %s" % (
                i, grch37_coord, grch38_coord,
                hit["cadd_PHRED"] if "cadd_PHRED" in hit else "",
                hit["transcriptConsequenceTerms"],
                result["gene_ids"],
                result["coding_gene_ids"]))

            result["extras"]["project_id"] = project_id
            result["extras"]["family_id"] = family_id

            # add gene info
            gene_names = {}
            if vep_annotation is not None:
                gene_names = {vep_anno["gene_id"]: vep_anno.get("gene_symbol") for vep_anno in vep_annotation if vep_anno.get("gene_symbol")}
            result["extras"]["gene_names"] = gene_names

            try:
                genes = {}
                for gene_id in result["coding_gene_ids"]:
                    if gene_id:
                        genes[gene_id] = reference.get_gene_summary(gene_id) or {}

                if not genes:
                    for gene_id in result["gene_ids"]:
                        if gene_id:
                            genes[gene_id] = reference.get_gene_summary(gene_id) or {}

                #if not genes:
                #    genes =  {vep_anno["gene_id"]: {"symbol": vep_anno["gene_symbol"]} for vep_anno in vep_annotation}

                result["extras"]["genes"] = genes
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.warn("WARNING: got unexpected error in add_gene_names_to_variants: %s : line %s" % (e, exc_tb.tb_lineno))

            variant_results.append(result)

        logger.info("Finished returning the %s variants: %s seconds" % (response.hits.total, time.time() - start))

        if self._redis_client:
            self._redis_client.set(cache_key, json.dumps(variant_results))

        return [Variant.fromJSON(variant_json) for variant_json in variant_results]

    def get_variants(self, project_id, family_id, genotype_filter=None, variant_filter=None, quality_filter=None, indivs_to_consider=None, user=None):
        for variant in self.get_elasticsearch_variants(
                project_id,
                family_id,
                variant_filter=variant_filter,
                genotype_filter=genotype_filter,
                quality_filter=quality_filter,
                indivs_to_consider=indivs_to_consider,
                user=user,
        ):

            yield variant

    def get_variants_in_gene(self, project_id, family_id, gene_id, genotype_filter=None, variant_filter=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)

        #db_query = self._make_db_query(genotype_filter, modified_variant_filter, user=None)
        raise ValueError("Not Implemented")

    def get_single_variant(self, project_id, family_id, xpos, ref, alt, user=None):
        chrom, pos = get_chr_pos(xpos)

        variant_id = "%s-%s-%s-%s" % (chrom, pos, ref, alt)
        results = list(self.get_elasticsearch_variants(project_id, family_id=family_id, variant_id_filter=[variant_id], user=user, include_all_consequences=True))

        if not results:
            return None

        if len(results) > 1:
            raise ValueError("Multiple variant records found for project: %s family: %s  %s-%s-%s-%s: \n %s" % (
                project_id, family_id, chrom, pos, ref, alt, "\n".join([pformat(v.toJSON()) for v in results])))

        variant = results[0]

        return variant

    def get_multiple_variants(self, project_id, family_id, xpos_ref_alt_tuples, user=None):
        """
        Get one or more specific variants in a family
        Variant should be identifiable by xpos, ref, and alt
        Note that ref and alt are just strings from the VCF (for now)
        """
        variant_ids = []
        for xpos, ref, alt in  xpos_ref_alt_tuples:
            chrom, pos = get_chr_pos(xpos)
            variant_ids.append("%s-%s-%s-%s" % (chrom, pos, ref, alt))


        results = self.get_elasticsearch_variants(project_id, family_id=family_id, variant_id_filter=variant_ids, user=user)
        # make sure all variants in xpos_ref_alt_tuples were retrieved and are in the same order.
        # Return None for tuples that weren't found in ES.
        results_by_xpos_ref_alt = {}
        for r in results:
            results_by_xpos_ref_alt[(r.xpos, r.ref, r.alt)] = r

        # create a list that's the same length as the input list of xpos_ref_alt_tuples, putting None for
        # xpos-ref-alt's that weren't found in the elasticsearch index
        results = [results_by_xpos_ref_alt.get(t) for t in xpos_ref_alt_tuples]

        return results

    def get_variants_cohort(self, project_id, cohort_id, variant_filter=None):

        raise ValueError("Not implemented")

    def get_single_variant_cohort(self, project_id, cohort_id, xpos, ref, alt):

        raise ValueError("Not implemented")

    def get_project_variants_in_gene(self, project_id, gene_id, variant_filter=None, user=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)

        variants = [variant for variant in self.get_elasticsearch_variants(project_id, variant_filter=modified_variant_filter, user=user, max_results_limit=9999)]
        return variants

    def _make_db_query(self, genotype_filter=None, variant_filter=None):
        """
        Caller specifies filters to get_variants, but they are evaluated later.
        Here, we just inspect those filters and see what heuristics we can apply to avoid a full table scan,
        Query here must return a superset of the true get_variants results
        Note that the full annotation isn't stored, so use the fields added by _add_index_fields_to_variant
        """
        db_query = {}

        # genotype filter
        if genotype_filter is not None:
            _add_genotype_filter_to_variant_query(db_query, genotype_filter)

        if variant_filter:
            logger.info(pformat(variant_filter.toJSON()))

            if variant_filter.locations:
                location_ranges = []
                for i, location in enumerate(variant_filter.locations):
                    if isinstance(location, basestring):
                        chrom, pos_range = location.split(":")
                        start, end = pos_range.split("-")
                        xstart = genomeloc.get_xpos(chrom, int(start))
                        xend = genomeloc.get_xpos(chrom, int(end))
                        variant_filter.locations[i] = (xstart, xend)
                    else:
                        xstart, xend = location

                    location_ranges.append({'$and' : [ {'xpos' : {'$gte': xstart }}, {'xpos' : {'$lte': xend }}] })

                db_query['$or'] = location_ranges

            if variant_filter.so_annotations:
                db_query['db_tags'] = {'$in': variant_filter.so_annotations}
            if variant_filter.genes:
                if getattr(variant_filter, 'exclude_genes'):
                    db_query['db_gene_ids'] = {'$nin': variant_filter.genes}
                else:
                    db_query['db_gene_ids'] = {'$in': variant_filter.genes}
            if variant_filter.ref_freqs:
                for population, freq in variant_filter.ref_freqs:
                    #if population in self._annotator.reference_population_slugs:
                    db_query['db_freqs.' + population] = {'$lte': freq}
            if variant_filter.ref_acs:
                for population, ac in variant_filter.ref_acs:
                    db_query['db_acs.' + population] = {'$lte': ac}
            if variant_filter.ref_hom_hemi:
                for population, count in variant_filter.ref_hom_hemi:
                    db_query['db_hemi.' + population] = {'$lte': count}
                    db_query['db_hom.' + population] = {'$lte': count}

        return db_query

    def family_exists(self, project_id, family_id):
        from xbrowse_server.base.models import Family
        family = Family.objects.get(project__project_id=project_id, family_id=family_id)
        return family.has_variant_data()

    def get_family_status(self, project_id, family_id):
        if self.family_exists(project_id, family_id):
            return 'loaded'
        else:
            return 'not_loaded'

    def project_collection_is_loaded(self, project):
        """Returns true if the project collection is fully loaded (this is the
        collection that stores the project-wide set of variants used for gene
        search)."""

        return project.get_elasticsearch_index() is not None

