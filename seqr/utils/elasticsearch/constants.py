from reference_data.models import Omim, GeneConstraint
from seqr.models import Individual

VARIANT_DOC_TYPE = 'variant'
MAX_VARIANTS = 10000
MAX_COMPOUND_HET_GENES = 1000
MAX_INDEX_NAME_LENGTH = 7500

XPOS_SORT_KEY = 'xpos'

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
IS_OR_INHERITANCE = 'is_or_inheritance'
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
    'any_affected': {
        AFFECTED: HAS_ALT,
        IS_OR_INHERITANCE: True,
    },
}

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
for population, pop_config in POPULATIONS.items():
    for freq_field, field_config in POPULATION_FIELD_CONFIGS.items():
        if freq_field not in pop_config:
            freq_suffix = freq_field
            if field_config.get('fields') and not pop_config.get('use_default_field_suffix'):
                freq_suffix = field_config['fields'][-1]
            pop_config[freq_field] = '{}_{}'.format(population, freq_suffix)


PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
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
                    'omim_gene_ids': lambda *args: [omim.gene.gene_id for omim in Omim.objects.filter(
                        phenotype_mim_number__isnull=False).only('gene__gene_id')]
                },
                'source': "params.omim_gene_ids.contains(doc['mainTranscript_gene_id'].value) ? 0 : 1"
            }
        }
    }],
    'protein_consequence': ['mainTranscript_major_consequence_rank'],
    'gnomad': [{POPULATIONS['gnomad_genomes']['AF']: {'missing': '_first'}}],
    'exac': [{POPULATIONS['exac']['AF']: {'missing': '_first'}}],
    '1kg': [{POPULATIONS['g1k']['AF']: {'missing': '_first'}}],
    'cadd': [{'cadd_PHRED': {'order': 'desc'}}],
    'revel': [{'dbnsfp_REVEL_score': {'order': 'desc'}}],
    'eigen': [{'eigen_Eigen_phred': {'order': 'desc'}}],
    'mpc': [{'mpc_MPC': {'order': 'desc'}}],
    'splice_ai': [{'splice_ai_delta_score': {'order': 'desc'}}],
    'primate_ai': [{'primate_ai_score': {'order': 'desc'}}],
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

CLINVAR_FIELDS = ['clinical_significance', 'variation_id', 'allele_id', 'gold_stars']
HGMD_FIELDS = ['accession', 'class']
GENOTYPES_FIELD_KEY = 'genotypes'
HAS_ALT_FIELD_KEYS = ['samples_num_alt_1', 'samples_num_alt_2']
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
    'filters': {'response_key': 'genotypeFilters', 'format_value': ','.join, 'default_value': []},
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


QUERY_FIELD_NAMES = CORE_FIELDS_CONFIG.keys() + PREDICTION_FIELDS_CONFIG.keys() + \
                    [SORTED_TRANSCRIPTS_FIELD_KEY, GENOTYPES_FIELD_KEY] + HAS_ALT_FIELD_KEYS
for field_name, fields in NESTED_FIELDS.items():
    QUERY_FIELD_NAMES += ['{}_{}'.format(field_name, field) for field in fields.keys()]
for population, pop_config in POPULATIONS.items():
    for field, field_config in POPULATION_RESPONSE_FIELD_CONFIGS.items():
        if pop_config.get(field):
            QUERY_FIELD_NAMES.append(pop_config.get(field))
        QUERY_FIELD_NAMES.append('{}_{}'.format(population, field))
        QUERY_FIELD_NAMES += ['{}_{}'.format(population, custom_field) for custom_field in field_config.get('fields', [])]
