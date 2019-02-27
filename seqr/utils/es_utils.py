from collections import defaultdict
from django.db.models import Max
import elasticsearch
from elasticsearch_dsl import Search, Q, Index
import json
import logging
from pyliftover.liftover import LiftOver
from sys import maxint

import settings
from reference_data.models import GENOME_VERSION_GRCh38, Omim, GeneConstraint
from seqr.models import Sample, Individual
from seqr.utils.xpos_utils import get_xpos, get_chrom_pos
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.views.utils.json_utils import _to_camel_case

logger = logging.getLogger(__name__)


VARIANT_DOC_TYPE = 'variant'


def get_es_client(timeout=30):
    return elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME, timeout=timeout, retry_on_timeout=True)


# TODO once all project data is reloaded get rid of these checks
def is_nested_genotype_index(es_index):
    es_client = get_es_client()
    index = Index(es_index, using=es_client)
    try:
        field_mapping = index.get_field_mapping(fields=['samples_num_alt_1'], doc_type=[VARIANT_DOC_TYPE])
        return bool(field_mapping.get(es_index, {}).get('mappings', {}).get(VARIANT_DOC_TYPE, {}).get('samples_num_alt_1'))
    except Exception:
        return False


def _get_latest_samples_for_families(families):
    samples = Sample.objects.filter(
        individual__family__in=families,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_status=Sample.SAMPLE_STATUS_LOADED,
        elasticsearch_index__isnull=False,
    )
    sample_individual_max_loaded_date = {
        agg['individual__guid']: agg['max_loaded_date'] for agg in
        samples.values('individual__guid').annotate(max_loaded_date=Max('loaded_date'))
    }
    return [s for s in samples if s.loaded_date == sample_individual_max_loaded_date[s.individual.guid]]


def get_single_es_variant(families, variant_id):
    variants = _get_filtered_family_es_variants(families, _single_variant_id_filter(variant_id), num_results=1)
    if not variants:
        raise Exception('Variant {} not found'.format(variant_id))
    return variants[0]


def get_es_variants_for_variant_tuples(families, xpos_ref_alt_tuples):
    return _get_filtered_family_es_variants(families, _variant_id_filter(xpos_ref_alt_tuples), num_results=len(xpos_ref_alt_tuples))


def _get_filtered_family_es_variants(families, filter, num_results=100):
    samples = _get_latest_samples_for_families(families)
    es_search, family_samples_by_id, _ = _get_es_search_for_samples(samples)
    es_search = es_search.filter(filter)
    genotypes_q, _, _ = _genotype_filter(inheritance=None, family_samples_by_id=family_samples_by_id)
    es_search = es_search.filter(genotypes_q)
    variant_results, _ = _execute_search(es_search, family_samples_by_id, end_index=num_results)
    return variant_results


def get_es_variants(search_model, page=1, num_results=100):

    start_index = (page - 1) * num_results
    end_index = page * num_results
    if search_model.total_results is not None:
        end_index = min(end_index, search_model.total_results)

    previous_search_results = search_model.results or {}
    loaded_results = previous_search_results.get('all_results') or []
    if len(loaded_results) >= end_index:
        return loaded_results[start_index:end_index]
    elif len(loaded_results):
        start_index = max(start_index, len(loaded_results))

    search = search_model.variant_search.search
    sort = search_model.sort

    genes, intervals, invalid_items = parse_locus_list_items(search.get('locus', {}))
    if invalid_items:
        raise Exception('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))

    samples = _get_latest_samples_for_families(search_model.families.all())

    es_search, family_samples_by_id, elasticsearch_index = _get_es_search_for_samples(
        samples, elasticsearch_index=search_model.es_index)

    if genes or intervals:
        es_search = es_search.filter(_location_filter(genes, intervals, search['locus']))

    #  Pathogencicity and transcript consequences actas "OR" filters instead of the usual "AND"

    pathogenicity_annotations_filter = _pathogenicity_filter(search.get('pathogenicity', {}))

    allowed_consequences = None
    if search.get('annotations'):
        consequences_filter, allowed_consequences = _annotations_filter(search['annotations'])
        if pathogenicity_annotations_filter:
            pathogenicity_annotations_filter |= consequences_filter
        else:
            pathogenicity_annotations_filter = consequences_filter

    if pathogenicity_annotations_filter:
        es_search = es_search.filter(pathogenicity_annotations_filter)

    if search.get('freqs'):
        es_search = es_search.filter(_frequency_filter(search['freqs']))

    if search.get('qualityFilter'):
        es_search = es_search.filter(_quality_filter(search['qualityFilter'], family_samples_by_id))

    genotypes_q, inheritance_mode, compound_het_q = _genotype_filter(search.get('inheritance'), family_samples_by_id)
    compound_het_search = None
    if compound_het_q:
        compound_het_search = es_search.filter(compound_het_q)
    es_search = es_search.filter(genotypes_q)

    if inheritance_mode == RECESSIVE:
        # recessive results are merged with compound het results so need to load all results through the end of the requested page,
        # not just a single page's worth of results (i.e. when skipping pages need to load middle pages as well)
        start_index = len(previous_search_results.get('variant_results') or [])

    sort = _get_sort(sort)

    variant_results = []
    total_results = 0
    if inheritance_mode != COMPOUND_HET:
        es_search = es_search.sort(*sort)
        logger.info('Searching in elasticsearch index: {}'.format(elasticsearch_index))

        variant_results, total_results = _execute_search(
            es_search, family_samples_by_id, start_index=start_index, end_index=end_index)

    compound_het_results = previous_search_results.get('compound_het_results')
    total_compound_het_results = None
    if inheritance_mode in [COMPOUND_HET, RECESSIVE] and compound_het_results is None:
        # For compound het search get results from aggregation instead of top level hits
        compound_het_search = compound_het_search[:0] if compound_het_search else es_search[:0]
        compound_het_search.aggs.bucket(
            'genes', 'terms', field='geneIds', min_doc_count=2, size=10000
        ).metric(
            'vars_by_gene', 'top_hits', size=100, sort=sort, _source=QUERY_FIELD_NAMES
        )

        logger.info('Searching in elasticsearch index: {}'.format(elasticsearch_index))
        logger.info(json.dumps(compound_het_search.to_dict(), indent=2))

        response = compound_het_search.execute()

        compound_het_results, total_compound_het_results = _parse_compound_het_hits(
            response, allowed_consequences, family_samples_by_id
        )
        logger.info('Total compound het hits: {}'.format(total_compound_het_results))

    if compound_het_results:
        previous_search_results['compound_het_results'] = compound_het_results
        variant_results += previous_search_results.get('variant_results', [])
        previous_search_results['variant_results'] = variant_results

        if total_compound_het_results is not None:
            total_results += total_compound_het_results
        else:
            total_results = search_model.total_results

        grouped_variants = compound_het_results

        if variant_results:
            grouped_variants += [[var] for var in variant_results]

        # Sort merged result sets
        grouped_variants = sorted(grouped_variants, key=lambda variants: tuple(variants[0]['_sort']))

        # Only return the requested page of variants
        start_index = max(len(loaded_results), (page - 1) * num_results)
        skipped = 0
        variant_results = []
        for variants in grouped_variants:
            if skipped < start_index:
                if start_index > len(loaded_results):
                    loaded_results += variants
                skipped += len(variants)
            else:
                variant_results += variants
                if len(variant_results) >= num_results:
                    break

    # Only save contiguous pages of results
    if len(loaded_results) == start_index:
        previous_search_results['all_results'] = loaded_results + variant_results

    search_model.results = previous_search_results
    search_model.total_results = total_results
    search_model.es_index = elasticsearch_index
    search_model.save()

    return variant_results


class InvalidIndexException(Exception):
    pass


def _get_es_search_for_samples(samples, elasticsearch_index=None):
    if not elasticsearch_index:
        es_indices = {s.elasticsearch_index for s in samples}
        if len(es_indices) > 1:
            # TODO get rid of this once add multi-project support and handle duplicate variants in different indices
            raise InvalidIndexException('Samples are not all contained in the same index: {}'.format(', '.join(es_indices)))
        elif len(es_indices) < 1:
            raise InvalidIndexException('No es index found for samples')
        elif not is_nested_genotype_index(list(es_indices)[0]):
            raise InvalidIndexException('Index "{}" does not have a valid schema'.format(list(es_indices)[0]))
        elasticsearch_index = ','.join(es_indices)

    family_samples_by_id = defaultdict(dict)
    for sample in samples:
        family_samples_by_id[sample.individual.family.guid][sample.sample_id] = sample

    es_search = Search(using=get_es_client(), index=elasticsearch_index)
    return es_search, family_samples_by_id, elasticsearch_index


def _execute_search(es_search, family_samples_by_id, start_index=0, end_index=100):
    es_search = es_search[start_index:end_index]
    es_search = es_search.source(QUERY_FIELD_NAMES)

    logger.info(json.dumps(es_search.to_dict(), indent=2))

    response = es_search.execute()
    total_results = response.hits.total
    logger.info('Total hits: {} ({} seconds)'.format(total_results, response.took / 100.0))

    variant_results = [_parse_es_hit(hit, family_samples_by_id) for hit in response]
    return variant_results, total_results


def _variant_id_filter(xpos_ref_alt_tuples):
    variant_ids = []
    for xpos, ref, alt in xpos_ref_alt_tuples:
        chrom, pos = get_chrom_pos(xpos)
        if chrom == 'M':
            chrom = 'MT'
        variant_ids.append('{}-{}-{}-{}'.format(chrom, pos, ref, alt))

    return Q('terms', variantId=variant_ids)


def _single_variant_id_filter(variant_id):
    return Q('term', variantId=variant_id)


AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED

ALT_ALT = 'alt_alt'
REF_REF = 'ref_ref'
REF_ALT = 'ref_alt'
HAS_ALT = 'has_alt'
HAS_REF = 'has_ref'
GENOTYPE_QUERY_MAP = {
    REF_REF: {'not_allowed_num_alt': ['no_call', 'num_alt_1', 'num_alt_2']},
    REF_ALT: {'allowed_num_alt': ['num_alt_1']},
    ALT_ALT: {'allowed_num_alt': ['num_alt_2']},
    HAS_ALT: {'allowed_num_alt': ['num_alt_1', 'num_alt_2']},
    HAS_REF: {'not_allowed_num_alt': ['no_call', 'num_alt_2']},
}

RECESSIVE = 'recessive'
X_LINKED_RECESSIVE = 'x_linked_recessive'
HOMOZYGOUS_RECESSIVE = 'homozygous_recessive'
COMPOUND_HET = 'compound_het'
RECESSIVE_FILTER = {
    AFFECTED: ALT_ALT,
    UNAFFECTED: HAS_REF,
}
INHERITANCE_FILTERS = {
   RECESSIVE: RECESSIVE_FILTER,
   X_LINKED_RECESSIVE: RECESSIVE_FILTER,
   HOMOZYGOUS_RECESSIVE: RECESSIVE_FILTER,
   COMPOUND_HET: {
       AFFECTED: REF_ALT,
       UNAFFECTED: HAS_REF,
   },
   'de_novo': {
       AFFECTED: HAS_ALT,
       UNAFFECTED: REF_REF,
   },
}


def _genotype_filter(inheritance, family_samples_by_id):
    genotypes_q = None
    compound_het_q = None

    inheritance_mode = (inheritance or {}).get('mode')
    inheritance_filter = (inheritance or {}).get('filter') or {}

    for family_guid, samples_by_id in family_samples_by_id.items():
        if inheritance:
            family_samples_q = _genotype_inheritance_filter(inheritance_mode, inheritance_filter, samples_by_id)

            # For recessive search, should be hom recessive, x-linked recessive, or compound het
            if inheritance_mode == RECESSIVE:
                x_linked_q = _genotype_inheritance_filter(X_LINKED_RECESSIVE, inheritance_filter, samples_by_id)
                family_samples_q |= x_linked_q

                family_compound_het_q = _genotype_inheritance_filter(COMPOUND_HET, inheritance_filter, samples_by_id)
                if not compound_het_q:
                    compound_het_q = family_compound_het_q
                else:
                    compound_het_q |= family_compound_het_q
        else:
            # If no inheritance specified only return variants where at least one of the requested samples has an alt allele
            sample_ids = samples_by_id.keys()
            family_samples_q = Q('terms', samples_num_alt_1=sample_ids) | Q('terms', samples_num_alt_2=sample_ids)

        family_samples_q = Q('bool', must=[family_samples_q], _name=family_guid)
        if not genotypes_q:
            genotypes_q = family_samples_q
        else:
            genotypes_q |= family_samples_q

    return genotypes_q, inheritance_mode, compound_het_q


def _genotype_inheritance_filter(inheritance_mode, inheritance_filter, samples_by_id):
    samples_q = Q()

    individuals = [sample.individual for sample in samples_by_id.values()]

    individual_genotype_filter = inheritance_filter.get('genotype') or {}
    individual_affected_status = inheritance_filter.get('affected') or {}
    for individual in individuals:
        if not individual_affected_status.get(individual.guid):
            individual_affected_status[individual.guid] = individual.affected

    if individual_genotype_filter:
        inheritance_mode = None
        logger.info('CUSTOM GENOTYPE FILTER: {}'.format(', '.join(individual_genotype_filter.keys())))

    if inheritance_mode:
        inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

    parent_x_linked_genotypes = {}
    if inheritance_mode == X_LINKED_RECESSIVE:
        samples_q &= Q('match', contig='X')
        for individual in individuals:
            if individual_affected_status[individual.guid] == AFFECTED:
                if individual.mother and individual_affected_status[individual.mother.guid] == UNAFFECTED:
                    parent_x_linked_genotypes[individual.mother.guid] = REF_ALT
                if individual.father and individual_affected_status[individual.father.guid] == UNAFFECTED:
                    parent_x_linked_genotypes[individual.mother.guid] = REF_REF

    for sample_id, sample in samples_by_id.items():

        individual_guid = sample.individual.guid
        affected = individual_affected_status[individual_guid]

        genotype = individual_genotype_filter.get(individual_guid) \
                   or parent_x_linked_genotypes.get(individual_guid) \
                   or inheritance_filter.get(affected)

        if genotype:
            not_allowed_num_alt = GENOTYPE_QUERY_MAP[genotype].get('not_allowed_num_alt')
            num_alt_to_filter = not_allowed_num_alt or GENOTYPE_QUERY_MAP[genotype].get('allowed_num_alt')
            sample_filters = [{'samples_{}'.format(num_alt): sample_id} for num_alt in num_alt_to_filter]

            sample_q = _build_or_filter('term', sample_filters)
            if not_allowed_num_alt:
                sample_q = ~Q(sample_q)

            samples_q &= sample_q

    return samples_q


def _quality_filter(quality_filter, family_samples_by_id):
    if quality_filter.get('vcf_filter') is not None:
        quality_q = ~Q('exists', field='filters')
    else:
        quality_q = Q()

    min_ab = quality_filter.get('min_ab')
    if min_ab % 5 != 0:
        raise Exception('Invalid ab filter {}'.format(min_ab))
    min_gq = quality_filter.get('min_gq')
    if min_gq % 5 != 0:
        raise Exception('Invalid gq filter {}'.format(min_gq))

    for samples_by_id in family_samples_by_id.values():
        for sample_id in samples_by_id.keys():
            if min_ab:
                #  AB only relevant for hets
                q = ~Q('term', samples_num_alt_1=sample_id)
                q |= _build_or_filter('term', [
                    {'samples_ab_gte_{}'.format(i): sample_id} for i in range(min_ab, 50, 5)
                ])
                quality_q &= q
            if min_gq:
                quality_q &= _build_or_filter('term', [
                    {'samples_gq_gte_{}'.format(i): sample_id} for i in range(min_gq, 100, 5)
                ])

    return quality_q


def _location_filter(genes, intervals, location_filter):
    q = None
    if intervals:
        q = _build_or_filter('range', [{
            'xpos': {
                'gte': get_xpos(interval['chrom'], interval['start']),
                'lte': get_xpos(interval['chrom'], interval['end'])
            }
        } for interval in intervals])

    if genes:
        gene_q = Q('terms', geneIds=genes.keys())
        if q:
            q |= gene_q
        else:
            q = gene_q

    if location_filter.get('excludeLocations'):
        return ~q
    else:
        return q


CLINVAR_SIGNFICANCE_MAP = {
    'pathogenic': ['Pathogenic', 'Pathogenic/Likely_pathogenic'],
    'likely_pathogenic': ['Likely_pathogenic', 'Pathogenic/Likely_pathogenic'],
    'benign': ['Benign', 'Benign/Likely_benign'],
    'likely_benign': ['Likely_benign', 'Benign/Likely_benign'],
    'vus_or_conflicting': [
        'Conflicting_interpretations_of_pathogenicity',
        'Uncertain_significance',
        'not_provided',
        'other'
    ],
}

HGMD_CLASS_MAP = {
    'disease_causing': ['DM'],
    'likely_disease_causing': ['DM?'],
    'hgmd_other': ['DP', 'DFP', 'FP', 'FTV'],
}


def _pathogenicity_filter(pathogenicity):
    clinvar_filters = pathogenicity.get('clinvar', [])
    hgmd_filters = pathogenicity.get('hgmd', [])

    pathogenicity_filter = None
    if clinvar_filters:
        clinvar_clinical_significance_terms = set()
        for clinvar_filter in clinvar_filters:
            clinvar_clinical_significance_terms.update(CLINVAR_SIGNFICANCE_MAP.get(clinvar_filter, []))
        pathogenicity_filter = Q('terms', clinvar_clinical_significance=list(clinvar_clinical_significance_terms))

    if hgmd_filters:
        hgmd_class = set()
        for hgmd_filter in hgmd_filters:
            hgmd_class.update(HGMD_CLASS_MAP.get(hgmd_filter, []))

        hgmd_q = Q('terms', hgmd_class=list(hgmd_class))
        pathogenicity_filter = pathogenicity_filter | hgmd_q if pathogenicity_filter else hgmd_q

    return pathogenicity_filter


def _annotations_filter(annotations):
    vep_consequences = [ann for annotations in annotations.values() for ann in annotations]

    consequences_filter = Q('terms', transcriptConsequenceTerms=vep_consequences)

    if 'intergenic_variant' in vep_consequences:
        # for many intergenic variants VEP doesn't add any annotations, so if user selected 'intergenic_variant', also match variants where transcriptConsequenceTerms is emtpy
        consequences_filter |= ~Q('exists', field='transcriptConsequenceTerms')

    return consequences_filter, vep_consequences


POPULATIONS = {
    'callset': {
        'AF': 'AF',
        'AC': 'AC',
        'AN': 'AN',
    },
    'topmed': {
        'use_default_field_suffix': True,
    },
    'g1k': {
        'AF': 'g1k_POPMAX_AF',
    },
    'exac': {
        'AF': 'exac_AF_POPMAX',
        'AC': 'exac_AC_Adj',
        'AN': 'exac_AN_Adj',
        'Hom': 'exac_AC_Hom',
        'Hemi': 'exac_AC_Hemi',
    },
    'gnomad_exomes': {},
    'gnomad_genomes': {},
}
POPULATION_FIELD_CONFIGS = {
    'AF': {'fields': ['AF_POPMAX_OR_GLOBAL'], 'format_value': float},
    'AC': {},
    'AN': {},
    'Hom': {},
    'Hemi': {},
}


def _get_pop_freq_key(population, freq_field):
    pop_config = POPULATIONS[population]
    field_config = POPULATION_FIELD_CONFIGS[freq_field]
    freq_suffix = freq_field
    if field_config.get('fields') and not pop_config.get('use_default_field_suffix'):
        freq_suffix = field_config['fields'][-1]
    return pop_config.get(freq_field) or '{}_{}'.format(population, freq_suffix)


def _pop_freq_filter(filter_key, value):
    return Q('range', **{filter_key: {'lte': value}}) | ~Q('exists', field=filter_key)


def _frequency_filter(frequencies):
    q = Q()
    for pop, freqs in frequencies.items():
        if freqs.get('af'):
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'AF'), freqs['af'])
        elif freqs.get('ac'):
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'AC'), freqs['ac'])

        if freqs.get('hh'):
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'Hom'), freqs['hh'])
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'Hemi'), freqs['hh'])
    return q


def _build_or_filter(op, filters):
    if not filters:
        return None
    q = Q(op, **filters[0])
    for filter_kwargs in filters[1:]:
        q |= Q(op, **filter_kwargs)
    return q


PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
XPOS_SORT_KEY = 'xpos'
CLINVAR_SORT = {
    '_script': {
        'type': 'number',
        'script': {
           'source': """
                if (doc['clinvar_clinical_significance'].empty ) {
                    return 2;
                }
                String clinsig = doc['clinvar_clinical_significance'].value;
                if (clinsig.indexOf('Pathogenic') >= 0 || clinsig.indexOf('Likely_pathogenic') >= 0) {
                    return 0;
                } else if (clinsig.indexOf('Benign') >= 0 || clinsig.indexOf('Likely_benign') >= 0) {
                    return 3;
                }
                return 1;
           """
        }
    }
}

SORT_FIELDS = {
    PATHOGENICTY_SORT_KEY: [CLINVAR_SORT],
    PATHOGENICTY_HGMD_SORT_KEY: [CLINVAR_SORT, {
        '_script': {
            'type': 'number',
            'script': {
               'source': "(!doc['hgmd_class'].empty && doc['hgmd_class'].value == 'DM') ? 0 : 1"
            }
        }
    }],
    'in_omim': [{
        '_script': {
            'type': 'number',
            'script': {
                'params': {
                    'omim_gene_ids': lambda *args: [omim.gene.gene_id for omim in Omim.objects.all().only('gene__gene_id')]
                },
                'source': "params.omim_gene_ids.contains(doc['mainTranscript_gene_id'].value) ? 0 : 1"
            }
        }
    }],
    'protein_consequence': ['mainTranscript_major_consequence_rank'],
    'exac': [{_get_pop_freq_key('exac', 'AF'): {'missing': '_first'}}],
    '1kg': [{_get_pop_freq_key('g1k', 'AF'): {'missing': '_first'}}],
    'constraint': [{
        '_script': {
            'order': 'asc',
            'type': 'number',
            'script': {
                'params': {
                    'constraint_ranks_by_gene': lambda *args: {
                        constraint.gene.gene_id: constraint.mis_z_rank + constraint.pLI_rank
                        for constraint in GeneConstraint.objects.all().only('gene__gene_id', 'mis_z_rank', 'pLI_rank')}
                },
                'source': "params.constraint_ranks_by_gene.getOrDefault(doc['mainTranscript_gene_id'].value, 1000000000)"
            }
        }
    }],
    XPOS_SORT_KEY: ['xpos'],
}


def _get_sort(sort_key):
    sorts = SORT_FIELDS.get(sort_key, [])

    # Add parameters to scripts
    if len(sorts) and isinstance(sorts[0], dict) and sorts[0].get('_script', {}).get('script', {}).get('params'):
        for key, val_func in sorts[0]['_script']['script']['params'].items():
            if not (isinstance(val_func, dict) or isinstance(val_func, list)):
                sorts[0]['_script']['script']['params'][key] = val_func()

    if XPOS_SORT_KEY not in sorts:
        sorts.append(XPOS_SORT_KEY)
    return sorts


CLINVAR_FIELDS = ['clinical_significance', 'variation_id', 'allele_id', 'gold_stars']
HGMD_FIELDS = ['accession', 'class']
GENOTYPES_FIELD_KEY = 'genotypes'
SORTED_TRANSCRIPTS_FIELD_KEY = 'sortedTranscriptConsequences'
NESTED_FIELDS = {
    field_name: {field: {} for field in fields} for field_name, fields in {
        'clinvar': CLINVAR_FIELDS,
        'hgmd': HGMD_FIELDS,
    }.items()
}

CORE_FIELDS_CONFIG = {
    'alt': {},
    'contig': {'response_key': 'chrom'},
    'filters': {'response_key': 'genotypeFilters', 'format_value': lambda filters: ','.join(filters), 'default_value': []},
    'originalAltAlleles': {'format_value': lambda alleles: [a.split('-')[-1] for a in alleles], 'default_value': []},
    'ref': {},
    'rsid': {},
    'start': {'response_key': 'pos', 'format_value': long},
    'variantId': {},
    'xpos': {'format_value': long},
}
PREDICTION_FIELDS_CONFIG = {
    'cadd_PHRED': {'response_key': 'cadd'},
    'dbnsfp_DANN_score': {},
    'eigen_Eigen_phred': {},
    'dbnsfp_FATHMM_pred': {},
    'dbnsfp_GERP_RS': {'response_key': 'gerp_rs'},
    'mpc_MPC': {},
    'dbnsfp_MetaSVM_pred': {},
    'dbnsfp_MutationTaster_pred': {'response_key': 'mut_taster'},
    'dbnsfp_phastCons100way_vertebrate': {'response_key': 'phastcons_100_vert'},
    'dbnsfp_Polyphen2_HVAR_pred': {'response_key': 'polyphen'},
    'primate_ai_score': {'response_key': 'primate_ai'},
    'splice_ai_delta_score': {'response_key': 'splice_ai'},
    'dbnsfp_REVEL_score': {},
    'dbnsfp_SIFT_pred': {},
}
GENOTYPE_FIELDS_CONFIG = {
    'ab': {},
    'ad': {},
    'dp': {},
    'gq': {},
    'pl': {},
    'sample_id': {},
    'num_alt': {'format_value': int, 'default_value': -1},
}

DEFAULT_POP_FIELD_CONFIG = {
    'format_value': int,
    'default_value': 0,
}
POPULATION_RESPONSE_FIELD_CONFIGS = {k: dict(DEFAULT_POP_FIELD_CONFIG, **v) for k, v in POPULATION_FIELD_CONFIGS.items()}


QUERY_FIELD_NAMES = CORE_FIELDS_CONFIG.keys() + PREDICTION_FIELDS_CONFIG.keys() + [SORTED_TRANSCRIPTS_FIELD_KEY, GENOTYPES_FIELD_KEY]
for field_name, fields in NESTED_FIELDS.items():
    QUERY_FIELD_NAMES += ['{}_{}'.format(field_name, field) for field in fields.keys()]
for population, pop_config in POPULATIONS.items():
    for field, field_config in POPULATION_RESPONSE_FIELD_CONFIGS.items():
        if pop_config.get(field):
            QUERY_FIELD_NAMES.append(pop_config.get(field))
        QUERY_FIELD_NAMES.append('{}_{}'.format(population, field))
        QUERY_FIELD_NAMES += ['{}_{}'.format(population, custom_field) for custom_field in field_config.get('fields', [])]


def _parse_es_hit(raw_hit, family_samples_by_id):
    hit = {k: raw_hit[k] for k in QUERY_FIELD_NAMES if k in raw_hit}

    genotypes = {}
    family_guids = list(raw_hit.meta.matched_queries)
    for family_guid in family_guids:
        samples_by_id = family_samples_by_id[family_guid]
        genotypes.update({
            samples_by_id[genotype_hit['sample_id']].individual.guid: _get_field_values(genotype_hit,
                                                                                        GENOTYPE_FIELDS_CONFIG)
            for genotype_hit in hit[GENOTYPES_FIELD_KEY] if genotype_hit['sample_id'] in samples_by_id
        })

    # TODO better handling for multi-project searches
    project = family_samples_by_id[family_guids[0]].values()[0].individual.family.project

    genome_version = project.genome_version
    lifted_over_genome_version = None
    lifted_over_chrom= None
    lifted_over_pos = None
    liftover_grch38_to_grch37 = _liftover_grch38_to_grch37()
    if liftover_grch38_to_grch37 and genome_version == GENOME_VERSION_GRCh38:
        if liftover_grch38_to_grch37:
            grch37_coord = liftover_grch38_to_grch37.convert_coordinate(
                'chr{}'.format(hit['contig'].lstrip('chr')), int(hit['start'])
            )
            if grch37_coord and grch37_coord[0]:
                lifted_over_chrom = grch37_coord[0][0].lstrip('chr')
                lifted_over_pos = grch37_coord[0][1]

    populations = {
        population: _get_field_values(
            hit, POPULATION_RESPONSE_FIELD_CONFIGS, format_response_key=lambda key: key.lower(), lookup_field_prefix=population,
            get_addl_fields=lambda field, field_config:
                [pop_config.get(field)] + ['{}_{}'.format(population, custom_field) for custom_field in field_config.get('fields', [])],
        )
        for population, pop_config in POPULATIONS.items()
    }

    sorted_transcripts = [
        {_to_camel_case(k): v for k, v in transcript.to_dict().items()}
        for transcript in hit[SORTED_TRANSCRIPTS_FIELD_KEY] or []
    ]
    transcripts = defaultdict(list)
    for transcript in sorted_transcripts:
        transcripts[transcript['geneId']].append(transcript)

    result = _get_field_values(hit, CORE_FIELDS_CONFIG, format_response_key=str)
    result.update({
        field_name: _get_field_values(hit, fields, lookup_field_prefix=field_name)
        for field_name, fields in NESTED_FIELDS.items()
    })
    if hasattr(raw_hit.meta, 'sort'):
        result['_sort'] = [_parse_es_sort(sort) for sort in raw_hit.meta.sort]
    result.update({
        'projectGuid': project.guid,
        'familyGuids': family_guids,
        'genotypes': genotypes,
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
        'mainTranscript': sorted_transcripts[0] if len(sorted_transcripts) else {},
        'populations': populations,
        'predictions': _get_field_values(
            hit, PREDICTION_FIELDS_CONFIG, format_response_key=lambda key: key.split('_')[1].lower()
        ),
        'transcripts': transcripts,
    })
    return result


def _parse_compound_het_hits(response, allowed_consequences, family_samples_by_id, *args):
    family_unaffected_individual_guids = {
        family_guid: {sample.individual.guid for sample in samples_by_id.values() if sample.individual.affected == UNAFFECTED}
        for family_guid, samples_by_id in family_samples_by_id.items()
    }

    variants_by_gene = []
    for gene_agg in response.aggregations.genes.buckets:
        gene_variants = [_parse_es_hit(hit, family_samples_by_id, *args) for hit in gene_agg['vars_by_gene']]

        if allowed_consequences:
            # Variants are returned if any transcripts have the filtered consequence, but to be compound het
            # the filtered consequence needs to be present in at least one transcript in the gene of interest
            gene_variants = [variant for variant in gene_variants if any(
                transcript['majorConsequence'] in allowed_consequences for transcript in
                variant['transcripts'][gene_agg['key']]
            )]

        if len(gene_variants) > 1:
            family_guids = set(gene_variants[0]['familyGuids'])
            for variant in gene_variants[1:]:
                family_guids = family_guids.intersection(set(variant['familyGuids']))

            invalid_family_guids = set()
            for family_guid in family_guids:
                for individual_guid in family_unaffected_individual_guids[family_guid]:
                    # To be compound het all unaffected individuals need to be hom ref for at least one of the variants
                    is_family_compound_het = any(
                        variant['genotypes'].get(individual_guid, {}).get('numAlt') != 1 for variant in gene_variants)
                    if not is_family_compound_het:
                        invalid_family_guids.add(family_guid)
                        break

            family_guids -= invalid_family_guids
            if family_guids:
                for variant in gene_variants:
                    variant['familyGuids'] = list(family_guids)
                variants_by_gene.append(gene_variants)

    return variants_by_gene, sum(len(results) for results in variants_by_gene)


#  TODO move liftover to hail pipeline once upgraded to 0.2
LIFTOVER_GRCH38_TO_GRCH37 = None
def _liftover_grch38_to_grch37():
    global LIFTOVER_GRCH38_TO_GRCH37
    if not LIFTOVER_GRCH38_TO_GRCH37:
        try:
            LIFTOVER_GRCH38_TO_GRCH37 = LiftOver('hg38', 'hg19')
        except Exception as e:
            logger.warn('WARNING: Unable to set up liftover. {}'.format(e))
    return LIFTOVER_GRCH38_TO_GRCH37


def _parse_es_sort(sort):
    # ES returns these values for sort when a sort field is missing
    if sort == 'Infinity':
        sort = maxint
    elif sort == '-Infinity':
        # None of the sorts used by seqr return negative values so -1 is fine
        sort = -1
    return sort


def _get_field_values(hit, field_configs, format_response_key=_to_camel_case, get_addl_fields=None, lookup_field_prefix=''):
    return {
        field_config.get('response_key', format_response_key(field)): _value_if_has_key(
            hit,
            (get_addl_fields(field, field_config) if get_addl_fields else []) +
            ['{}_{}'.format(lookup_field_prefix, field) if lookup_field_prefix else field],
            **field_config
        )
        for field, field_config in field_configs.items()
    }


def _value_if_has_key(hit, keys, format_value=None, default_value=None, **kwargs):
    for key in keys:
        if key in hit:
            return format_value(default_value if hit[key] is None else hit[key]) if format_value else hit[key]
    return default_value
