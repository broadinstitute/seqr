GENOME_VERSION_GRCh38 = 'GRCh38'
GENOME_VERSION_GRCh37 = 'GRCh37'

AFFECTED = 'A'
UNAFFECTED = 'N'
UNKNOWN_AFFECTED = 'U'
AFFECTED_ID = 0
UNAFFECTED_ID = 1
UNKNOWN_AFFECTED_ID = 2
AFFECTED_ID_MAP = {AFFECTED: AFFECTED_ID, UNAFFECTED: UNAFFECTED_ID, UNKNOWN_AFFECTED: UNKNOWN_AFFECTED_ID}

GROUPED_VARIANTS_FIELD = 'variants'
GNOMAD_GENOMES_FIELD = 'gnomad_genomes'
SPLICE_AI_FIELD = 'splice_ai'
NEW_SV_FIELD = 'new_structural_variants'
SCREEN_KEY = 'SCREEN'  # uses all caps to match filter provided by the seqr UI
UTR_ANNOTATOR_KEY = 'UTRAnnotator'
EXTENDED_SPLICE_KEY = 'extended_splice_site'
MOTIF_FEATURES_KEY = 'motif_feature'
REGULATORY_FEATURES_KEY = 'regulatory_feature'
CLINVAR_KEY = 'clinvar'
HGMD_KEY = 'hgmd'
STRUCTURAL_ANNOTATION_FIELD = 'structural'
FAMILY_GUID_FIELD = 'familyGuids'
GENOTYPES_FIELD = 'genotypes'

ANNOTATION_OVERRIDE_FIELDS = [
    SCREEN_KEY, SPLICE_AI_FIELD, NEW_SV_FIELD, STRUCTURAL_ANNOTATION_FIELD, MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY,
]
ALLOWED_TRANSCRIPTS = 'allowed_transcripts'
ALLOWED_SECONDARY_TRANSCRIPTS = 'allowed_transcripts_secondary'
HAS_ANNOTATION_OVERRIDE = 'has_annotation_override'
FILTERED_GENE_TRANSCRIPTS = 'gene_transcripts'

XPOS = 'xpos'

PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
ABSENT_PATH_SORT_OFFSET = 12.5
CONSEQUENCE_SORT = 'protein_consequence'
ALPHAMISSENSE_SORT = 'alphamissense'
OMIM_SORT = 'in_omim'

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
    AFFECTED_ID: ALT_ALT,
    UNAFFECTED_ID: HAS_REF,
}
INHERITANCE_FILTERS = {
    RECESSIVE: RECESSIVE_FILTER,
    X_LINKED_RECESSIVE: RECESSIVE_FILTER,
    'homozygous_recessive': RECESSIVE_FILTER,
    COMPOUND_HET: {
        AFFECTED_ID: COMP_HET_ALT,
        UNAFFECTED_ID: HAS_REF,
    },
    'de_novo': {
        AFFECTED_ID: HAS_ALT,
        UNAFFECTED_ID: REF_REF,
    },
}

PREFILTER_FREQ_CUTOFF = 0.01
PATH_FREQ_OVERRIDE_CUTOFF = 0.05
CLINVAR_PATH_FILTER = 'pathogenic'
CLINVAR_LIKELY_PATH_FILTER = 'likely_pathogenic'
CLINVAR_PATH_SIGNIFICANCES = {CLINVAR_PATH_FILTER, CLINVAR_LIKELY_PATH_FILTER}
CLINVAR_PATH_RANGES = [
    (CLINVAR_PATH_FILTER, 'Pathogenic', 'Pathogenic/Likely_risk_allele'),
    (CLINVAR_LIKELY_PATH_FILTER, 'Pathogenic/Likely_pathogenic', 'Likely_risk_allele'),
    ('vus_or_conflicting', 'Conflicting_classifications_of_pathogenicity', 'No_pathogenic_assertion'),
    ('likely_benign', 'Likely_benign', 'Benign/Likely_benign'),
    ('benign', 'Benign/Likely_benign', 'Benign'),
]
HGMD_PATH_RANGES = [
    ('disease_causing', 'DM', 'DM'),
    ('likely_disease_causing', 'DM?', 'DM?'),
    ('hgmd_other', 'DP', None),
]

MAX_LOAD_INTERVALS = 1000
