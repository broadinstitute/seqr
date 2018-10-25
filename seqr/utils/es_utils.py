from collections import defaultdict
from copy import deepcopy
from django.db.models import Max
import elasticsearch
from elasticsearch_dsl import Search, Q
import json
import logging
from pyliftover.liftover import LiftOver

import settings
from reference_data.models import GENOME_VERSION_GRCh38, Omim, GeneConstraint
from seqr.models import Sample, Individual
from seqr.utils.xpos_utils import get_xpos
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.views.utils.json_utils import _to_camel_case

logger = logging.getLogger(__name__)


VARIANT_DOC_TYPE = 'variant'


def get_es_client():
    return elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME)


def get_es_variants(search, individuals, sort=None, offset=0, num_results=None):

    genes, intervals, invalid_items = parse_locus_list_items(search.get('locus', {}), all_new=True)
    if invalid_items:
        raise Exception('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))

    samples = Sample.objects.filter(
        individual__in=individuals,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_status=Sample.SAMPLE_STATUS_LOADED,
        elasticsearch_index__isnull=False,
    )
    sample_individual_max_loaded_date = {
        agg['individual__guid']: agg['max_loaded_date'] for agg in
        samples.values('individual__guid').annotate(max_loaded_date=Max('loaded_date'))
    }
    samples = [s for s in samples if s.loaded_date == sample_individual_max_loaded_date[s.individual.guid]]

    elasticsearch_index = ','.join({s.elasticsearch_index for s in samples})
    elasticsearch_index = '1kg-test--both-nested'
    logger.info('Searching in elasticsearch index: {}'.format(elasticsearch_index))

    samples_by_id = {_encode_name(sample.sample_id): sample for sample in samples}

    #  TODO move liftover to hail pipeline once upgraded to 0.2
    liftover_grch38_to_grch37 = None
    try:
        liftover_grch38_to_grch37 = LiftOver('hg38', 'hg19')
    except Exception as e:
        logger.warn('WARNING: Unable to set up liftover. {}'.format(e))

    es_search = Search(using=get_es_client(), index=elasticsearch_index)

    if search.get('inheritance'):
        es_search = es_search.filter(_genotype_filter(search['inheritance'], individuals, samples_by_id))
    else:
        es_search = es_search.filter(_has_genotype_filter(samples_by_id.keys()))

    if search.get('qualityFilter'):
        es_search = es_search.filter(_quality_filter(search['qualityFilter'], samples_by_id.keys()))

    if intervals:
        es_search = es_search.filter(_interval_filter(intervals))

    if genes:
        es_search = es_search.filter(_gene_filter(genes, search['locus']))

    if search.get('annotations'):
        es_search = es_search.filter(_annotations_filter(search['annotations']))

    if search.get('freqs'):
        es_search = es_search.filter(_frequency_filter(search['freqs']))

    # sort and pagination
    es_search = es_search.sort(*_get_sort(sort, samples_by_id))
    es_search = es_search[offset: offset + num_results]

    # Only return relevant fields
    field_names = _get_query_field_names()
    es_search = es_search.source(field_names)

    logger.info(json.dumps(es_search.to_dict(), indent=2))

    response = es_search.execute()

    logger.info('Total hits: {} ({} seconds)'.format(response.hits.total, response.took/100.0))

    variant_results = [_parse_es_hit(hit, samples_by_id, liftover_grch38_to_grch37, field_names) for hit in response]

    return variant_results, response.hits.total, elasticsearch_index


AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED
ALT_ALT = 'alt_alt'
REF_REF = 'ref_ref'
REF_ALT = 'ref_alt'
HAS_ALT = 'has_alt'
HAS_REF = 'has_ref'

GENOTYPE_QUERY_MAP = {
    REF_REF: 0,
    REF_ALT: 1,
    ALT_ALT: 2,
    HAS_ALT: {'gte': 1},
    HAS_REF: {'gte': 0, 'lte': 1},
}
RANGE_FIELDS = {k for k, v in GENOTYPE_QUERY_MAP.items() if type(v) != int}

RECESSIVE = 'recessive'
X_LINKED_RECESSIVE = 'x_linked_recessive'
RECESSIVE_FILTER = {
    AFFECTED: {'genotype': ALT_ALT},
    UNAFFECTED: {'genotype': HAS_REF},
}
INHERITANCE_FILTERS = {
    X_LINKED_RECESSIVE: RECESSIVE_FILTER,
    RECESSIVE: RECESSIVE_FILTER,
    'homozygous_recessive': RECESSIVE_FILTER,
    'de_novo': {
        AFFECTED: {'genotype': HAS_ALT},
        UNAFFECTED: {'genotype': REF_REF},
    },
}


def _has_genotype_q(sample_id, genotype):
    return Q(Q('term', **{'genotypes.sample_id': sample_id}) & Q('range' if genotype in RANGE_FIELDS else 'term', **{'genotypes.num_alt': GENOTYPE_QUERY_MAP[genotype]}))


def _genotype_filter(inheritance, individuals, samples_by_id):
    inheritance_mode = inheritance.get('mode')
    inheritance_filter = inheritance.get('filter') or {}
    parent_x_linked_genotypes = {}
    q = Q()

    if inheritance_mode:
        if inheritance_filter.get(AFFECTED) and inheritance_filter.get(UNAFFECTED):
            inheritance_mode = None
        if INHERITANCE_FILTERS.get(inheritance_mode):
            inheritance_filter = INHERITANCE_FILTERS[inheritance_mode]
        if inheritance_mode == X_LINKED_RECESSIVE:
            q &= Q('match', contig='X')
            for individual in individuals:
                if individual.affected == AFFECTED:
                    parent_x_linked_genotypes.update({
                        '{}_{}'.format(individual.family.guid, individual.maternal_id): REF_ALT,
                        '{}_{}'.format(individual.family.guid, individual.paternal_id): REF_REF,
                    })
        # TODO compound het

    for sample_id, sample in samples_by_id.items():
        individual = sample.individual
        genotype = None
        filter_for_status = inheritance_filter.get(individual.affected, {})
        parent_genotype = parent_x_linked_genotypes.get('{}_{}'.format(individual.family.guid, individual.individual_id))

        if individual.affected == UNAFFECTED and parent_genotype:
            q &= _has_genotype_q(sample_id, parent_genotype)
        elif filter_for_status.get('individuals'):
            if filter_for_status['individuals'].get(individual.individual_id):
                genotype = filter_for_status['individuals'][individual.individual_id]
        elif filter_for_status.get('genotype'):
            genotype = filter_for_status['genotype']

        if genotype:
            q &= _has_genotype_q(sample_id, genotype)

    return Q('nested', path='genotypes', query=q)


def _has_genotype_filter(sample_ids):
    q = _has_genotype_q(sample_ids[0], HAS_ALT)
    for sample_id in sample_ids[1:]:
        q |= _has_genotype_q(sample_id, HAS_ALT)
    return Q('nested', path='genotypes', query=q)


def _quality_filter(quality_filter, sample_ids):
    q = None
    if quality_filter.get('vcf_filter') is not None:
        q = ~Q('exists', field='filters')

    min_ab = quality_filter['min_ab'] / 1000.0 if quality_filter.get('min_ab') else None
    min_gq = quality_filter.get('min_gq')
    for sample_id in sample_ids:
        if min_ab is not None:
            #  AB only relevant for hets
            ab_q = ~Q('term', **{'{}_num_alt'.format(sample_id): 1}) | Q('range', **{'{}_ab'.format(sample_id): {'gte': min_ab}})
            q = ab_q & q if q else ab_q
        if min_gq is not None:
            gq_q = Q('range', **{'{}_gq'.format(sample_id): {'gte': min_gq}})
            q = gq_q & q if q else gq_q
    return q


def _interval_filter(intervals):
    return _build_or_filter('range', [{
        'xpos': {
            'gte': get_xpos(interval['chrom'], interval['start']),
            'lte': get_xpos(interval['chrom'], interval['end'])
        }
    } for interval in intervals])


def _gene_filter(genes, location_filter):
    if location_filter.get('excludeLocations'):
        return ~Q('terms', geneIds=genes.keys())
    else:
        return Q('terms', geneIds=genes.keys())


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


def _annotations_filter(annotations):
    clinvar_filters = annotations.pop('clinvar', [])
    hgmd_filters = annotations.pop('hgmd', [])
    vep_consequences = [ann for annotations in annotations.values() for ann in annotations]

    consequences_filter = Q('terms', transcriptConsequenceTerms=vep_consequences)

    if clinvar_filters:
        clinvar_clinical_significance_terms = set()
        for clinvar_filter in clinvar_filters:
            clinvar_clinical_significance_terms.update(CLINVAR_SIGNFICANCE_MAP.get(clinvar_filter, []))
        consequences_filter |= Q('terms', clinvar_clinical_significance=list(clinvar_clinical_significance_terms))

    if hgmd_filters:
        hgmd_class = set()
        for hgmd_filter in hgmd_filters:
            hgmd_class.update(HGMD_CLASS_MAP.get(hgmd_filter, []))
        consequences_filter |= Q('terms', hgmd_class=list(hgmd_class))

    if 'intergenic_variant' in vep_consequences:
        # for many intergenic variants VEP doesn't add any annotations, so if user selected 'intergenic_variant', also match variants where transcriptConsequenceTerms is emtpy
        consequences_filter |= ~Q('exists', field='transcriptConsequenceTerms')

    return consequences_filter


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
        'AC': 'exac_AC_Adj',
        'AN': 'exac_AN_Adj',
        'Hom': 'exac_AC_Hom',
        'Hemi': 'exac_AC_Hemi',
    },
    'gnomad_exomes': {},
    'gnomad_genomes': {},
}
POPULATION_FIELD_CONFIGS = {
    'AF': {'fields': ['AF_POPMAX_OR_GLOBAL', 'AF_POPMAX'], 'format_value': float},
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


def _get_family_samples(samples_by_id):
    family_samples = defaultdict(list)
    for sample_id, sample in samples_by_id.items():
        family_samples[sample.individual.family.guid].append(sample_id)
    return family_samples


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
    'family_guid': [{
        '_script': {
            'type': 'string',
            'script': {
                'params': {
                    'family_samples': _get_family_samples
                },
                'source': """ArrayList families = new ArrayList(params.family_samples.keySet()); families.sort((a, b) -> a.compareTo(b)); for (family in families) { for (sample in params.family_samples[family]) {if(doc.containsKey(sample+"_num_alt") && params._source[sample+\"_num_alt\"] >= 0) {return family;}}}return "zz";"""
            }
        }
    }],
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
                'source': "params.constraint_ranks_by_gene.getOrDefault(doc['mainTranscript_gene_id'].value, 10000000)"
            }
        }
    }],
    XPOS_SORT_KEY: ['xpos'],
}


def _get_sort(sort_key, *args):
    sorts = SORT_FIELDS.get(sort_key, [])

    # Add parameters to scripts
    if len(sorts) and isinstance(sorts[0], dict) and sorts[0].get('_script', {}).get('script', {}).get('params'):
        for key, val_func in sorts[0]['_script']['script']['params'].items():
            sorts[0]['_script']['script']['params'][key] = val_func(*args)

    if XPOS_SORT_KEY not in sorts:
        sorts.append(XPOS_SORT_KEY)
    return sorts


CLINVAR_FIELDS = ['clinical_significance', 'variation_id', 'allele_id', 'gold_stars']
HGMD_FIELDS = ['accession', 'class']
TRANSCRIPT_FIELDS = [
    'gene_id', 'gene_symbol', 'lof', 'lof_flags', 'lof_filter', 'hgvsc', 'hgvsp', 'amino_acids', 'protein_position',
    'major_consequence',
]
NESTED_FIELDS = {
    field_name: {field: {} for field in fields} for field_name, fields in {
        'clinvar': CLINVAR_FIELDS,
        'hgmd': HGMD_FIELDS,
        'mainTranscript': TRANSCRIPT_FIELDS
    }.items()
}

CORE_FIELDS_CONFIG = {
    'variantId': {},
    'alt': {},
    'contig': {'response_key': 'chrom'},
    'start': {'response_key': 'pos', 'format_value': long},
    'filters': {'response_key': 'genotypeFilters', 'format_value': lambda filters: ','.join(filters), 'default_value': []},
    'origAltAlleles': {'format_value': lambda alleles: [a.split('-')[-1] for a in alleles], 'default_value': []},
    'ref': {},
    'xpos': {'format_value': long},
    'genotypes': {},
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
    'dbnsfp_REVEL_score': {},
    'dbnsfp_SIFT_pred': {},
}
GENOTYPE_FIELDS_CONFIG = {
    'ab': {},
    'ad': {},
    'dp': {},
    'gq': {},
    'pl': {},
    'num_alt': {'format_value': int, 'default_value': -1},
}

DEFAULT_POP_FIELD_CONFIG = {
    'format_value': int,
    'default_value': 0,
    'no_key_use_default': False,
}
POPULATION_RESPONSE_FIELD_CONFIGS = {k: dict(DEFAULT_POP_FIELD_CONFIG, **v) for k, v in POPULATION_FIELD_CONFIGS.items()}


def _get_query_field_names():
    field_names = CORE_FIELDS_CONFIG.keys() + PREDICTION_FIELDS_CONFIG.keys()
    for field_name, fields in NESTED_FIELDS.items():
        field_names += ['{}_{}'.format(field_name, field) for field in fields.keys()]
    for population, pop_config in POPULATIONS.items():
        for field, field_config in POPULATION_RESPONSE_FIELD_CONFIGS.items():
            if pop_config.get(field):
                field_names.append(pop_config.get(field))
            field_names.append('{}_{}'.format(population, field))
            field_names += ['{}_{}'.format(population, custom_field) for custom_field in field_config.get('fields', [])]
    return field_names


def _parse_es_hit(raw_hit, samples_by_id, liftover_grch38_to_grch37, field_names):
    hit = {k: raw_hit[k] for k in field_names if k in raw_hit}

    core_field_configs = deepcopy(CORE_FIELDS_CONFIG)
    core_field_configs['genotypes']['format_value'] = \
        lambda genotypes: {samples_by_id[genotype['sample_id']].individual.guid: _get_field_values(genotype, GENOTYPE_FIELDS_CONFIG)
                           for genotype in genotypes if genotype['sample_id'] in samples_by_id}

    result = _get_field_values(hit, core_field_configs, format_response_key=str)
    result.update({
        field_name: _get_field_values(hit, fields, lookup_field_prefix=field_name)
        for field_name, fields in NESTED_FIELDS.items()
    })

    # TODO better handling for multi-family/ project searches
    family = samples_by_id.values()[0].individual.family
    project = family.project

    genome_version = project.genome_version
    lifted_over_genome_version = None
    lifted_over_chrom= None
    lifted_over_pos = None
    if liftover_grch38_to_grch37 and genome_version == GENOME_VERSION_GRCh38:
        if liftover_grch38_to_grch37:
            grch37_coord = liftover_grch38_to_grch37.convert_coordinate(
                'chr{}'.format(hit['contig'].lstrip('chr')), int(hit['start'])
            )
            if grch37_coord and grch37_coord[0]:
                lifted_over_chrom = grch37_coord[0][0].lstrip('chr')
                lifted_over_pos = grch37_coord[0][1]

    result.update({
        'projectGuid': project.guid,
        'familyGuid': family.guid,
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
    })

    result['populations'] = {
        population: _get_field_values(
            hit, POPULATION_RESPONSE_FIELD_CONFIGS, format_response_key=lambda key: key.lower(), lookup_field_prefix=population,
            get_addl_fields=lambda field, field_config:
                [pop_config.get(field)] + ['{}_{}'.format(population, custom_field) for custom_field in field_config.get('fields', [])],
        )
        for population, pop_config in POPULATIONS.items()
    }

    result['predictions'] = _get_field_values(
        hit, PREDICTION_FIELDS_CONFIG, format_response_key=lambda key: key.split('_')[1].lower()
    )

    return result


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


def _value_if_has_key(hit, keys, format_value=None, default_value=None, no_key_use_default=True, **kwargs):
    for key in keys:
        if key in hit:
            return format_value(default_value if hit[key] is None else hit[key]) if format_value else hit[key]
    return default_value if no_key_use_default else None


# make encoded values as human-readable as possible
#  TODO store sample ids already encoded
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


def _encode_name(s):
    '''Applies a reversable encoding to the special chars in the given name or id string, and returns the result.
    Among other things, the encoded string is a valid elasticsearch or mongodb field name.

    See:
    https://discuss.elastic.co/t/special-characters-in-field-names/10658/2
    https://discuss.elastic.co/t/illegal-characters-in-elasticsearch-field-names/17196/2
    '''
    s = s.replace(ES_FIELD_NAME_ESCAPE_CHAR, 2 * ES_FIELD_NAME_ESCAPE_CHAR)
    for original_value, encoded in ES_FIELD_NAME_SPECIAL_CHAR_MAP.items():
        s = s.replace(original_value, encoded)
    if s[0] in ES_FIELD_NAME_BAD_LEADING_CHARS:
        s = ES_FIELD_NAME_ESCAPE_CHAR + s
    return s

