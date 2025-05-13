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

NEW_SV_FIELD = 'new_structural_variants'
SV_ANNOTATION_TYPES = {'structural_consequence', 'structural', NEW_SV_FIELD}
ALL_DATA_TYPES = 'ALL'
