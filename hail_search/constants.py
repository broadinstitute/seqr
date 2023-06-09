GENOME_VERSION_GRCh38_DISPLAY = 'GRCh38'

AFFECTED = 'A'
UNAFFECTED = 'N'
MALE = 'M'

VARIANT_DATASET = 'VARIANTS'
SV_DATASET = 'SV'
MITO_DATASET = 'MITO'
GCNV_KEY = f'{SV_DATASET}_WES'
SV_KEY = f'{SV_DATASET}_WGS'

VARIANT_KEY_FIELD = 'variantId'
GROUPED_VARIANTS_FIELD = 'variants'
GNOMAD_GENOMES_FIELD = 'gnomad_genomes'
SPLICE_AI_FIELD = 'splice_ai'
NEW_SV_FIELD = 'new_structural_variants'
SCREEN_KEY = 'SCREEN'
CLINVAR_KEY = 'clinvar'
HGMD_KEY = 'hgmd'

STRUCTURAL_ANNOTATION_FIELD = 'structural'
STRUCTURAL_ANNOTATION_FIELD_SECONDARY = 'structural_secondary'

POPULATION_SORTS = {
    'gnomad': [GNOMAD_GENOMES_FIELD, 'gnomad_mito'],
    'gnomad_exomes': ['gnomad_exomes'],
    'callset_af': ['callset', 'sv_callset'],
}
XPOS_SORT_KEY = 'xpos'
CONSEQUENCE_SORT_KEY = 'protein_consequence'
PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'

ALT_ALT = 'alt_alt'
REF_REF = 'ref_ref'
REF_ALT = 'ref_alt'
HAS_ALT = 'has_alt'
HAS_REF = 'has_ref'
COMP_HET_ALT = 'COMP_HET_ALT'

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
        AFFECTED: COMP_HET_ALT,
        UNAFFECTED: HAS_REF,
    },
    'de_novo': {
        AFFECTED: HAS_ALT,
        UNAFFECTED: REF_REF,
    },
}

CONSEQUENCE_RANKS = [
    "transcript_ablation",
    "splice_acceptor_variant",
    "splice_donor_variant",
    "stop_gained",
    "frameshift_variant",
    "stop_lost",
    "start_lost",  # new in v81
    "initiator_codon_variant",  # deprecated
    "transcript_amplification",
    "inframe_insertion",
    "inframe_deletion",
    "missense_variant",
    "protein_altering_variant",  # new in v79
    "splice_region_variant",
    "incomplete_terminal_codon_variant",
    "start_retained_variant",
    "stop_retained_variant",
    "synonymous_variant",
    "coding_sequence_variant",
    "mature_miRNA_variant",
    "5_prime_UTR_variant",
    "3_prime_UTR_variant",
    "non_coding_transcript_exon_variant",
    "non_coding_exon_variant",  # deprecated
    "intron_variant",
    "NMD_transcript_variant",
    "non_coding_transcript_variant",
    "nc_transcript_variant",  # deprecated
    "upstream_gene_variant",
    "downstream_gene_variant",
    "TFBS_ablation",
    "TFBS_amplification",
    "TF_binding_site_variant",
    "regulatory_region_ablation",
    "regulatory_region_amplification",
    "feature_elongation",
    "regulatory_region_variant",
    "feature_truncation",
    "intergenic_variant",
]
CONSEQUENCE_RANK_MAP = {c: i for i, c in enumerate(CONSEQUENCE_RANKS)}
SV_CONSEQUENCE_RANK_OFFSET = 4.5
SCREEN_CONSEQUENCES = ['CTCF-bound', 'CTCF-only', 'DNase-H3K4me3', 'PLS', 'dELS', 'pELS', 'DNase-only', 'low-DNase']
SCREEN_CONSEQUENCE_RANK_MAP = {c: i for i, c in enumerate(SCREEN_CONSEQUENCES)}

SV_CONSEQUENCE_RANKS = [
    'COPY_GAIN', 'LOF', 'DUP_LOF', 'DUP_PARTIAL', 'INTRONIC', 'INV_SPAN', 'NEAREST_TSS', 'PROMOTER', 'UTR',
]
SV_CONSEQUENCE_RANK_MAP = {c: i for i, c in enumerate(SV_CONSEQUENCE_RANKS)}
SV_TYPES = ['gCNV_DEL', 'gCNV_DUP', 'BND', 'CPX', 'CTX', 'DEL', 'DUP', 'INS', 'INV', 'CNV']
SV_TYPE_DISPLAYS = [t.replace('gCNV_', '') for t in SV_TYPES]
SV_DEL_INDICES = {i for i, sv_type in enumerate(SV_TYPES) if 'DEL' in SV_TYPES}
SV_TYPE_MAP = {c: i for i, c in enumerate(SV_TYPES)}
SV_TYPE_DETAILS = [
    'INS_iDEL', 'INVdel', 'INVdup', 'ME', 'ME:ALU', 'ME:LINE1', 'ME:SVA', 'dDUP', 'dDUP_iDEL', 'delINV', 'delINVdel',
    'delINVdup', 'dupINV', 'dupINVdel', 'dupINVdup',
]

CLINVAR_SIGNIFICANCES = [
    'Pathogenic', 'Pathogenic,_risk_factor', 'Pathogenic,_Affects', 'Pathogenic,_drug_response',
    'Pathogenic,_drug_response,_protective,_risk_factor', 'Pathogenic,_association', 'Pathogenic,_other',
    'Pathogenic,_association,_protective', 'Pathogenic,_protective', 'Pathogenic/Likely_pathogenic',
    'Pathogenic/Likely_pathogenic,_risk_factor', 'Pathogenic/Likely_pathogenic,_drug_response',
    'Pathogenic/Likely_pathogenic,_other', 'Likely_pathogenic,_risk_factor', 'Likely_pathogenic',
    'Conflicting_interpretations_of_pathogenicity', 'Conflicting_interpretations_of_pathogenicity,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_Affects',
    'Conflicting_interpretations_of_pathogenicity,_association,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_other,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_association',
    'Conflicting_interpretations_of_pathogenicity,_drug_response',
    'Conflicting_interpretations_of_pathogenicity,_drug_response,_other',
    'Conflicting_interpretations_of_pathogenicity,_other', 'Uncertain_significance',
    'Uncertain_significance,_risk_factor', 'Uncertain_significance,_Affects', 'Uncertain_significance,_association',
    'Uncertain_significance,_other', 'Affects', 'Affects,_risk_factor', 'Affects,_association', 'other', 'NA',
    'risk_factor', 'drug_response,_risk_factor', 'association', 'confers_sensitivity', 'drug_response', 'not_provided',
    'Likely_benign,_drug_response,_other', 'Likely_benign,_other', 'Likely_benign', 'Benign/Likely_benign,_risk_factor',
    'Benign/Likely_benign,_drug_response', 'Benign/Likely_benign,_other', 'Benign/Likely_benign', 'Benign,_risk_factor',
    'Benign,_confers_sensitivity', 'Benign,_association,_confers_sensitivity', 'Benign,_drug_response', 'Benign,_other',
    'Benign,_protective', 'Benign', 'protective,_risk_factor', 'protective',
    # In production - sort these correctly (get current list of values from actual clinvar file)
    'Pathogenic/Pathogenic,_low_penetrance', 'Pathogenic/Pathogenic,_low_penetrance|risk_factor',
    'Pathogenic/Likely_pathogenic/Pathogenic,_low_penetrance', 'Pathogenic/Likely_pathogenic/Pathogenic,_low_penetrance|other',
    'Pathogenic/Likely_pathogenic,_low_penetrance', 'Conflicting_interpretations_of_pathogenicity,_protective',
    'Likely_risk_allele', 'Uncertain_significance,_drug_response', 'Uncertain_significance/Uncertain_risk_allele',
    'Uncertain_risk_allele', 'Uncertain_risk_allele,_risk_factor', 'Uncertain_risk_allele,_protective',
    'association,_risk_factor', 'association,_drug_response', 'association,_drug_response,_risk_factor',
    'association_not_found', 'drug_response,_other', 'Likely_benign,_association', 'Benign/Likely_benign,_association',
    'Benign/Likely_benign,_drug_response,_other', 'Benign/Likely_benign,_other,_risk_factor', 'Benign,_association',
]
CLINVAR_SIG_MAP = {sig: i for i, sig in enumerate(CLINVAR_SIGNIFICANCES)}
CLINVAR_SIG_BENIGN_OFFSET = 39.5
PATH_FREQ_OVERRIDE_CUTOFF = 0.05
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
CLINVAR_PATH_SIGNIFICANCES = set(CLINVAR_SIGNFICANCE_MAP['pathogenic'])
CLINVAR_PATH_SIGNIFICANCES.update(CLINVAR_SIGNFICANCE_MAP['likely_pathogenic'])

HGMD_SIGNIFICANCES = ['DM', 'DM?', 'DP', 'DFP', 'FP', 'FTV', 'R']
HGMD_SIG_MAP = {sig: i for i, sig in enumerate(HGMD_SIGNIFICANCES)}
HGMD_CLASS_MAP = {
    'disease_causing': ['DM'],
    'likely_disease_causing': ['DM?'],
    'hgmd_other': ['DP', 'DFP', 'FP', 'FTV'],
}

PREDICTION_FIELD_ID_LOOKUP = {
    'fathmm': ['D', 'T'],
    'mut_taster': ['D', 'A', 'N', 'P'],
    'polyphen': ['D', 'P', 'B'],
    'sift': ['D', 'T'],
    'mitotip': ['likely_pathogenic',  'possibly_pathogenic', 'possibly_benign', 'likely_benign'],
    'haplogroup_defining': ['Y'],
}

CHROMOSOMES = [
    '1',
    '2',
    '3',
    '4',
    '5',
    '6',
    '7',
    '8',
    '9',
    '10',
    '11',
    '12',
    '13',
    '14',
    '15',
    '16',
    '17',
    '18',
    '19',
    '20',
    '21',
    '22',
    'X',
    'Y',
    'M',
]
CHROM_TO_XPOS_OFFSET = {chrom: (1 + i)*int(1e9) for i, chrom in enumerate(CHROMOSOMES)}
