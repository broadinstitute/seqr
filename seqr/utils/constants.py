"""Constants shared between seqr.models, reference_data.models, and clickhouse_search - kept here,
rather than on those Django model classes, so clickhouse_search (and loading_pipeline's minimal
test settings) can depend on these plain values without importing the Postgres/guardian-backed
seqr.models/reference_data.models apps.
"""

# Individual
SEX_MALE = 'M'
SEX_FEMALE = 'F'
SEX_UNKNOWN = 'U'
FEMALE_ANEUPLOIDIES = ['XXX', 'X0']
MALE_ANEUPLOIDIES = ['XXY', 'XYY']
FEMALE_SEXES = [SEX_FEMALE, *FEMALE_ANEUPLOIDIES]
MALE_SEXES = [SEX_MALE, *MALE_ANEUPLOIDIES]

AFFECTED_STATUS_AFFECTED = 'A'
AFFECTED_STATUS_UNAFFECTED = 'N'
AFFECTED_STATUS_UNKNOWN = 'U'

# Dataset
SAMPLE_TYPE_WES = 'WES'
SAMPLE_TYPE_WGS = 'WGS'
DATASET_TYPE_VARIANT_CALLS = 'SNV_INDEL'
DATASET_TYPE_SV_CALLS = 'SV'
DATASET_TYPE_MITO_CALLS = 'MITO'

# reference_data genome versions
GENOME_VERSION_GRCh37 = '37'
GENOME_VERSION_GRCh38 = '38'
