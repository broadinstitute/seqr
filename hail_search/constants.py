GENOME_VERSION_GRCh38_DISPLAY = 'GRCh38'

AFFECTED = 'A'
UNAFFECTED = 'N'
AFFECTED_ID = 0
UNAFFECTED_ID = 1
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
    'callset_af': ['seqr', 'sv_callset'],
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


SV_CONSEQUENCE_RANK_OFFSET = 4.5
SV_CONSEQUENCE_RANKS = [
    'COPY_GAIN', 'LOF', 'DUP_LOF', 'DUP_PARTIAL', 'INTRONIC', 'INV_SPAN', 'NEAREST_TSS', 'PROMOTER', 'UTR',
]
SV_TYPES = ['gCNV_DEL', 'gCNV_DUP', 'BND', 'CPX', 'CTX', 'DEL', 'DUP', 'INS', 'INV', 'CNV']
SV_TYPE_DISPLAYS = [t.replace('gCNV_', '') for t in SV_TYPES]
SV_DEL_INDICES = {i for i, sv_type in enumerate(SV_TYPES) if 'DEL' in SV_TYPES}
SV_TYPE_MAP = {c: i for i, c in enumerate(SV_TYPES)}
SV_TYPE_DETAILS = [
    'INS_iDEL', 'INVdel', 'INVdup', 'ME', 'ME:ALU', 'ME:LINE1', 'ME:SVA', 'dDUP', 'dDUP_iDEL', 'delINV', 'delINVdel',
    'delINVdup', 'dupINV', 'dupINVdel', 'dupINVdup',
]

PATH_FREQ_OVERRIDE_CUTOFF = 0.05
CLINVAR_PATH_SIGNIFICANCES = {'pathogenic', 'likely_pathogenic'}
CLINVAR_NO_ASSERTION = 'No_pathogenic_assertion'
CLINVAR_PATH_RANGES = [
    ('pathogenic', 'Pathogenic', 'Pathogenic/Likely_risk_allele'),
    ('likely_pathogenic', 'Pathogenic/Likely_pathogenic', 'Likely_risk_allele'),
    ('vus_or_conflicting', 'Conflicting_interpretations_of_pathogenicity', CLINVAR_NO_ASSERTION),
    ('likely_benign', 'Likely_benign', 'Benign/Likely_benign'),
    ('benign', 'Benign/Likely_benign', 'Benign'),
]
HGMD_PATH_RANGES = [
    ('disease_causing', 'DM', 'DM'),
    ('likely_disease_causing', 'DM?', 'DM?'),
    ('hgmd_other', 'DP', None),
]

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
