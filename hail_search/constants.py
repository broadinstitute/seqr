GENOME_VERSION_GRCh38_DISPLAY = 'GRCh38'

AFFECTED = 'A'
UNAFFECTED = 'N'
AFFECTED_ID = 0
UNAFFECTED_ID = 1
MALE = 'M'

VARIANT_DATASET = 'VARIANTS'

VARIANT_KEY_FIELD = 'variantId'
GNOMAD_GENOMES_FIELD = 'gnomad_genomes'
SPLICE_AI_FIELD = 'splice_ai'
NEW_SV_FIELD = 'new_structural_variants'
SCREEN_KEY = 'SCREEN'  # uses all caps to match filter provided by the seqr UI
CLINVAR_KEY = 'clinvar'
HGMD_KEY = 'hgmd'
STRUCTURAL_ANNOTATION_FIELD = 'structural'

ANNOTATION_OVERRIDE_FIELDS = [
    SCREEN_KEY, SPLICE_AI_FIELD, NEW_SV_FIELD, STRUCTURAL_ANNOTATION_FIELD,
]

XPOS = 'xpos'

ALT_ALT = 'alt_alt'
REF_REF = 'ref_ref'
REF_ALT = 'ref_alt'
HAS_ALT = 'has_alt'
HAS_REF = 'has_ref'
COMP_HET_ALT = 'COMP_HET_ALT'

RECESSIVE = 'recessive'
X_LINKED_RECESSIVE = 'x_linked_recessive'
COMPOUND_HET = 'compound_het'
ANY_AFFECTED = 'any_affected'
RECESSIVE_FILTER = {
    AFFECTED: ALT_ALT,
    UNAFFECTED: HAS_REF,
}
INHERITANCE_FILTERS = {
    RECESSIVE: RECESSIVE_FILTER,
    X_LINKED_RECESSIVE: RECESSIVE_FILTER,
    'homozygous_recessive': RECESSIVE_FILTER,
    COMPOUND_HET: {
        AFFECTED: COMP_HET_ALT,
        UNAFFECTED: HAS_REF,
    },
    'de_novo': {
        AFFECTED: HAS_ALT,
        UNAFFECTED: REF_REF,
    },
}

CLINVAR_PATH_RANGES = [
    ('pathogenic', 'Pathogenic', 'Pathogenic/Likely_risk_allele'),
    ('likely_pathogenic', 'Pathogenic/Likely_pathogenic', 'Likely_risk_allele'),
    ('vus_or_conflicting', 'Conflicting_interpretations_of_pathogenicity', 'No_pathogenic_assertion'),
    ('likely_benign', 'Likely_benign', 'Benign/Likely_benign'),
    ('benign', 'Benign/Likely_benign', 'Benign'),
]
HGMD_PATH_RANGES = [
    ('disease_causing', 'DM', 'DM'),
    ('likely_disease_causing', 'DM?', 'DM?'),
    ('hgmd_other', 'DP', None),
]
