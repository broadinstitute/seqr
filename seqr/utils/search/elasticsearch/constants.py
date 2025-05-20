from django.db.models import Min

from reference_data.models import Omim, GeneConstraint
from seqr.models import Sample, PhenotypePrioritization
from seqr.utils.search.constants import XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, REF_REF, REF_ALT, ALT_ALT, HAS_ALT, HAS_REF, \
    PATHOGENICTY_HGMD_SORT_KEY, PRIORITIZED_GENE_SORT


MAX_COMPOUND_HET_GENES = 1000
MAX_INDEX_NAME_LENGTH = 4000
MAX_SEARCH_CLAUSES = 1024
MAX_INDEX_SEARCHES = 75
PREFILTER_SEARCH_SIZE = 200

GENOTYPE_QUERY_MAP = {
    REF_REF: {'not_allowed_num_alt': ['samples_no_call', 'samples_num_alt_1', 'samples_num_alt_2', 'samples']},
    REF_ALT: {'allowed_num_alt': ['samples_num_alt_1', 'samples']},
    ALT_ALT: {'allowed_num_alt': ['samples_num_alt_2', 'samples_cn_0', 'samples_cn_2', 'samples_cn_gte_4']},
    HAS_ALT: {'allowed_num_alt': ['samples_num_alt_1', 'samples_num_alt_2', 'samples']},
    HAS_REF: {
        'not_allowed_num_alt': ['samples_no_call', 'samples_num_alt_2', 'samples_cn_0', 'samples_cn_gte_4'],
    },
}

PATH_FREQ_OVERRIDE_CUTOFF = 0.05

CLINVAR_PATH_SIGNIFICANCES = {'pathogenic', 'likely_pathogenic'}

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
        'Hom': 'homozygote_count',
    },
    'topmed': {
        'filter_AF': [],
        'Het': None,
    },
    'exac': {
        'filter_AF': ['exac_AF_POPMAX'],
        'AC': 'exac_AC_Adj',
        'AN': 'exac_AN_Adj',
        'Hom': 'exac_AC_Hom',
        'Hemi': 'exac_AC_Hemi',
    },
    'gnomad_exomes': {
        'filter_AF': ['gnomad_exomes_AF_POPMAX_OR_GLOBAL'],
    },
    'gnomad_genomes': {
        'filter_AF': ['gnomad_genomes_AF_POPMAX_OR_GLOBAL'],
    },
    'gnomad_svs': {},
    'callset_heteroplasmy': {
        'AN': 'AN',
        'AC': 'AC_het',
        'AF': 'AF_het',
    },
    'gnomad_mito': {'max_hl': None},
    'gnomad_mito_heteroplasmy': {
        'AN': 'gnomad_mito_AN',
        'AC': 'gnomad_mito_AC_het',
        'AF': 'gnomad_mito_AF_het',
        'max_hl': 'gnomad_mito_max_hl'
    },
    'helix': {'max_hl': None},
    'helix_heteroplasmy': {
        'AN': 'helix_AN',
        'AC': 'helix_AC_het',
        'AF': 'helix_AF_het',
        'max_hl': 'helix_max_hl',
    }
}

POPULATION_FIELD_CONFIGS = {
    'AF': {'format_value': float},
    'filter_AF': {'format_value': lambda val: float(val) if val is not None else None, 'default_value': None},
    'AC': {},
    'AN': {},
    'Hom': {},
    'Hemi': {},
    'Het': {},
    'ID': {'format_value': str, 'default_value': None},
    'max_hl': {'format_value': float},
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


def _get_phenotype_priority_ranks_by_gene(samples, *args):
    families = {s.individual.family for s in samples}
    family_ranks = PhenotypePrioritization.objects.filter(
        individual__family=list(families)[0], rank__lte=100).values('gene_id').annotate(min_rank=Min('rank'))
    return {agg['gene_id']: agg['min_rank'] for agg in family_ranks}


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
            'script': {
                'params': {
                    'omim_gene_ids': lambda *args: [omim.gene.gene_id for omim in Omim.objects.filter(
                        phenotype_mim_number__isnull=False, gene__isnull=False).only('gene__gene_id')]
                },
                'source': "(doc.containsKey('mainTranscript_gene_id') && !doc['mainTranscript_gene_id'].empty && params.omim_gene_ids.contains(doc['mainTranscript_gene_id'].value)) ? 0 : 1",
            }
        }
    }, {
        '_script': {
            'type': 'number',
            'script': {
                'source': """
                    for (int i = 0; i < doc['geneIds'].length; ++i) {
                        if (params.omim_gene_ids.contains(doc['geneIds'][i])) {
                            return 0;
                        }
                    } 
                    return 1
                """
            }
        }
    }],
    PRIORITIZED_GENE_SORT: [{
        '_script': {
            'type': 'number',
            'script': {
                'params': {
                    'prioritized_ranks_by_gene': _get_phenotype_priority_ranks_by_gene,
                },
                'source': """
                    int min_rank = 1000000;
                    for (int i = 0; i < doc['geneIds'].length; ++i) {
                        if (params.prioritized_ranks_by_gene.getOrDefault(doc['geneIds'][i], 1000000) < min_rank) {
                            min_rank = params.prioritized_ranks_by_gene.get(doc['geneIds'][i])
                        }
                    }
                    return min_rank;
                """
            }
        }
    }],
    'protein_consequence': [{
        '_script': {
            'type': 'number',
            'script': {
               'source': "doc.containsKey('svType') ? 4.5 : (doc['mainTranscript_major_consequence_rank'].empty ? 1000 : doc['mainTranscript_major_consequence_rank'].value)"
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
    'size': [{
        '_script': {
            'type': 'number',
            'script': {
               'source': "(doc.containsKey('svType') && (doc['svType'].value == 'BND' || doc['svType'].value == 'CTX')) ? -50 : doc['start'].value - doc['end'].value"
            }
        }
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
    }] for sort, pop_key in {'gnomad': 'gnomad_genomes', 'gnomad_exomes': 'gnomad_exomes', 'callset_af': 'callset'}.items()}
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
    sort: [{sort_field: {'order': 'desc', 'unmapped_type': 'double', 'numeric_type': 'double'}}]
    for sort, sort_field in PREDICTOR_SORT_FIELDS.items()
})

SCREEN_KEY = 'SCREEN'
CLINVAR_KEY = 'clinvar'
CLINVAR_FIELDS = ['clinical_significance', 'variation_id', 'allele_id', 'gold_stars']
HGMD_KEY = 'hgmd'
HGMD_FIELDS = ['accession', 'class']
GENOTYPES_FIELD_KEY = 'genotypes'
HAS_ALT_FIELD_KEYS = ['samples_num_alt_1', 'samples_num_alt_2', 'samples']
SORTED_TRANSCRIPTS_FIELD_KEY = 'sortedTranscriptConsequences'
CANONICAL_TRANSCRIPT_FILTER = 'non_coding_transcript_exon_variant__canonical'
NESTED_FIELDS = {
    field_name: {field: {} for field in fields} for field_name, fields in {
        CLINVAR_KEY: CLINVAR_FIELDS,
        HGMD_KEY: HGMD_FIELDS,
    }.items()
}

GRCH38_LOCUS_FIELD = 'rg37_locus'
XSTOP_FIELD = 'xstop'
SPLICE_AI_FIELD = 'splice_ai'
CORE_FIELDS_CONFIG = {
    'alt': {},
    'contig': {'response_key': 'chrom'},
    'end': {'format_value': int},
    'filters': {'response_key': 'genotypeFilters', 'format_value': ','.join, 'default_value': ''},
    'num_exon': {'response_key': 'numExon'},
    'originalAltAlleles': {'format_value': lambda alleles: [a.split('-')[-1] for a in alleles], 'default_value': []},
    'ref': {},
    'rsid': {},
    'screen_region_type': {'response_key': 'screenRegionType', 'format_value': lambda types: types[0] if types else None},
    'start': {'response_key': 'pos', 'format_value': int},
    'svType': {},
    'variantId': {},
    'xpos': {'format_value': int},
    XSTOP_FIELD:  {'format_value': int},
    'rg37_locus_end': {'response_key': 'rg37LocusEnd', 'format_value': lambda locus: locus.to_dict()},
    'sv_type_detail': {'response_key': 'svTypeDetail'},
    'cpx_intervals': {
      'response_key': 'cpxIntervals',
      'format_value': lambda intervals:  [interval.to_dict() for interval in (intervals or [])],
    },
    'algorithms': {'format_value': ', '.join},
    'bothsides_support': {'response_key': 'bothsidesSupport'},
}
MITO_CORE_FIELDS_CONFIG = {
    'common_low_heteroplasmy': {'response_key': 'commonLowHeteroplasmy'},
    'high_constraint_region': {'response_key': 'highConstraintRegion'},
    'mitomap_pathogenic': {'response_key': 'mitomapPathogenic'},
}
CORE_FIELDS_CONFIG.update(MITO_CORE_FIELDS_CONFIG)
PREDICTION_FIELDS_CONFIG = {
    'cadd_PHRED': {'response_key': 'cadd'},
    'dbnsfp_DANN_score': {},
    'eigen_Eigen_phred': {},
    'dbnsfp_VEST4_score': {
        'response_key': 'vest',
        'format_value': lambda x: x and next((v for v in x.split(';') if v != '.'), None),
    },
    'dbnsfp_MutPred_score': {'response_key': 'mut_pred', 'format_value': lambda x: None if x == '-' else x},
    'mpc_MPC': {},
    'dbnsfp_MutationTaster_pred': {'response_key': 'mut_taster'},
    'dbnsfp_Polyphen2_HVAR_pred': {'response_key': 'polyphen'},
    'gnomad_non_coding_constraint_z_score': {'response_key': 'gnomad_noncoding'},
    'primate_ai_score': {'response_key': 'primate_ai'},
    'splice_ai_delta_score': {'response_key': SPLICE_AI_FIELD},
    'splice_ai_splice_consequence': {'response_key': 'splice_ai_consequence'},
    'dbnsfp_REVEL_score': {},
    'dbnsfp_SIFT_pred': {},
    'StrVCTVRE_score': {'response_key': 'strvctvre'},
}
MITO_PREDICTION_FIELDS_CONFIG = {
    'mitimpact_apogee': {},
    'hap_defining_variant': {'response_key': 'haplogroup_defining', 'format_value': lambda k: 'Y' if k else None},
    'mitotip_mitoTIP': {},
    'hmtvar_hmtVar': {},
}
PREDICTION_FIELDS_CONFIG.update(MITO_PREDICTION_FIELDS_CONFIG)

def get_prediction_response_key(key):
    return key.split('_')[1].lower()

PREDICTION_FIELD_LOOKUP = {
    field_config.get('response_key', get_prediction_response_key(field)): field
    for field, field_config in PREDICTION_FIELDS_CONFIG.items()
}
MULTI_FIELD_PREDICTORS = {
    'fathmm': ['dbnsfp_fathmm_MKL_coding_pred', 'dbnsfp_FATHMM_pred']
}
PREDICTION_FIELDS_RESPONSE_CONFIG = {k: {'response_key': k} for k, v in MULTI_FIELD_PREDICTORS.items()}
PREDICTION_FIELDS_RESPONSE_CONFIG.update(PREDICTION_FIELDS_CONFIG)

QUALITY_QUERY_FIELDS = {'gq_sv': 5}
SHARED_QUALITY_FIELDS = {'gq': 5}
SNP_QUALITY_FIELDS = {'ab': 5}
SNP_QUALITY_FIELDS.update(SHARED_QUALITY_FIELDS)
SV_QUALITY_FIELDS = {'qs': 10}
SV_QUALITY_FIELDS.update(SHARED_QUALITY_FIELDS)
QUALITY_QUERY_FIELDS.update(SNP_QUALITY_FIELDS)
QUALITY_QUERY_FIELDS.update(SV_QUALITY_FIELDS)
BASE_GENOTYPE_FIELDS_CONFIG = {
    'sample_id': {},
    'sample_type': {},
    'num_alt': {'format_value': int, 'default_value': -1},
}

GENOTYPE_FIELDS_CONFIG = {
    'ad': {},
    'dp': {},
    'pl': {},
}
GENOTYPE_FIELDS_CONFIG.update(BASE_GENOTYPE_FIELDS_CONFIG)
GENOTYPE_FIELDS_CONFIG.update({field: {} for field in SNP_QUALITY_FIELDS.keys()})
MITO_GENOTYPE_FIELDS_CONFIG = {
    'dp': {},
    'hl': {},
    'mito_cn': {},
    'contamination': {},
}
MITO_GENOTYPE_FIELDS_CONFIG.update(BASE_GENOTYPE_FIELDS_CONFIG)
MITO_GENOTYPE_FIELDS_CONFIG.update({field: {} for field in SHARED_QUALITY_FIELDS.keys()})
SV_GENOTYPE_FIELDS_CONFIG = {
    'cn': {'format_value': int, 'default_value': -1},
    'end': {},
    'start': {},
    'num_exon': {},
    'geneIds': {'response_key': 'geneIds', 'format_value': list},
    'defragged': {'format_value': bool},
    'prev_call': {'format_value': bool},
    'prev_overlap': {'format_value': bool},
    'new_call': {'format_value': bool},
    'prev_num_alt': {'format_value': lambda i: None if i is None else int(i)},
}
SV_GENOTYPE_FIELDS_CONFIG.update(BASE_GENOTYPE_FIELDS_CONFIG)
SV_GENOTYPE_FIELDS_CONFIG.update({field: {} for field in SV_QUALITY_FIELDS.keys()})

GENOTYPE_FIELDS = {
  Sample.DATASET_TYPE_VARIANT_CALLS: GENOTYPE_FIELDS_CONFIG,
  Sample.DATASET_TYPE_SV_CALLS: SV_GENOTYPE_FIELDS_CONFIG,
  Sample.DATASET_TYPE_MITO_CALLS: MITO_GENOTYPE_FIELDS_CONFIG,
}

QUERY_FIELD_NAMES = list(CORE_FIELDS_CONFIG.keys()) + list(PREDICTION_FIELDS_CONFIG.keys()) + \
                    [field for fields in MULTI_FIELD_PREDICTORS.values() for field in fields] + \
                    [SORTED_TRANSCRIPTS_FIELD_KEY, GENOTYPES_FIELD_KEY, GRCH38_LOCUS_FIELD] + HAS_ALT_FIELD_KEYS
for field_name, fields in NESTED_FIELDS.items():
    QUERY_FIELD_NAMES += ['{}_{}'.format(field_name, field) for field in fields.keys()]
for pop_config in POPULATIONS.values():
    for pop_field in pop_config.values():
        if isinstance(pop_field, list):
            QUERY_FIELD_NAMES += pop_field
        elif pop_field is not None:
            QUERY_FIELD_NAMES.append(pop_field)

SV_SAMPLE_OVERRIDE_FIELD_CONFIGS = {
    'pos': {'select_val': min, 'genotype_field': 'start'},
    'end': {'select_val': max},
    'numExon':{'select_val': max},
    'geneIds': {
        'select_val': lambda gene_lists: set([gene_id for gene_list in gene_lists for gene_id in (gene_list or [])]),
        'equal': lambda a, b: set(a or []) == set(b or [])
    },
}
