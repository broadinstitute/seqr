from seqr.utils.constants import AFFECTED_STATUS_AFFECTED as AFFECTED, AFFECTED_STATUS_UNAFFECTED as UNAFFECTED, \
    MALE_SEXES, FEMALE_SEXES, SAMPLE_TYPE_WES, SAMPLE_TYPE_WGS, DATASET_TYPE_VARIANT_CALLS, DATASET_TYPE_SV_CALLS, \
    DATASET_TYPE_MITO_CALLS, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

MAX_VARIANTS = 10000

XPOS_SORT_KEY = 'xpos'
PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
PRIORITIZED_GENE_SORT = 'prioritized_gene'

ALT_ALT = 'alt_alt'
REF_REF = 'ref_ref'
REF_ALT = 'ref_alt'
HAS_ALT = 'has_alt'
HAS_REF = 'has_ref'

COMPOUND_HET = 'compound_het'
COMPOUND_HET_ALLOW_HOM_ALTS = 'compound_het_allow_hom_alts'
RECESSIVE = 'recessive'
X_LINKED_RECESSIVE = 'x_linked_recessive'
X_LINKED_RECESSIVE_MALE_AFFECTED = 'x_linked_recessive_male_affected'
HOMOZYGOUS_RECESSIVE = 'homozygous_recessive'
DE_NOVO = 'de_novo'
ANY_AFFECTED = 'any_affected'

RECESSIVE_FILTER = {
    AFFECTED: ALT_ALT,
    UNAFFECTED: HAS_REF,
}
INHERITANCE_FILTERS = {
    RECESSIVE: RECESSIVE_FILTER,
    X_LINKED_RECESSIVE: RECESSIVE_FILTER,
    X_LINKED_RECESSIVE_MALE_AFFECTED: {
        AFFECTED: REF_ALT,
        UNAFFECTED: HAS_REF,
    },
    HOMOZYGOUS_RECESSIVE: RECESSIVE_FILTER,
    COMPOUND_HET: {
        AFFECTED: REF_ALT,
        UNAFFECTED: HAS_REF,
    },
    DE_NOVO: {
        AFFECTED: HAS_ALT,
        UNAFFECTED: REF_REF,
    },
}

SPLICE_AI_FIELD = 'splice_ai'
SCREEN_KEY = 'SCREEN'  # uses all caps to match filter provided by the seqr UI
UTR_ANNOTATOR_KEY = 'UTRAnnotator'
EXTENDED_SPLICE_KEY = 'extended_splice_site'
EXTENDED_SPLICE_REGION_CONSEQUENCE = 'extended_intronic_splice_region_variant'
MOTIF_FEATURES_KEY = 'motif_feature'
REGULATORY_FEATURES_KEY = 'regulatory_feature'

NEW_SV_FIELD = 'new_structural_variants'
SV_CONSEQUENCES_FIELD = 'structural_consequence'
SV_TYPE_FILTER_FIELD = 'structural'
SV_ANNOTATION_TYPES = {SV_CONSEQUENCES_FIELD, SV_TYPE_FILTER_FIELD, NEW_SV_FIELD}

CLINVAR_KEY = 'clinvar'
CLINVAR_PATH_FILTER = 'pathogenic'
CLINVAR_LIKELY_PATH_FILTER = 'likely_pathogenic'
CLINVAR_CONFLICTING_P_LP = 'conflicting_p_lp'
CLINVAR_CONFLICTING_NO_P = 'conflicting_no_p'
CLINVAR_CONFLICTING = 'conflicting'
CLINVAR_PATH_SIGNIFICANCES = {CLINVAR_PATH_FILTER, CLINVAR_LIKELY_PATH_FILTER, CLINVAR_CONFLICTING_P_LP}
PATH_FREQ_OVERRIDE_CUTOFF = 0.05
CLINVAR_PATH_RANGES = [
    (CLINVAR_PATH_FILTER, 'Pathogenic', 'Pathogenic/Likely_risk_allele'),
    (CLINVAR_LIKELY_PATH_FILTER, 'Pathogenic/Likely_pathogenic', 'Likely_risk_allele'),
    (CLINVAR_CONFLICTING, 'Conflicting_classifications_of_pathogenicity', 'Conflicting_classifications_of_pathogenicity'),
    ('vus', 'Uncertain_risk_allele', 'No_pathogenic_assertion'),
    ('likely_benign', 'Likely_benign', 'Benign/Likely_benign'),
    ('benign', 'Benign/Likely_benign', 'Benign'),
]

CLINVAR_ASSERTIONS = [
    'Affects',
    'association',
    'association_not_found',
    'confers_sensitivity',
    'drug_response',
    'low_penetrance',
    'not_provided',
    'other',
    'protective',
    'risk_factor',
    'no_classification_for_the_single_variant',
    'no_classifications_from_unflagged_records',
]
CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY = 'Conflicting_classifications_of_pathogenicity'
CLINVAR_DEFAULT_PATHOGENICITY = 'No_pathogenic_assertion'
CLINVAR_PATHOGENICITIES = [
    'Pathogenic',
    'Pathogenic/Likely_pathogenic',
    'Pathogenic/Likely_pathogenic/Established_risk_allele',
    'Pathogenic/Likely_pathogenic/Likely_risk_allele',
    'Pathogenic/Likely_risk_allele',
    'Likely_pathogenic',
    'Likely_pathogenic/Likely_risk_allele',
    'Established_risk_allele',
    'Likely_risk_allele',
    CLINVAR_CONFLICTING_CLASSICATIONS_OF_PATHOGENICITY,
    'Uncertain_risk_allele',
    'Uncertain_significance/Uncertain_risk_allele',
    'Uncertain_significance',
    CLINVAR_DEFAULT_PATHOGENICITY,
    'Likely_benign',
    'Benign/Likely_benign',
    'Benign',
]

HGMD_KEY = 'hgmd'
HGMD_CLASS_FILTERS = [
    ('disease_causing', 'DM'),
    ('likely_disease_causing', 'DM?'),
]
