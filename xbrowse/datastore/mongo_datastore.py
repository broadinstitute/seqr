from collections import defaultdict, OrderedDict
import itertools
import json
import os
import sys
import random
import string
import copy
import sys
from datetime import date, datetime

import pysam
import pymongo
from xbrowse.utils import compressed_file, get_progressbar
from xbrowse.utils import slugify

from xbrowse import utils as xbrowse_utils
from xbrowse import vcf_stuff
from xbrowse.core.variant_filters import VariantFilter, passes_variant_filter
from xbrowse import Variant
import datastore
from pprint import pprint, pformat

import StringIO
import elasticsearch
import elasticsearch_dsl
from elasticsearch_dsl import Q

from pyliftover import LiftOver

liftover = LiftOver('hg38', 'hg19')


#ELASTICSEARCH_HOST="35.193.68.71"

#ELASTICSEARCH_HOST="104.155.188.102"

# make encoded values as human-readable as possible
ES_FIELD_NAME_ESCAPE_CHAR = '$'
ES_FIELD_NAME_BAD_LEADING_CHARS = set(['_', '-', '+', ES_FIELD_NAME_ESCAPE_CHAR])
ES_FIELD_NAME_SPECIAL_CHAR_MAP = {
    '.': '_$dot$_',
    ',': '_$comma$_',
    '#': '_$hash$_',
    '*': '_$star$_',
    '(': '_$lp$_',
    ')': '_$rp$_',
    '[': '_$lsb$_',
    ']': '_$rsb$_',
    '{': '_$lcb$_',
    '}': '_$rcb$_',
}

import StringIO
import elasticsearch
import elasticsearch_dsl
from elasticsearch_dsl import Q


# make encoded values as human-readable as possible
ES_FIELD_NAME_ESCAPE_CHAR = '$'
ES_FIELD_NAME_BAD_LEADING_CHARS = set(['_', '-', '+', ES_FIELD_NAME_ESCAPE_CHAR])
ES_FIELD_NAME_SPECIAL_CHAR_MAP = {
    '.': '_$dot$_',
    ',': '_$comma$_',
    '#': '_$hash$_',
    '*': '_$star$_',
    '(': '_$lp$_',
    ')': '_$rp$_',
    '[': '_$lsb$_',
    ']': '_$rsb$_',
    '{': '_$lcb$_',
    '}': '_$rcb$_',
}


def _encode_field_name(s):
    """Encodes arbitrary string into an elasticsearch field name

    See:
    https://discuss.elastic.co/t/special-characters-in-field-names/10658/2
    https://discuss.elastic.co/t/illegal-characters-in-elasticsearch-field-names/17196/2
    """
    field_name = StringIO.StringIO()
    for i, c in enumerate(s):
        if c == ES_FIELD_NAME_ESCAPE_CHAR:
            field_name.write(2*ES_FIELD_NAME_ESCAPE_CHAR)
        elif c in ES_FIELD_NAME_SPECIAL_CHAR_MAP:
            field_name.write(ES_FIELD_NAME_SPECIAL_CHAR_MAP[c])  # encode the char
        else:
            field_name.write(c)  # write out the char as is

    field_name = field_name.getvalue()

    # escape 1st char if necessary
    if any(field_name.startswith(c) for c in ES_FIELD_NAME_BAD_LEADING_CHARS):
        return ES_FIELD_NAME_ESCAPE_CHAR + field_name
    else:
        return field_name


def _decode_field_name(field_name):
    """Converts an elasticsearch field name back to the original unencoded string"""

    if field_name.startswith(ES_FIELD_NAME_ESCAPE_CHAR):
        field_name = field_name[1:]

    i = 0
    original_string = StringIO.StringIO()
    while i < len(field_name):
        current_string = field_name[i:]
        if current_string.startswith(2*ES_FIELD_NAME_ESCAPE_CHAR):
            original_string.write(ES_FIELD_NAME_ESCAPE_CHAR)
            i += 2
        else:
            for original_value, encoded_value in ES_FIELD_NAME_SPECIAL_CHAR_MAP.items():
                if current_string.startswith(encoded_value):
                    original_string.write(original_value)
                    i += len(encoded_value)
                    break
            else:
                original_string.write(field_name[i])
                i += 1

    return original_string.getvalue()

MONGO_QUERY_RESULTS_LIMIT = 6000

GENOTYPE_QUERY_MAP = {

    'ref_ref': 0,
    'ref_alt': 1,
    'alt_alt': 2,

    'has_alt': {'$gte': 1},
    'has_ref': {'$in': [0,1]},

    'not_missing': {'$gte': 0},
    'missing': -1,
}


CHROMOSOME_SIZES = { "1":249250621, "2":243199373, "3":198022430, "4":191154276, "5":180915260, "6":171115067, "7":159138663, "8":146364022, "9":141213431, "10":135534747, "11":135006516, "12":133851895, "13":115169878, "14":107349540, "15":102531392, "16":90354753, "17":81195210, "18":78077248, "19":59128983, "20":63025520, "21":48129895, "22":51304566, "X":155270560, "Y":59373566, "MT":16569, } # used for stats

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


class MongoDatastore(datastore.Datastore):

    def __init__(self, db, annotator, custom_population_store=None, custom_populations_map=None):
        self._db = db
        self._annotator = annotator
        self._custom_population_store = custom_population_store
        self._custom_populations_map = custom_populations_map
        if self._custom_populations_map is None:
            self._custom_populations_map = {}

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
            if variant_filter.locations:
                location_ranges = []
                for xstart, xend in variant_filter.locations:
                    location_ranges.append({'$and' : [ {'xpos' : {'$gte': xstart }}, {'xpos' : {'$lte': xend }}] })
                db_query['$or'] = location_ranges

            if variant_filter.so_annotations:
                db_query['db_tags'] = {'$in': variant_filter.so_annotations}
            if variant_filter.genes:
                db_query['db_gene_ids'] = {'$in': variant_filter.genes}
                db_query['db_exclude_genes'] = getattr(variant_filter, 'exclude_genes')
            if variant_filter.ref_freqs:
                for population, freq in variant_filter.ref_freqs:
                    if population in self._annotator.reference_population_slugs:
                        db_query['db_freqs.' + population] = {'$lte': freq}

        return db_query

    
    def get_elasticsearch_variants(self, query_json, project_id, family_id, variant_id_filter=None):
        from xbrowse_server.base.models import Individual

        ELASTICSEARCH_PORT="9200"
        if project_id == "ATGU_WGS-Jueppner":
            ELASTICSEARCH_HOST="10.4.3.24"
        elif project_id == "rare_genomes_project":
            ELASTICSEARCH_HOST="35.188.168.227"
        else:
            ELASTICSEARCH_HOST="10.48.5.14"
        client = elasticsearch.Elasticsearch(ELASTICSEARCH_HOST, port=ELASTICSEARCH_PORT)

        if project_id == "Engle_WGS_900":
            indices = ["engle_wgs_900_samples__*coding_0", "engle_wgs_900_samples__*coding_1", "engle_wgs_900_samples__*coding_2", "engle_wgs_900_samples__*coding_4"]
        elif project_id == "rare_genomes_project":
            indices = ["rgp_callset_2"] #["rare_genomes_project"]
        elif project_id == "Engle_WGS_2_sample":
            indices = ["engle_wgs_2_sample"]
        elif project_id == "NIAID-gatk3dot4":
            indices = ["niaid-gatk3dot4"]
        elif project_id == "ATGU_WGS-Jueppner":
            indices = ["atgu_wgs_jueppner"]
        else:
            raise ValueError("Unexpected project_id: " + str(project_id))

        if family_id is not None: 
            family_individual_ids = [i.indiv_id for i in Individual.objects.filter(family__family_id=family_id)]
            # figure out which indices contain this family
            if len(indices) == 1:
                index_to_search = indices[0]
            else:
                index_to_search = None
                for index_name in indices:
                    mapping = elasticsearch_dsl.Index(index_name, using=client).get_mapping()
                    mapping_subset = {k: v for k, v in mapping[index_name.replace("*", "")]["mappings"]["variant"]["properties"].items() if k.startswith("S") or k.startswith("RGP") or k.startswith("APY-001")}

                    corrected_indiv_id = family_individual_ids[0].replace("S132-4_1_1", "S132-4.1.1").replace("S218-3_1", "S218-3.1").replace("S250-1_1", "S250-1.1").replace("S258-1_1", "S258-1.1")
                    genotype_field_name = "%s_num_alt" % _encode_field_name(corrected_indiv_id)
                    if genotype_field_name in mapping_subset:
                        index_to_search = index_name
                        break
                    else:
                        print("%s not found in %s" % (genotype_field_name, index_name))
                else:
                    raise ValueError("ERROR: family: %s not found in database" % family_id)

            # do the query 
            s = elasticsearch_dsl.Search(using=client, index=index_to_search)
        else:
            family_individual_ids = [i.indiv_id for i in Individual.objects.filter(project__project_id=project_id)]

            if project_id == "Engle_WGS_900":
                indices = ["engle_wgs_900_samples__*"]
            elif project_id == "rare_genomes_project":
                indices = ["rare_genomes_project__*coding"]
            elif project_id == "Engle_WGS_2_sample":
                indices = ["engle_wgs_2_sample"]
            elif project_id == "NIAID-gatk3dot4":
                indices = ["niaid-gatk3dot4"]
            elif project_id == "ATGU_WGS-Jueppner":
                indices = ["atgu_wgs_jueppner"]
            s = elasticsearch_dsl.Search(using=client, index=indices[0]) #",".join(indices))

        print("===> QUERY: ")
        pprint(query_json)

        if variant_id_filter is not None:
            s = s.filter('term', **{"variantId": variant_id_filter})

        # parse variant query
        #query_json = query_json.get('$and', [])
        for key, value in query_json.items():
            if key == 'db_tags':
                vep_consequences = query_json.get('db_tags', {}).get('$in', [])
                s = s.filter("terms",  transcriptConsequenceTerms=vep_consequences)
                print("==> transcriptConsequenceTerms: %s" % str(vep_consequences))

            if key.startswith("genotypes"):
                sample_id = ".".join(key.split(".")[1:-1])
                encoded_sample_id = _encode_field_name(sample_id)
                genotype_filter = value
                if type(genotype_filter) == int or type(genotype_filter) == basestring:
                    print("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": genotype_filter}))
                    s = s.filter('term', **{encoded_sample_id+"_num_alt": genotype_filter})

                elif '$gte' in genotype_filter:
                    genotype_filter = {k.replace("$", ""): v for k, v in genotype_filter.items()}
                    s = s.filter('range', **{encoded_sample_id+"_num_alt": genotype_filter})
                    print("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": genotype_filter}))
                elif "$in" in genotype_filter:
                    num_alt_values = genotype_filter['$in']
                    q = Q('term', **{encoded_sample_id+"_num_alt": num_alt_values[0]})
                    print("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": num_alt_values[0]}))
                    for num_alt_value in num_alt_values[1:]:
                        q = q | Q('term', **{encoded_sample_id+"_num_alt": num_alt_value})
                        print("==> genotypes: %s" % str({encoded_sample_id+"_num_alt": num_alt_value}))
                    s = s.filter(q)

            if key == "db_gene_ids":
                gene_ids = query_json.get('db_gene_ids', {}).get('$in', [])
                exclude_genes = query_json.get('db_exclude_genes')

                if exclude_genes:
                    s = s.exclude("terms", geneIds=gene_ids)
                else:
                    s =  s.filter("terms",  geneIds=gene_ids)
                print("==> %s %s" % ("exclude" if exclude_genes else "include", "geneIds: " + str(gene_ids)))

            if key == "$or" and type(value) == list:
                xpos_filters = value[0].get("$and", {})

                # for example: $or : [{'$and': [{'xpos': {'$gte': 12345}}, {'xpos': {'$lte': 54321}}]}]
                xpos_filters_dict = {}
                for xpos_filter in xpos_filters:
                    xpos_filter_setting = xpos_filter["xpos"]  # for example {'$gte': 12345} or {'$lte': 54321}
                    xpos_filters_dict.update(xpos_filter_setting)
                xpos_filter_setting = {k.replace("$", ""): v for k, v in xpos_filters_dict.items()}
                s = s.filter('range', **{"xpos": xpos_filter_setting})
                print("==> xpos range: " + str({"xpos": xpos_filter_setting}))


            af_key_map = {
                "db_freqs.1kg_wgs_phase3": "g1k_AF",
                "db_freqs.1kg_wgs_phase3_popmax": "g1k_POPMAX_AF",
                "db_freqs.exac_v3": "exac_AF",
                "db_freqs.exac_v3_popmax": "exac_AF_POPMAX",
                "db_freqs.topmed": "topmed_AF",
                "db_freqs.gnomad_exomes": "gnomad_exomes_AF",
                "db_freqs.gnomad_exomes_popmax": "gnomad_exomes_AF_POPMAX",
                "db_freqs.gnomad_genomes": "gnomad_genomes_AF",
                "db_freqs.gnomad_genomes_popmax": "gnomad_genomes_AF_POPMAX",
            }

            if key in af_key_map:
                filter_key = af_key_map[key]
                af_filter_setting = {k.replace("$", ""): v for k, v in value.items()}
                s = s.filter(Q('range', **{filter_key: af_filter_setting}) | ~Q('exists', field=filter_key))
                print("==> %s: %s" % (filter_key, af_filter_setting))

            s.sort("xpos")

        print("=====")
        print("FULL QUERY OBJ: " + pformat(s.__dict__))
        print("FILTERS: " + pformat(s.to_dict()))
        print("=====")
        print("Hits: ")
        # https://elasticsearch-py.readthedocs.io/en/master/helpers.html#elasticsearch.helpers.scan

        response = s.execute()
        print("TOTAL: " + str(response.hits.total))
        #print(pformat(response.to_dict()))
        for i, hit in enumerate(s.scan()):  # preserve_order=True
            if i == 0:
                print("Hit columns: " + str(hit.__dict__))
            #print("##### Raw result " + str(i) + "  "+ str(hit.meta))
            #pprint(hit.__dict__)
            filters = ",".join(hit["filters"]) if "filters" in hit else ""
            genotypes = {}
            all_num_alt = []
            for individual_id in family_individual_ids:
                encoded_individual_id = _encode_field_name(individual_id)
                num_alt =  int(hit["%s_num_alt" % encoded_individual_id]) if ("%s_num_alt" % encoded_individual_id) in hit else -1
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
                    'ab': hit["%s_ab" % encoded_individual_id] if ("%s_ab" % encoded_individual_id) in hit else '',
                    'alleles': map(str, alleles),
                    'extras': {
                        'ad': hit["%s_ab" % encoded_individual_id]  if ("%s_ad" % encoded_individual_id) in hit else '',
                        'dp': hit["%s_dp" % encoded_individual_id]  if ("%s_dp" % encoded_individual_id) in hit else '',
                        'pl': '',
                    },
                    'filter': filters or "pass",
                    'gq': hit["%s_gq" % encoded_individual_id] if ("%s_gq" % encoded_individual_id in hit and hit["%s_gq" % encoded_individual_id] is not None) else '',
                    'num_alt': num_alt,
                }

            if all([num_alt <= 0 for num_alt in all_num_alt]):
                #print("Filtered out due to genotype: " + str(genotypes))
                print("Filtered all_num_alt <= 0 - Result %s: GRCh38: %s:%s,  cadd: %s  %s - %s" % (i, hit["contig"], hit["start"], hit["cadd_PHRED"] if "cadd_PHRED" in hit else "", hit["transcriptConsequenceTerms"], all_num_alt))
                continue
            
            vep_annotation = json.loads(str(hit['sortedTranscriptConsequences']))
            
            if project_id not in ["NIAID-gatk3dot4"]:
                lifted_over_coord = liftover.convert_coordinate("chr%s" % hit["contig"].replace("chr", ""), int(hit["start"])), #
                if lifted_over_coord and lifted_over_coord[0] and lifted_over_coord[0][0]:
                    lifted_over_coord = "%s-%s-%s-%s "% (lifted_over_coord[0][0][0], lifted_over_coord[0][0][1], hit["ref"],  hit["alt"])
                else:
                    lifted_over_coord = None
            else:
                lifted_over_coord = hit["variantId"]
                                                     
            result = {
                #u'_id': ObjectId('596d2207ff66f729285ca588'),
                'alt': str(hit["alt"]) if "alt" in hit else None,
                'annotation': {
                    'fathmm': None,
                    'metasvm': None,
                    'muttaster': None,
                    'polyphen': None,
                    'sift': None,

                    'cadd_phred': hit["cadd_PHRED"] if "cadd_PHRED" in hit else None,
                    'dann_score': hit["dbnsfp_DANN_score"] if "dbnsfp_DANN_score" in hit else None,
                    'revel_score': hit["dbnsfp_REVEL_score"] if "dbnsfp_REVEL_score" in hit else None,
                    'mpc_score': hit["mpc_MPC"] if "mpc_MPC" in hit else None,
                    
                    'annotation_tags': list(hit["transcriptConsequenceTerms"]) if "transcriptConsequenceTerms" in hit else None,
                    'coding_gene_ids': list(hit['geneIds']),
                    'gene_ids': list(hit['geneIds']),
                    'vep_annotation': vep_annotation,
                    'vep_group': str(hit['mainTranscript_major_consequence']),
                    'vep_consequence': str(hit['mainTranscript_major_consequence']),
                    'worst_vep_annotation_index': 0,
                    'worst_vep_index_per_gene': {str(hit['mainTranscript_gene_id']): 0},
                },
                'chr': hit["contig"],
                'coding_gene_ids': None,
                'db_freqs': {
                    '1kg_wgs_AF': float(hit["g1k_AF"] or 0.0),
                    '1kg_wgs_popmax_AF': float(hit["g1k_POPMAX_AF"] or 0.0),
                    'exac_v3_AC': float(hit["exac_AC_Adj"] or 0.0) if "exac_AC_Adj" in hit else 0.0,
                    'exac_v3_AF': float(hit["exac_AF"] or 0.0) if "exac_AF" in hit else (hit["exac_AC_Adj"]/float(hit["exac_AN_Adj"]) if int(hit["exac_AN_Adj"] or 0) > 0 else 0.0),                    
                    'exac_v3_popmax_AF': float(hit["exac_AF_POPMAX"] or 0.0) if "exac_AF_POPMAX" in hit else 0.0,
                    'topmed_AF': float(hit["topmed_AF"] or 0.0) if "topmed_AF" in hit else 0.0,
                    'gnomad_exomes_AC': float(hit["gnomad_exomes_AC"] or 0.0) if "gnomad_exomes_AC" in hit else 0.0,
                    'gnomad_exomes_Hom': float(hit["gnomad_exomes_HOM"] or 0.0) if "gnomad_exomes_HOM" in hit else 0.0,
                    'gnomad_exomes_AF': float(hit["gnomad_exomes_AF"] or 0.0) if "gnomad_exomes_AF" in hit else 0.0,
                    'gnomad_exomes_popmax_AF': float(hit["gnomad_exomes_AF_POPMAX"] or 0.0) if "gnomad_exomes_AF_POPMAX" in hit else 0.0,
                    'gnomad_genomes_AC': float(hit["gnomad_genomes_AC"] or 0.0) if "gnomad_genomes_AC" in hit else 0.0,
                    'gnomad_genomes_Hom': float(hit["gnomad_genomes_HOM"] or 0.0) if "gnomad_genomes_HOM" in hit else 0.0,
                    'gnomad_genomes_AF': float(hit["gnomad_genomes_AF"] or 0.0) if "gnomad_genomes_AF" in hit else 0.0,
                    'gnomad_genomes_popmax_AF': float(hit["gnomad_genomes_AF_POPMAX"] or 0.0) if "gnomad_genomes_AF_POPMAX" in hit else 0.0,
                    'gnomad_exome_coverage': float(hit["gnomad_exome_coverage"] or -1) if "gnomad_exome_coverage" in hit else -1,
                    'gnomad_genome_coverage': float(hit["gnomad_genome_coverage"] or -1) if "gnomad_genome_coverage" in hit else -1,
                },
                'db_gene_ids': list(hit["geneIds"]),
                'db_tags': str(hit["transcriptConsequenceTerms"]) if "transcriptConsequenceTerms" in hit else None,
                'extras': {
                    'grch37_coords': lifted_over_coord,
                    'grch38_coords': "%s-%s-%s-%s" % (hit["contig"], hit["start"], hit["ref"], hit["alt"]),
                    u'alt_allele_pos': 0,
                    u'orig_alt_alleles': map(str, [a.split("-")[-1] for a in hit["originalAltAlleles"]]) if "originalAltAlleles" in hit else []},
                'gene_ids': None,
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
            
            #print("\n\nConverted result: " + str(i))
            print("Result %s: GRCh37: %s GRCh38: %s:%s,  cadd: %s  %s - gene ids: %s, coding gene_ids: %s" % (i, lifted_over_coord, result["chr"], result["pos"], hit["cadd_PHRED"] if "cadd_PHRED" in hit else "", hit["transcriptConsequenceTerms"], result["gene_ids"], result["coding_gene_ids"]))
            #pprint(result["db_freqs"])

            yield result
            
            if i > 50000:
                break

        
    def get_variants(self, project_id, family_id, genotype_filter=None, variant_filter=None):

        db_query = self._make_db_query(genotype_filter, variant_filter)
        sys.stderr.write("%s\n" % str(db_query))

        counters = OrderedDict([('returned_by_query', 0), ('passes_variant_filter', 0)])
        pprint({'$and' : [{k: v} for k, v in db_query.items()]})

        if project_id in ["Engle_WGS_900", "rare_genomes_project", "Engle_WGS_2_sample", "NIAID-gatk3dot4", "ATGU_WGS-Jueppner"]:
            for i, variant_dict in enumerate(self.get_elasticsearch_variants(db_query, project_id, family_id)):
                #if i > 1000:
                #    return
                #print("----- variant"+str(i))
                #pprint(variant_dict)

                variant = Variant.fromJSON(variant_dict)
                print("gene_ids: %s   ----- variant.gene_ids %s  ======> "  % (variant.gene_ids, variant_dict.get("gene_ids")))
                #print("###### ==> variant.annotation: " + str(variant.annotation))
                self.add_annotations_to_variant(variant, project_id)
                counters["returned_by_query"] += 1
                if passes_variant_filter(variant, variant_filter)[0]:
                    counters["passes_variant_filter"] += 1
                    yield variant
                else:
                    print("Failed variant filter: %s-%s" % (variant_dict["chr"], variant_dict["pos"]))

            print("Counters: " + str(counters))
            return
        
        collection = self._get_family_collection(project_id, family_id)
        if not collection:
            print("Error: mongodb collection not found for project %s family %s " % (project_id, family_id))
            return
        
        for i, variant_dict in enumerate(collection.find({'$and' : [{k: v} for k, v in db_query.items()]}).sort('xpos').limit(MONGO_QUERY_RESULTS_LIMIT+5)):
            if i >= MONGO_QUERY_RESULTS_LIMIT:
                raise Exception("ERROR: this search exceeded the %s variant result size limit. Please set additional filters and try again." % MONGO_QUERY_RESULTS_LIMIT)

            #print("----- variant"+str(i))
            pprint(variant_dict)
            
            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            counters["returned_by_query"] += 1
            if passes_variant_filter(variant, variant_filter)[0]:
                counters["passes_variant_filter"] += 1
                yield variant

        for k, v in counters.items():
            sys.stderr.write("    %s: %s\n" % (k,v))


    def get_variants_in_gene(self, project_id, family_id, gene_id, genotype_filter=None, variant_filter=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)

        db_query = self._make_db_query(genotype_filter, modified_variant_filter)
        collection = self._get_family_collection(project_id, family_id)
        if not collection:
            return

        # we have to collect list in memory here because mongo can't sort on xpos,
        # as result size can get too big.
        # need to find a better way to do this.

        variants = []
        print("###### get_variants_in_gene(..) query: ")
        pprint(db_query)
        for variant_dict in collection.find(db_query).hint([('db_gene_ids', pymongo.ASCENDING), ('xpos', pymongo.ASCENDING)]):
            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            if passes_variant_filter(variant, modified_variant_filter):
                variants.append(variant)
        variants = sorted(variants, key=lambda v: v.unique_tuple())
        for v in variants:
            yield v

    def get_variants_in_range(self, project_id, family_id, xpos_start, xpos_end):
        collection = self._get_family_collection(project_id, family_id)
        if not collection:
            raise ValueError("Family not found: " + str(family_id))

        print("###### get_variants_in_range(..) query: ")
        pprint({'$and': [{'xpos': {'$gte': xpos_start}}, {'xpos': {'$lte': xpos_end}}]})
        
        for i, variant_dict in enumerate(collection.find({'$and': [{'xpos': {'$gte': xpos_start}}, {'xpos': {'$lte': xpos_end}}]}).limit(MONGO_QUERY_RESULTS_LIMIT+5)):
            if i > MONGO_QUERY_RESULTS_LIMIT:
                raise Exception("ERROR: this search exceeded the %s variant result size limit. Please set additional filters and try again." % MONGO_QUERY_RESULTS_LIMIT)

            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            yield variant


    def get_single_variant(self, project_id, family_id, xpos, ref, alt):
        from seqr.utils.xpos_utils import get_chrom_pos

        chrom, pos = get_chrom_pos(xpos)

        variant_id = "%s-%s-%s-%s" % (chrom, pos, ref, alt)
        results = list(self.get_elasticsearch_variants({}, project_id, family_id, variant_id))
        print("###### single variant search: " + variant_id + ". results: " + str(results))
        if not results:
            return None
        variant_dict = results[0]
        variant = Variant.fromJSON(variant_dict)
        self.add_annotations_to_variant(variant, project_id)
        return variant

    
        #collection = self._get_family_collection(project_id, family_id)
        #if not collection:
        #    return None
        #variant_dict = collection.find_one({'xpos': xpos, 'ref': ref, 'alt': alt})
        #if variant_dict:
        #    variant = Variant.fromJSON(variant_dict)
        #    self.add_annotations_to_variant(variant, project_id)
        #    return variant
        #else:
        #    return None

    def get_variants_cohort(self, project_id, cohort_id, variant_filter=None):

        db_query = self._make_db_query(None, variant_filter)
        collection = self._get_family_collection(project_id, cohort_id)
        print("##### get_variants_cohort query:")
        pprint(db_query)
        for i, variant in enumerate(collection.find(db_query).sort('xpos').limit(MONGO_QUERY_RESULTS_LIMIT+5)):
            if i > MONGO_QUERY_RESULTS_LIMIT:
                raise Exception("ERROR: this search exceeded the %s variant result size limit. Please set additional filters and try again." % MONGO_QUERY_RESULTS_LIMIT)

            yield Variant.fromJSON(variant)

    def get_single_variant_cohort(self, project_id, cohort_id, xpos, ref, alt):

        collection = self._get_family_collection(project_id, cohort_id)
        variant = collection.find_one({'xpos': xpos, 'ref': ref, 'alt': alt})
        return Variant.fromJSON(variant)

    #
    # New sample stuff
    #
    def get_all_individuals(self):
        """
        List of all individuals in the datastore
        Items are (project_id, indiv_id) tuples
        """
        return [(i['project_id'], i['indiv_id']) for i in self._db.individuals.find()]

    def get_all_families(self):
        """
        List of all families in the datastore
        Items are (project_id, family_id) tuples
        """
        return [(i['project_id'], i['family_id']) for i in self._db.families.find()]

    def individual_exists(self, project_id, indiv_id):
        return self._db.individuals.find_one({
            'project_id': project_id,
            'indiv_id': indiv_id
        }) is not None

    def add_individual(self, project_id, indiv_id):
        if self.individual_exists(project_id, indiv_id):
            raise Exception("Indiv (%s, %s) already exists" % (project_id, indiv_id))
        indiv = {
            'project_id': project_id,
            'indiv_id': indiv_id,
        }
        self._db.individuals.save(indiv)

    def get_individuals(self, project_id):
        return [ i['indiv_id'] for i in self._db.individuals.find({ 'project_id': project_id }) ]

    def family_exists(self, project_id, family_id):
        return self._db.families.find_one({'project_id': project_id, 'family_id': family_id}) is not None

    def get_individuals_for_family(self, project_id, family_id):
        return self._db.families.find_one({'project_id': project_id, 'family_id': family_id})['individuals']

    def get_family_status(self, project_id, family_id):
        family_doc = self._db.families.find_one({'project_id': project_id, 'family_id': family_id})
        if not family_doc:
            return None
        return family_doc['status']

    def get_family_statuses(self, family_list):
        ret = {f: None for f in family_list}
        by_project = defaultdict(list)
        for project_id, family_id in family_list:
            by_project[project_id].append(family_id)
        for project_id, family_id_list in by_project.items():
            for family_doc in self._db.families.find({'project_id': project_id, 'family_id': {'$in': family_id_list}}):
                ret[(project_id, family_doc['family_id'])] = family_doc['status']
        return ret

    def _get_family_info(self, project_id, family_id=None):
        if family_id is None:
            return [family_info for family_info in self._db.families.find({'project_id': project_id})]
        else:
            return self._db.families.find_one({'project_id': project_id, 'family_id': family_id})

    def _get_family_collection(self, project_id, family_id):
        family_info = self._get_family_info(project_id, family_id)
        if not family_info:
            return None
        return self._db[family_info['coll_name']]


    #
    # Variant loading
    # Unique to mongo datastore, not part of protocol
    #

    def _add_family_info(self, project_id, family_id, individuals):
        """
        Add all the background info about this family
        We try to keep this as simple as possible - just IDs
        After this is run, variants are ready to be loaded
        """

        if self.family_exists(project_id, family_id):
            #raise Exception("Family (%s, %s) already exists" % (project_id, family_id))
            return

        for indiv_id in individuals:
            if not self.individual_exists(project_id, indiv_id):
                self.add_individual(project_id, indiv_id)

        family_coll_name = "family_%s_%s" % (slugify(project_id, separator='_'),
                                             slugify(family_id, separator='_'))
        family = {
            'project_id': project_id,
            'family_id': family_id,
            'individuals': individuals,
            'coll_name': family_coll_name,
            'status': 'loading'
        }

        family_collection = self._db[family_coll_name]
        self._index_family_collection(family_collection)

        self._db.families.save(family)

    def add_family(self, project_id, family_id, individuals):
        """
        Add new family
        Adds individuals if they don't exist yet
        Phenotypes and pedigrees aren't stored, just which individuals
        """
        self._add_family_info(project_id, family_id, individuals)

    def add_family_set(self, family_list):
        """
        Add a set of families from the same VCF file
        family_list is just a list of dicts with keys of project_id, family_id, individuals
        """
        for fam_info in family_list:
            self._add_family_info(fam_info['project_id'], fam_info['family_id'], fam_info['individuals'])

    def load_family_set(self, vcf_file_path, family_list, reference_populations=None, vcf_id_map=None, mark_as_loaded=True, start_from_chrom=None, end_with_chrom=None):
        """
        Load a set of families from the same VCF file
        family_list is a list of (project_id, family_id) tuples
        """
        family_info_list = [self._get_family_info(f[0], f[1]) for f in family_list]
        self._load_variants_for_family_set(
            family_info_list,
            vcf_file_path,
            reference_populations=reference_populations,
            vcf_id_map=vcf_id_map, 
            start_from_chrom=start_from_chrom, 
            end_with_chrom=end_with_chrom,
        )

        if mark_as_loaded:
            for family in family_info_list:
                self._finalize_family_load(family['project_id'], family['family_id'])

    def _load_variants_for_family_set(self, family_info_list, vcf_file_path, reference_populations=None, vcf_id_map=None, start_from_chrom=None, end_with_chrom=None):
        """
        Load variants for a set of families, assuming all come from the same VCF file

        Added after load_variants_for_family to speed up loading - goal is to
        only iterate the VCF once. Here's how it works:

        for each raw variant:
            annotate
            for each family:
                extract family variant from full variant
                update variant inheritance
                if family variant is relevant for family:
                    add to collection

        """
        self._add_vcf_file_for_family_set(
            family_info_list,
            vcf_file_path,
            reference_populations=reference_populations,
            vcf_id_map=vcf_id_map,
            start_from_chrom=start_from_chrom, 
            end_with_chrom=end_with_chrom,
        )

    def _add_vcf_file_for_family_set(self, family_info_list, vcf_file_path, reference_populations=None, vcf_id_map=None, start_from_chrom=None, end_with_chrom=None):
        collections = {f['family_id']: self._db[f['coll_name']] for f in family_info_list}
        #for collection in collections.values():
        #    collection.drop_indexes()
        indiv_id_list = [i for f in family_info_list for i in f['individuals']]
        number_of_families = len(family_info_list)
        sys.stderr.write("Loading variants for %(number_of_families)d families %(family_info_list)s from %(vcf_file_path)s\n" % locals())

        for family in family_info_list:
            print("Indexing family: " + str(family))
            collection = collections[family['family_id']]
            collection.ensure_index([('xpos', 1), ('ref', 1), ('alt', 1)])

        # check whether some of the variants for this chromosome has been loaded already
        # if yes, start from the last loaded variant, and not from the beginning
        if "_chr" in vcf_file_path or ".chr" in vcf_file_path:
            # if the VCF files are split by chromosome (eg. for WGS projects), check within the chromosome
            vcf_file = compressed_file(vcf_file_path)
            variant = next(vcf_stuff.iterate_vcf(vcf_file, genotypes=False, indiv_id_list=indiv_id_list, vcf_id_map=vcf_id_map))
            print(vcf_file_path + "  - chromsome: " + str(variant.chr))
            vcf_file.close()

            position_per_chrom = {}
            for chrom in range(1,24):
                position_per_chrom[chrom] = defaultdict(int)
                for family in family_info_list:     #variants = collections[family['family_id']].find().sort([('xpos',-1)]).limit(1)
                    variants = list(collections[family['family_id']].find({'$and': [{'xpos': { '$gte': chrom*1e9 }}, {'xpos': { '$lt': (chrom+1)*1e9}}] }).sort([('xpos',-1)]).limit(1))
                    if len(variants) > 0:
                        position_per_chrom[chrom][family['family_id']] = variants[0]['xpos'] - chrom*1e9
                    else:
                        position_per_chrom[chrom][family['family_id']] = 0

            for chrom in range(1,24):
                position_per_chrom[chrom] = min(position_per_chrom[chrom].values()) # get the smallest last-loaded variant position for this chromosome across all families

            chr_idx = int(variant.xpos/1e9)
            start_from_pos = int(position_per_chrom[chr_idx])

            print("Start from: %s - %s (%0.1f%% done)" % (chr_idx, start_from_pos, 100.*start_from_pos/CHROMOSOME_SIZES[variant.chr.replace("chr", "")]))
            tabix_file = pysam.TabixFile(vcf_file_path)
            vcf_iter = itertools.chain(tabix_file.header, tabix_file.fetch(variant.chr.replace("chr", ""), start_from_pos, int(2.5e8)))
        elif start_from_chrom or end_with_chrom:
            if start_from_chrom:
                print("Start chrom: chr%s" % start_from_chrom)
            if end_with_chrom: 
                print("End chrom: chr%s" % end_with_chrom)
            
            chrom_list = list(map(str, range(1,23))) + ['X','Y']
            chrom_list_start_index = 0
            if start_from_chrom:
                chrom_list_start_index = chrom_list.index(start_from_chrom.replace("chr", "").upper())
                
            chrom_list_end_index = len(chrom_list)
            if end_with_chrom:
                chrom_list_end_index = chrom_list.index(end_with_chrom.replace("chr", "").upper())
            
            tabix_file = pysam.TabixFile(vcf_file_path)
            vcf_iter = tabix_file.header
            for chrom in chrom_list[chrom_list_start_index:chrom_list_end_index+1]:
                print("Will load chrom: " + chrom)
                try:
                    vcf_iter = itertools.chain(vcf_iter, tabix_file.fetch(chrom))
                except ValueError as e:
                    print("WARNING: " + str(e))
                    
        else:
            vcf_iter = vcf_file = compressed_file(vcf_file_path)
            # TODO handle case where it's one vcf file, not split by chromosome

        size = os.path.getsize(vcf_file_path)
        #progress = get_progressbar(size, 'Loading VCF: {}'.format(vcf_file_path))

        def insert_all_variants_in_buffer(buff, collections_dict):
            for family_id in buff:
                if len(buff[family_id]) == 0:  # defensive programming
                    raise ValueError("%s has zero variants to insert. Should not be in buff." % family_id)

            while len(buff) > 0:
                # choose a random family for which to insert a variant from among families that still have variants to insert
                family_id = random.choice(buff.keys())

                # pop a variant off the list for this family, and insert it
                family_variant_dict_to_insert = buff[family_id].pop()
                c = collections_dict[family_id]
                c.insert(family_variant_dict_to_insert)

                if len(buff[family_id]) == 0:
                    del buff[family_id]  # if no more variants for this family, delete it

        vcf_rows_counter = 0
        variants_buffered_counter = 0
        family_id_to_variant_list = defaultdict(list)  # will accumulate variants to be inserted all at once
        for variant in vcf_stuff.iterate_vcf(vcf_iter, genotypes=True, indiv_id_list=indiv_id_list, vcf_id_map=vcf_id_map):
            if variant.alt == "*":
                #print("Skipping GATK 3.4 * alt allele: " + str(variant.unique_tuple()))
                continue

            try:
                annotation = self._annotator.get_annotation(variant.xpos, variant.ref, variant.alt, populations=reference_populations)
            except ValueError, e:
                sys.stderr.write("WARNING: " + str(e) + "\n")
                continue

            vcf_rows_counter += 1
            for family in family_info_list:
                # TODO: can we move this inside the if relevant clause below?
                try:
                    family_variant = variant.make_copy(restrict_to_genotypes=family['individuals'])
                    family_variant_dict = family_variant.toJSON()
                    _add_index_fields_to_variant(family_variant_dict, annotation)
                    if xbrowse_utils.is_variant_relevant_for_individuals(family_variant, family['individuals']):
                        collection = collections[family['family_id']]
                        if not collection.find_one({'xpos': family_variant.xpos, 'ref': family_variant.ref, 'alt': family_variant.alt}):
                            family_id_to_variant_list[family['family_id']].append(family_variant_dict)
                            variants_buffered_counter += 1
                except Exception, e:
                    sys.stderr.write("ERROR: on variant %s, family: %s - %s\n" % (variant.toJSON(), family, e))


            if variants_buffered_counter > 2000:
                print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + "-- %s:%s-%s-%s (%0.1f%% done) - inserting %d family-variants from %d vcf rows into %s families" % (variant.chr, variant.pos, variant.ref, variant.alt, 100*variant.pos / CHROMOSOME_SIZES[variant.chr.replace("chr", "")], variants_buffered_counter, vcf_rows_counter, len(family_id_to_variant_list)))

                insert_all_variants_in_buffer(family_id_to_variant_list, collections)

                assert len(family_id_to_variant_list) == 0
                vcf_rows_counter = 0
                variants_buffered_counter = 0

        if variants_buffered_counter > 0:
            insert_all_variants_in_buffer(family_id_to_variant_list, collections)

            assert len(family_id_to_variant_list) == 0


    def _finalize_family_load(self, project_id, family_id):
        """
        Call after family is loaded. Sets status and possibly more in the future
        """
        self._index_family_collection(self._get_family_collection(project_id, family_id))
        family = self._db.families.find_one({'project_id': project_id, 'family_id': family_id})
        family['status'] = 'loaded'
        self._db.families.save(family)

    def _index_family_collection(self, collection):
        collection.ensure_index('xpos')
        collection.ensure_index([('db_freqs', 1), ('xpos', 1)])
        collection.ensure_index([('db_tags', 1), ('xpos', 1)])
        collection.ensure_index([('db_gene_ids', 1), ('xpos', 1)])

    def delete_project(self, project_id):
        self._db.individuals.remove({'project_id': project_id})
        for family_info in self._db.families.find({'project_id': project_id}):
            self._db.drop_collection(family_info['coll_name'])
        self._db.families.remove({'project_id': project_id})

    def delete_family(self, project_id, family_id):
        for family_info in self._db.families.find({'project_id': project_id, 'family_id': family_id}):
            self._db.drop_collection(family_info['coll_name'])
        self._db.families.remove({'project_id': project_id, 'family_id': family_id})

    def add_annotations_to_variant(self, variant, project_id):
        self._annotator.annotate_variant(variant)
        try:
            if self._custom_population_store:
                custom_pop_slugs = self._custom_populations_map.get(project_id)
                if custom_pop_slugs:
                    self._custom_population_store.add_populations_to_variants([variant], custom_pop_slugs)
        except Exception, e:
            sys.stderr.write("Error in add_annotations_to_variant: " + str(e) + "\n")


    #
    # This stuff is all copied in from ProjectDatastore
    #

    def _get_project_collection(self, project_id):
        project = self._db.projects.find_one({'project_id': project_id})
        if project:
            return self._db[project['collection_name']]
        else:
            return None

    def add_variants_to_project_from_vcf(self, vcf_file, project_id, indiv_id_list=None, start_from_chrom=None, end_with_chrom=None):
        """
        This is how variants are loaded
        """

        chrom_list = list(map(str, range(1,23))) + ['X','Y']
        chrom_list_start_index = 0
        if start_from_chrom:
            chrom_list_start_index = chrom_list.index(start_from_chrom.replace("chr", "").upper())

        chrom_list_end_index = len(chrom_list)
        if end_with_chrom:
            chrom_list_end_index = chrom_list.index(end_with_chrom.replace("chr", "").upper())
        chromosomes_to_include = set(chrom_list[chrom_list_start_index : chrom_list_end_index])
        #tabix_file = pysam.TabixFile(vcf_file)
        #vcf_iter = tabix_file.header
        #for chrom in chrom_list[chrom_list_start_index:chrom_list_end_index]:
        #    print("Will load chrom: " + chrom)
        #    vcf_iter = itertools.chain(vcf_iter, tabix_file.fetch(chrom))

        project_collection = self._get_project_collection(project_id)
        reference_populations = self._annotator.reference_population_slugs + self._custom_populations_map.get(project_id)
        for counter, variant in enumerate(vcf_stuff.iterate_vcf(vcf_file, genotypes=True, indiv_id_list=indiv_id_list)):
            if (start_from_chrom or end_with_chrom) and variant.chr.replace("chr", "") not in chromosomes_to_include:
                continue

            if variant.alt == "*":
                #print("Skipping GATK 3.4 * alt allele: " + str(variant.unique_tuple()))
                continue

            if counter % 2000 == 0:
                print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S") + "-- inserting variant %d  %s:%s-%s-%s (%0.1f%% done with %s) " % (counter, variant.chr, variant.pos, variant.ref, variant.alt, 100*variant.pos / CHROMOSOME_SIZES[variant.chr.replace("chr", "")], variant.chr))

            variant_dict = project_collection.find_one({'xpos': variant.xpos, 'ref': variant.ref, 'alt': variant.alt})
            if not variant_dict:
                variant_dict = variant.toJSON()
                try:
                    annotation = self._annotator.get_annotation(variant.xpos, variant.ref, variant.alt, populations=reference_populations)
                except ValueError, e:
                    sys.stderr.write("WARNING: " + str(e) + "\n")
                    continue
                _add_index_fields_to_variant(variant_dict, annotation)
            else:
                for indiv_id, genotype in variant.get_genotypes():
                    if genotype.num_alt != 0:
                        variant_dict['genotypes'][indiv_id] = genotype._asdict()
            project_collection.save(variant_dict)

    def project_exists(self, project_id):
        return self._db.projects.find_one({'project_id': project_id})

    def project_collection_is_loaded(self, project_id):
        """Returns true if the project collection is fully loaded (this is the
        collection that stores the project-wide set of variants used for gene
        search)."""
        project = self._db.projects.find_one({'project_id': project_id})
        if project is not None and "is_loaded" in project:
            return project["is_loaded"]
        else:
            return False

    def set_project_collection_to_loaded(self, project_id, is_loaded=True):
        """Set the project collection "is_loaded" field to the given value.
        This field is used by other parts of seqr to decide if this collection
        is ready for use."""
        project = self._db.projects.find_one({'project_id': project_id})
        if project is not None and "is_loaded" in project:
            project["is_loaded"] = is_loaded
            #print("Setting %s to %s" % (project["_id"], project))
            project_id = project['_id']
            del project['_id']
            self._db.projects.update({'_id': project_id}, {"$set": project})
        else:
            raise ValueError("Couldn't find project collection for %s" % project_id)

    def add_project(self, project_id):
        """
        Add all the background info about this family
        We try to keep this as simple as possible - just IDs
        After this is run, variants are ready to be loaded
        """

        if self.project_exists(project_id):
            raise Exception("Project {} exists".format(project_id))

        project = {
            'project_id': project_id,
            'collection_name': 'project_' + ''.join([random.choice(string.digits) for i in range(8)]),
            'is_loaded': False,
        }
        self._db.projects.insert(project)
        project_collection = self._db[project['collection_name']]
        self._index_family_collection(project_collection)

    def delete_project_store(self, project_id):
        project = self._db.projects.find_one({'project_id': project_id})
        if project:
            self._db.drop_collection(project['collection_name'])
        self._db.projects.remove({'project_id': project_id})

    def get_project_variants_in_gene(self, project_id, gene_id, variant_filter=None):

        if variant_filter is None:
            modified_variant_filter = VariantFilter()
        else:
            modified_variant_filter = copy.deepcopy(variant_filter)
        modified_variant_filter.add_gene(gene_id)


        db_query = self._make_db_query(None, modified_variant_filter)
        sys.stderr.write("Project Gene Search: " + str(project_id) + " all variants query: " + str(db_query))
        if project_id in ["Engle_WGS_900", "rare_genomes_project", "Engle_WGS_2_sample", "NIAID-gatk3dot4", "ATGU_WGS-Jueppner"]:
            variants = []
            for i, variant_dict in enumerate(self.get_elasticsearch_variants(db_query, project_id, family_id=None)):
                variant = Variant.fromJSON(variant_dict)
                self.add_annotations_to_variant(variant, project_id)
                if passes_variant_filter(variant, modified_variant_filter):
                    variants.append(variant)
                    
            #variants = sorted(variants, key=lambda v: v.unique_tuple())
            return variants
        
        collection = self._get_project_collection(project_id)
        if not collection:
            return []

        # we have to collect list in memory here because mongo can't sort on xpos,
        # as result size can get too big.
        # need to find a better way to do this.
        variants = []
        print("###### get_project_variants_in_gene(..) query: ")
        pprint(db_query)
        for variant_dict in collection.find(db_query).hint([('db_gene_ids', pymongo.ASCENDING), ('xpos', pymongo.ASCENDING)]):
            variant = Variant.fromJSON(variant_dict)
            self.add_annotations_to_variant(variant, project_id)
            if passes_variant_filter(variant, modified_variant_filter):
                variants.append(variant)
        variants = sorted(variants, key=lambda v: v.unique_tuple())
        return variants
