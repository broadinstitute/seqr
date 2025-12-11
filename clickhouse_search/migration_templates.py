import os
from string import Template

from settings import DATABASES, PIPELINE_RUNNER_SERVER

CLICKHOUSE_WRITER_PASSWORD = os.environ.get('CLICKHOUSE_WRITER_PASSWORD', 'clickhouse_test')
CLICKHOUSE_WRITER_USER = os.environ.get('CLICKHOUSE_WRITER_USER', 'clickhouse')

# NOTE THESE ARE CONSIDERED IMMUTABLE

ALL_VARIANTS_MV_HEADER = Template("""
CREATE MATERIALIZED VIEW `$reference_genome/$dataset_type/reference_data/$reference_dataset/all_variants_mv`
REFRESH EVERY 10 YEAR
TO `$reference_genome/$dataset_type/reference_data/$reference_dataset/all_variants`
EMPTY
""")

ALL_TO_SEQR_MV = Template("""
CREATE MATERIALIZED VIEW `$reference_genome/$dataset_type/reference_data/$reference_dataset/all_variants_to_seqr_variants_mv`
REFRESH EVERY 10 YEAR
TO `$reference_genome/$dataset_type/reference_data/$reference_dataset/seqr_variants`
EMPTY
AS SELECT
    DISTINCT ON (key)
    key,
    COLUMNS('.*') EXCEPT(version, variantId, key)
FROM `$reference_genome/$dataset_type/reference_data/$reference_dataset/all_variants` src
INNER JOIN `$reference_genome/$dataset_type/key_lookup` dst
ON assumeNotNull(src.variantId) = dst.variantId
""")

DICTIONARY_TEMPLATE = Template("""
CREATE DICTIONARY `$reference_genome/$dataset_type/reference_data/$reference_dataset`
(
$columns
)
PRIMARY KEY $primary_key
SOURCE(CLICKHOUSE(
    USER '$clickhouse_writer_user'
    PASSWORD '$clickhouse_writer_password'
    $source
))
LIFETIME(MIN 0 MAX 0)
LAYOUT($layout)
$range_block
""")

def render_search_dictionary(
    reference_genome: str,
    dataset_type: str,
    reference_dataset: str,
    columns: str,
    primary_key: str,
    source: str,
    layout: str,
):
    range_block = f"RANGE(MIN start MAX end)" if layout == "RANGE_HASHED()" else ""    
    return DICTIONARY_TEMPLATE.substitute(
        reference_genome=reference_genome,
        dataset_type=dataset_type,
        reference_dataset=reference_dataset,
        columns=columns,
        primary_key=primary_key,
        source=source,
        layout=layout,
        range_block=range_block,
        clickhouse_writer_user=CLICKHOUSE_WRITER_USER,
        clickhouse_writer_password=CLICKHOUSE_WRITER_PASSWORD,
    )


def conditionally_refresh_reference_dataset(reference_dataset: str):
    def inner(apps, schema_editor):
        if DATABASES['default']['NAME'].startswith('test_'):
            return
        requests.post(
            f"{PIPELINE_RUNNER_SERVER}/refresh_clickhouse_reference_dataset_enqueue",
            json={"reference_dataset": reference_dataset},
            timeout=60,
        )
    return inner


