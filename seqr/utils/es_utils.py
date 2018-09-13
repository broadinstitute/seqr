from django.db.models import Max
import elasticsearch
from elasticsearch_dsl import Search, Q
import json
import logging
from pyliftover.liftover import LiftOver

import settings
from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Sample, Individual
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.gene_utils import parse_locus_list_items

logger = logging.getLogger(__name__)


VARIANT_DOC_TYPE = 'variant'


def get_es_client():
    return elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME)


VARIANT_FIELDS = [
    'xpos', 'ref', 'alt', 'cadd_PHRED', 'dbnsfp_DANN_score', 'eigen_Eigen_phred', 'dbnsfp_Eigen_phred',
    'dbnsfp_FATHMM_pred', 'dbnsfp_GERP_RS', 'dbnsfp_phastCons100way_vertebrate', 'mpc_MPC', 'dbnsfp_MetaSVM_pred',
    'dbnsfp_MutationTaster_pred', 'dbnsfp_Polyphen2_HVAR_pred', 'primate_ai_score', 'dbnsfp_REVEL_score',
    'dbnsfp_SIFT_pred', 'mainTranscript_major_consequence', 'mainTranscript_gene_symbol', 'mainTranscript_symbol',
    'mainTranscript_lof', 'mainTranscript_lof_flags', 'mainTranscript_lof_filter', 'mainTranscript_hgvsc',
    'mainTranscript_hgvsp', 'mainTranscript_amino_acids', 'mainTranscript_protein_position', 'contig',
    'clinvar_clinical_significance', 'clinvar_variation_id', 'clinvar_allele_id', 'clinvar_gold_stars',
    'hgmd_accession', 'hgmd_class', 'codingGeneIds', 'geneIds', 'filters', 'originalAltAlleles', 'AF', 'AC', 'AN',
    'topmed_AF', 'topmed_AC', 'topmed_AN', 'g1k_POPMAX_AF', 'g1k_AF', 'g1k_AC', 'g1k_AN', 'exac_AF_POPMAX', 'exac_AF',
    'exac_AC_Adj', 'exac_AN_Adj', 'exac_AC_Hom', 'exac_AC_Hemi', 'gnomad_exomes_AF_POPMAX_OR_GLOBAL',
    'gnomad_exomes_AF_POPMAX', 'gnomad_exomes_AF', 'gnomad_exomes_AC', 'gnomad_exomes_AN', 'gnomad_exomes_Hom',
    'gnomad_exomes_Hemi', 'gnomad_genomes_AF_POPMAX_OR_GLOBAL', 'gnomad_genomes_AF_POPMAX', 'gnomad_genomes_AF',
    'gnomad_genomes_AC', 'gnomad_genomes_AN', 'gnomad_genomes_Hom', 'gnomad_genomes_Hemi', 'start',
]
GENOTYPE_FIELDS = ['ab', 'ad', 'dp', 'gq', 'pl', 'num_alt']


def get_es_variants(search, individuals):
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
    logger.info('Searching in elasticsearch index: {}'.format(elasticsearch_index))

    samples_by_id = {_encode_name(sample.sample_id): sample for sample in samples}

    #  TODO move liftover to hail pipeline once upgraded to 0.2
    liftover_grch38_to_grch37 = None
    try:
        liftover_grch38_to_grch37 = LiftOver('hg38', 'hg19')
    except Exception as e:
        logger.warn('WARNING: Unable to set up liftover. {}'.format(e))

    es_search = Search(using=get_es_client(), index=elasticsearch_index)

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

    if search.get('inheritance'):
        es_search = es_search.filter(_genotype_filter(search['inheritance'], individuals, samples_by_id))

    # Only return relevant fields
    field_names = []
    for sample_id in samples_by_id.keys():
        field_names += ['{}_{}'.format(sample_id, field) for field in GENOTYPE_FIELDS]
    field_names += VARIANT_FIELDS
    es_search = es_search.source(field_names)

    # TODO sort and pagination
    es_search = es_search.sort('xpos')
    es_search = es_search[0:100]
    logger.info(json.dumps(es_search.to_dict()))

    response = es_search.execute()

    logger.info('=====')
    logger.info('Total hits: {} ({} seconds)'.format(response.hits.total, response.took/100.0))

    variant_results = [_parse_es_hit(hit, samples_by_id, liftover_grch38_to_grch37, field_names) for hit in response]

    return variant_results


def _has_genotype_filter(sample_ids):
    return _build_or_filter('range', [{'{}_num_alt'.format(sample_id): {'gte': 1}} for sample_id in sample_ids])


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


POP_AF_SUFFIX = {
    'g1k': 'POPMAX_AF',
    'topmed': 'AF',
}
POP_HH_SUFFIX = {
    'exac': 'AC_',
}


def _pop_freq_filter(filter_key, value):
    return Q('range', **{filter_key: {'lte': value}}) | ~Q('exists', field=filter_key)


def _frequency_filter(frequencies):
    q = None
    for pop, freqs in frequencies.items():
        if freqs.get('af'):
            filter_key = 'AF' if pop == 'callset' else '{}_{}'.format(pop, POP_AF_SUFFIX.get(pop, 'AF_POPMAX'))
            freq_q = _pop_freq_filter(filter_key, freqs['af'])
            q = freq_q & q if q else freq_q
        elif freqs.get('ac'):
            filter_key = 'AC' if pop == 'callset' else '{}_AC'.format(pop)
            freq_q = _pop_freq_filter(filter_key, freqs['ac'])
            q = freq_q & q if q else freq_q

        if freqs.get('hh'):
            freq_q = _pop_freq_filter('{}_{}Hom'.format(pop, POP_HH_SUFFIX.get(pop, '')), freqs['hh'])
            freq_q &= _pop_freq_filter('{}_{}Hemi'.format(pop, POP_HH_SUFFIX.get(pop, '')), freqs['hh'])
            q = freq_q & q if q else freq_q
    return q


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


def _genotype_filter(inheritance, individuals, samples_by_id):
    inheritance_mode = inheritance.get('mode')
    inheritance_filter = inheritance.get('filter') or {}
    parent_x_linked_num_alt = {}
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
                    parent_x_linked_num_alt.update({
                        individual.maternal_id: GENOTYPE_QUERY_MAP[REF_ALT],
                        individual.paternal_id: GENOTYPE_QUERY_MAP[REF_REF],
                    })
        # TODO compound het

    for sample_id, sample in samples_by_id.items():
        genotype = None
        filter_for_status = inheritance_filter.get(sample.individual.affected, {})

        if sample.individual.affected == UNAFFECTED and parent_x_linked_num_alt.get(sample.individual.individual_id):
            q &= Q('term', **{'{}_num_alt'.format(sample_id): parent_x_linked_num_alt[sample.individual.individual_id]})
        elif filter_for_status.get('individuals'):
            if filter_for_status['individuals'].get(sample.individual.individual_id):
                genotype = filter_for_status['individuals'][sample.individual.individual_id]
        elif filter_for_status.get('genotype'):
            genotype = filter_for_status['genotype']

        if genotype:
            q &= Q('range' if genotype in RANGE_FIELDS else 'term', **{'{}_num_alt'.format(sample_id): GENOTYPE_QUERY_MAP[genotype]})

    return q


def _build_or_filter(op, filters):
    if not filters:
        return None
    q = Q(op, **filters[0])
    for filter_kwargs in filters[1:]:
        q |= Q(op, **filter_kwargs)
    return q


POLYPHEN_MAP = {
    'D': 'probably_damaging',
    'P': 'possibly_damaging',
    'B': 'benign',
    '.': None,
    '': None
}
SIFT_MAP = {
    'D': 'damaging',
    'T': 'tolerated',
    '.': None,
    '': None
}
FATHMM_MAP = {
    'D': 'damaging',
    'T': 'tolerated',
    '.': None,
    '': None
}
MUTTASTER_MAP = {
    'A': 'disease_causing',
    'D': 'disease_causing',
    'N': 'polymorphism',
    'P': 'polymorphism',
    '.': None,
    '': None
}
METASVM_MAP = {
    'D': 'damaging',
    'T': 'tolerated',
    '.': None,
    '': None
}


def _parse_es_hit(raw_hit, samples_by_id, liftover_grch38_to_grch37, field_names):
    hit = {k: raw_hit[k] for k in field_names if k in raw_hit}

    matched_sample_ids = [sample_id for sample_id in samples_by_id.keys() if any(k for k in hit.keys() if k.startswith(sample_id))]
    genotypes = {}
    for sample_id in matched_sample_ids:
        num_alt_key = '{}_num_alt'.format(sample_id)
        num_alt = int(hit[num_alt_key]) if hit.get(num_alt_key) is not None else -1

        # TODO don't pass down alleles, have UI do this
        if num_alt == 0:
            alleles = [hit['ref'], hit['ref']]
        elif num_alt == 1:
            alleles = [hit['ref'], hit['alt']]
        elif num_alt == 2:
            alleles = [hit['alt'], hit['alt']]
        elif num_alt == -1:
            alleles = []
        else:
            raise ValueError('Invalid num_alt: ' + str(num_alt))

        genotypes[samples_by_id[sample_id].individual.guid] = {
            'ab': hit.get('{}_ab'.format(sample_id)),
            'ad': hit.get('{}_ad'.format(sample_id)),
            'alleles': alleles,
            'dp': hit.get('{}_dp'.format(sample_id)),
            'gq': hit.get('{}_gq'.format(sample_id)) or '',
            'numAlt': num_alt,
            'pl': hit.get('{}_pl'.format(sample_id)),
        }

    # TODO better handling for multi-family/ project searches
    family = samples_by_id[matched_sample_ids[0]].individual.family
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

    return {
        'variantId': '{}-{}-{}'.format(hit['xpos'], hit['ref'], hit['alt']),
        'projectGuid': project.guid,
        'familyGuid': family.guid,
        'alt': hit['alt'],
        'annotation': {
            'cadd_phred': hit.get('cadd_PHRED'),
            'dann_score': hit.get('dbnsfp_DANN_score'),
            'eigen_phred': hit.get('eigen_Eigen_phred', hit.get('dbnsfp_Eigen_phred')),
            'fathmm': FATHMM_MAP.get((hit.get('dbnsfp_FATHMM_pred') or '').split(';')[0]),
            'gerp_rs': _float_if_has_key(hit, ['dbnsfp_GERP_RS']),
            'phastcons100vert': _float_if_has_key(hit, ['dbnsfp_phastCons100way_vertebrate']),
            'mpc_score': hit.get('mpc_MPC'),
            'metasvm': METASVM_MAP.get((hit.get('dbnsfp_MetaSVM_pred') or '').split(';')[0]),
            'mut_taster': MUTTASTER_MAP.get((hit.get('dbnsfp_MutationTaster_pred') or '').split(';')[0]),
            'polyphen': POLYPHEN_MAP.get((hit.get('dbnsfp_Polyphen2_HVAR_pred') or '').split(';')[0]),
            'primate_ai_score': hit.get('primate_ai_score'),
            'revel_score': hit.get('dbnsfp_REVEL_score'),
            'sift': SIFT_MAP.get((hit.get('dbnsfp_SIFT_pred') or '').split(';')[0]),
            'vepConsequence': hit.get('mainTranscript_major_consequence', ''),
            'mainTranscript': {
                'symbol': hit.get('mainTranscript_gene_symbol') or hit.get('mainTranscript_symbol'),
                'lof': hit.get('mainTranscript_lof'),
                'lofFlags': hit.get('mainTranscript_lof_flags'),
                'lofFilter': hit.get('mainTranscript_lof_filter'),
                'hgvsc': hit.get('mainTranscript_hgvsc'),
                'hgvsp': hit.get('mainTranscript_hgvsp'),
                'aminoAcids': hit.get('mainTranscript_amino_acids'),
                'proteinPosition': hit.get('mainTranscript_protein_position'),
            },
        },
        'chrom': hit['contig'],
        'clinvar': {
            'clinsig': (hit.get('clinvar_clinical_significance') or '').lower(),
            'variantId': hit.get('clinvar_variation_id'),
            'alleleId': hit.get('clinvar_allele_id'),
            'goldStars': hit.get('clinvar_gold_stars'),
        },
        'hgmd': {
            'accession': hit.get('hgmd_accession'),
            'class': hit.get('hgmd_class'),
        },
        'geneIds': list(hit.get('codingGeneIds') or []) or list(hit.get('geneIds') or []),
        'genotypeFilters': ','.join(hit['filters'] or []),
        'genotypes': genotypes,
        'genomeVersion': genome_version,
        'liftedOverGenomeVersion': lifted_over_genome_version,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
        'origAltAlleles':  [a.split('-')[-1] for a in hit.get('originalAltAlleles', [])],
        'populations': {
            'callset': {
                'af': _float_if_has_key(hit, ['AF']),
                'ac': _int_if_has_key(hit, ['AC']),
                'an': _int_if_has_key(hit, ['AN']),
            },
            'topmed': {
                'af': _float_if_has_key(hit, ['topmed_AF']),
                'ac': _int_if_has_key(hit, ['topmed_AC']),
                'an': _int_if_has_key(hit, ['topmed_AN']),
            },
            'g1k': {
                'af': _float_if_has_key(hit, ['g1k_POPMAX_AF', 'g1k_AF']),
                'ac': _int_if_has_key(hit, ['g1k_AC']),
                'an': _int_if_has_key(hit, ['g1k_AN']),
            },
            'exac': {
                'af': _float_if_has_key(hit, ['exac_AF_POPMAX', 'exac_AF']),
                'ac': _int_if_has_key(hit, ['exac_AC_Adj']),
                'an': _int_if_has_key(hit, ['exac_AN_Adj']),
                'hom':  _int_if_has_key(hit, ['exac_AC_Hom']),
                'hemi': _int_if_has_key(hit, ['exac_AC_Hemi']),
            },
            'gnomad_exomes': {
                'af': _float_if_has_key(hit, ['gnomad_exomes_AF_POPMAX_OR_GLOBAL', 'gnomad_exomes_AF_POPMAX', 'gnomad_exomes_AF']),
                'ac': _int_if_has_key(hit, ['gnomad_exomes_AC']),
                'an': _int_if_has_key(hit, ['gnomad_exomes_AN']),
                'hom': _int_if_has_key(hit, ['gnomad_exomes_Hom']),
                'hemi': _int_if_has_key(hit, ['gnomad_exomes_Hemi']),
            },
            'gnomad_genomes': {
                'af': _float_if_has_key(hit, ['gnomad_genomes_AF_POPMAX_OR_GLOBAL', 'gnomad_genomes_AF_POPMAX', 'gnomad_genomes_AF']),
                'ac': _int_if_has_key(hit, ['gnomad_genomes_AC']),
                'an': _int_if_has_key(hit, ['gnomad_genomes_AN']),
                'hom': _int_if_has_key(hit, ['gnomad_genomes_Hom']),
                'hemi': _int_if_has_key(hit, ['gnomad_genomes_Hemi']),
            },
        },
        'pos': long(hit['start']),
        'ref': hit['ref'],
        'xpos': long(hit['xpos']),
    }


def _float_if_has_key(hit, keys):
    for key in keys:
        if key in hit:
            return float(hit[key] or 0.0)
    return None


def _int_if_has_key(hit, keys):
    for key in keys:
        if key in hit:
            return int(hit[key] or 0)
    return None


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

