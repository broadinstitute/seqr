from reference_data.models import Omim, GeneConstraint
from seqr.models import Individual

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
    REF_REF: {'not_allowed_num_alt': ['samples_no_call', 'samples_num_alt_1', 'samples_num_alt_2', 'samples']},
    REF_ALT: {'allowed_num_alt': ['samples_num_alt_1', 'samples']},
    ALT_ALT: {'allowed_num_alt': ['samples_num_alt_2', 'samples_cn_0', 'samples_cn_2', 'samples_cn_gte_4']},
    HAS_ALT: {'allowed_num_alt': ['samples_num_alt_1', 'samples_num_alt_2', 'samples']},
    HAS_REF: {
        'not_allowed_num_alt': ['samples_no_call', 'samples_num_alt_2', 'samples_cn_0', 'samples_cn_gte_4'],
    },
}

RECESSIVE = 'recessive'
X_LINKED_RECESSIVE = 'x_linked_recessive'
HOMOZYGOUS_RECESSIVE = 'homozygous_recessive'
COMPOUND_HET = 'compound_het'
ANY_AFFECTED = 'any_affected'
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
    'sv_callset': {
        'AF': 'sf',
        'filter_AF': [],
        'AC': 'sc',
        'AN': 'sn',
    },
    'callset': {
        'AF': 'AF',
        'filter_AF': [],
        'AC': 'AC',
        'AN': 'AN',
    },
    'topmed': {
        'filter_AF': [],
    },
    'g1k': {
        'filter_AF': ['g1k_POPMAX_AF'],
    },
    'exac': {
        'filter_AF': ['exac_AF_POPMAX'],
        'AC': 'exac_AC_Adj',
        'AN': 'exac_AN_Adj',
        'Hom': 'exac_AC_Hom',
        'Hemi': 'exac_AC_Hemi',
    },
    'gnomad_exomes': {
        'filter_AF': ['gnomad_exomes_FAF_AF', 'gnomad_exomes_AF_POPMAX_OR_GLOBAL'],
    },
    'gnomad_genomes': {
        'filter_AF': ['gnomad_genomes_FAF_AF', 'gnomad_genomes_AF_POPMAX_OR_GLOBAL'],
    },
}
POPULATION_FIELD_CONFIGS = {
    'AF': {'format_value': float},
    'filter_AF': {'format_value': lambda val: float(val) if val is not None else None, 'default_value': None},
    'AC': {},
    'AN': {},
    'Hom': {},
    'Hemi': {},
}
for population, pop_config in POPULATIONS.items():
    for freq_field in POPULATION_FIELD_CONFIGS.keys():
        if freq_field not in pop_config:
            freq_suffix = freq_field
            pop_config[freq_field] = '{}_{}'.format(population, freq_suffix)

DEFAULT_POP_FIELD_CONFIG = {
    'format_value': int,
    'default_value': 0,
}
POPULATION_RESPONSE_FIELD_CONFIGS = {k: dict(DEFAULT_POP_FIELD_CONFIG, **v) for k, v in POPULATION_FIELD_CONFIGS.items()}


PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
CLINVAR_SORT = {
    '_script': {
        'type': 'number',
        'script': {
           'source': """
                if (!doc.containsKey('clinvar_clinical_significance') || doc['clinvar_clinical_significance'].empty ) {
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
               'source': "(doc.containsKey('hgmd_class') && !doc['hgmd_class'].empty && doc['hgmd_class'].value == 'DM') ? 0 : 1"
            }
        }
    }],
    'in_omim': [{
        '_script': {
            'type': 'number',
            'order': 'desc',
            'script': {
                'params': {
                    'omim_gene_ids': lambda *args: [omim.gene.gene_id for omim in Omim.objects.filter(
                        phenotype_mim_number__isnull=False).only('gene__gene_id')]
                },
                'source': """
                    int total = 0; 
                    for (int i = 0; i < doc['geneIds'].length; ++i) {
                        if (params.omim_gene_ids.contains(doc['geneIds'][i])) {
                            total += 1;
                            if (doc.containsKey('mainTranscript_gene_id') && 
                                doc['geneIds'][i] == doc['mainTranscript_gene_id'].value) {
                                total += 1
                            }
                        }
                    } 
                    return total
                """
            }
        }
    }],
    'protein_consequence': [{
        '_script': {
            'type': 'number',
            'script': {
               'source': "doc.containsKey('svType') ? 4.5 : doc['mainTranscript_major_consequence_rank'].value"
            }
        }
    }],
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
                'source': """
                    int min = 1000000000; 
                    for (int i = 0; i < doc['geneIds'].length; ++i) {
                        if (params.constraint_ranks_by_gene.getOrDefault(doc['geneIds'][i], 1000000000) < min) {
                            min = params.constraint_ranks_by_gene.get(doc['geneIds'][i])
                        }
                    } 
                    return min
                """
            }
        },
    }],
    XPOS_SORT_KEY: ['xpos'],
}
POPULATION_SORTS = {
    sort: [{
        '_script': {
            'type': 'number',
            'script': {
                'params': {'field': POPULATIONS[pop_key]['AF']},
                'source': "doc.containsKey(params.field) ? (doc[params.field].empty ? 0 : doc[params.field].value) : 1"
            }
        }
    }] for sort, pop_key in {'gnomad': 'gnomad_genomes', 'exac': 'exac', '1kg': 'g1k'}.items()}
SORT_FIELDS.update(POPULATION_SORTS)
PREDICTOR_SORT_FIELDS = {
    'cadd': 'cadd_PHRED',
    'revel': 'dbnsfp_REVEL_score',
    'eigen': 'eigen_Eigen_phred',
    'mpc': 'mpc_MPC',
    'splice_ai': 'splice_ai_delta_score',
    'primate_ai': 'primate_ai_score',
}
SORT_FIELDS.update({
    sort: [{sort_field: {'order': 'desc', 'unmapped_type': True}}]
    for sort, sort_field in PREDICTOR_SORT_FIELDS.items()
})

CLINVAR_FIELDS = ['clinical_significance', 'variation_id', 'allele_id', 'gold_stars']
HGMD_FIELDS = ['accession', 'class']
GENOTYPES_FIELD_KEY = 'genotypes'
HAS_ALT_FIELD_KEYS = ['samples_num_alt_1', 'samples_num_alt_2', 'samples']
SORTED_TRANSCRIPTS_FIELD_KEY = 'sortedTranscriptConsequences'
NESTED_FIELDS = {
    field_name: {field: {} for field in fields} for field_name, fields in {
        'clinvar': CLINVAR_FIELDS,
        'hgmd': HGMD_FIELDS,
    }.items()
}

GRCH38_LOCUS_FIELD = 'rg37_locus'
CORE_FIELDS_CONFIG = {
    'alt': {},
    'contig': {'response_key': 'chrom'},
    'end': {'format_value': int},
    'filters': {'response_key': 'genotypeFilters', 'format_value': ','.join, 'default_value': []},
    'num_exon': {'response_key': 'numExon'},
    'originalAltAlleles': {'format_value': lambda alleles: [a.split('-')[-1] for a in alleles], 'default_value': []},
    'ref': {},
    'rsid': {},
    'start': {'response_key': 'pos', 'format_value': int},
    'svType': {},
    'variantId': {},
    'xpos': {'format_value': int},
    GRCH38_LOCUS_FIELD: {},
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
    'splice_ai_splice_consequence': {'response_key': 'splice_ai_consequence'},
    'dbnsfp_REVEL_score': {},
    'dbnsfp_SIFT_pred': {},
    'StrVCTVRE_score': {'response_key': 'strvctvre'},
}

QUALITY_FIELDS = {'gq': 5, 'ab': 5, 'qs': 10}
GENOTYPE_FIELDS_CONFIG = {
    'ad': {},
    'dp': {},
    'pl': {},
    'cn': {'format_value': int, 'default_value': 2},
    'end': {},
    'start': {},
    'num_exon': {},
    'defragged': {'format_value': bool},
    'sample_id': {},
    'num_alt': {'format_value': int, 'default_value': -1},
}
GENOTYPE_FIELDS_CONFIG.update({field: {} for field in QUALITY_FIELDS.keys()})

QUERY_FIELD_NAMES = list(CORE_FIELDS_CONFIG.keys()) + list(PREDICTION_FIELDS_CONFIG.keys()) + \
                    [SORTED_TRANSCRIPTS_FIELD_KEY, GENOTYPES_FIELD_KEY] + HAS_ALT_FIELD_KEYS
for field_name, fields in NESTED_FIELDS.items():
    QUERY_FIELD_NAMES += ['{}_{}'.format(field_name, field) for field in fields.keys()]
for pop_config in POPULATIONS.values():
    for pop_field in pop_config.values():
        if isinstance(pop_field, list):
            QUERY_FIELD_NAMES += pop_field
        else:
            QUERY_FIELD_NAMES.append(pop_field)
