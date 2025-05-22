from seqr.models import Individual

VCF_FILE_EXTENSIONS = ('.vcf', '.vcf.gz', '.vcf.bgz')

MAX_VARIANTS = 10000
MAX_EXPORT_VARIANTS = 1000
MAX_NO_LOCATION_COMP_HET_FAMILIES = 100

XPOS_SORT_KEY = 'xpos'
PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
PRIORITIZED_GENE_SORT = 'prioritized_gene'

AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED
MALE_SEXES = Individual.MALE_SEXES

ALT_ALT = 'alt_alt'
REF_REF = 'ref_ref'
REF_ALT = 'ref_alt'
HAS_ALT = 'has_alt'
HAS_REF = 'has_ref'

COMPOUND_HET = 'compound_het'
RECESSIVE = 'recessive'
X_LINKED_RECESSIVE = 'x_linked_recessive'
HOMOZYGOUS_RECESSIVE = 'homozygous_recessive'
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

SPLICE_AI_FIELD = 'splice_ai'
SCREEN_KEY = 'SCREEN'  # uses all caps to match filter provided by the seqr UI
UTR_ANNOTATOR_KEY = 'UTRAnnotator'
EXTENDED_SPLICE_KEY = 'extended_splice_site'
EXTENDED_SPLICE_REGION_CONSEQUENCE = 'extended_intronic_splice_region_variant'
MOTIF_FEATURES_KEY = 'motif_feature'
REGULATORY_FEATURES_KEY = 'regulatory_feature'

NEW_SV_FIELD = 'new_structural_variants'
SV_ANNOTATION_TYPES = {'structural_consequence', 'structural', NEW_SV_FIELD}
ALL_DATA_TYPES = 'ALL'

CLINVAR_KEY = 'clinvar'
CLINVAR_PATH_FILTER = 'pathogenic'
CLINVAR_LIKELY_PATH_FILTER = 'likely_pathogenic'
CLINVAR_PATH_SIGNIFICANCES = {CLINVAR_PATH_FILTER, CLINVAR_LIKELY_PATH_FILTER}
PATH_FREQ_OVERRIDE_CUTOFF = 0.05
CLINVAR_PATH_RANGES = [
    (CLINVAR_PATH_FILTER, 'Pathogenic', 'Pathogenic/Likely_risk_allele'),
    (CLINVAR_LIKELY_PATH_FILTER, 'Pathogenic/Likely_pathogenic', 'Likely_risk_allele'),
    ('vus_or_conflicting', 'Conflicting_classifications_of_pathogenicity', 'No_pathogenic_assertion'),
    ('likely_benign', 'Likely_benign', 'Benign/Likely_benign'),
    ('benign', 'Benign/Likely_benign', 'Benign'),
]

HGMD_KEY = 'hgmd'
HGMD_CLASS_FILTERS = [
    ('disease_causing', 'DM'),
    ('likely_disease_causing', 'DM?'),
]
