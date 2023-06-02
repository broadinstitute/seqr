from seqr.models import Sample

SEQR_DATSETS_GS_PATH = 'gs://seqr-datasets/v02'

VCF_FILE_EXTENSIONS = ('.vcf', '.vcf.gz', '.vcf.bgz')

MAX_EXPORT_VARIANTS = 1000
MAX_NO_LOCATION_COMP_HET_FAMILIES = 100

XPOS_SORT_KEY = 'xpos'
PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
PRIORITIZED_GENE_SORT = 'prioritized_gene'

COMPOUND_HET = 'compound_het'
RECESSIVE = 'recessive'

NEW_SV_FIELD = 'new_structural_variants'
SV_ANNOTATION_TYPES = {'structural_consequence', 'structural', NEW_SV_FIELD}
ALL_DATA_TYPES = 'ALL'

DATASET_TYPES_LOOKUP = {
    data_types[0]: data_types for data_types in [
        [Sample.DATASET_TYPE_VARIANT_CALLS, Sample.DATASET_TYPE_MITO_CALLS],
        [Sample.DATASET_TYPE_SV_CALLS],
    ]
}
DATASET_TYPES_LOOKUP[ALL_DATA_TYPES] = [dt for dts in DATASET_TYPES_LOOKUP.values() for dt in dts]

