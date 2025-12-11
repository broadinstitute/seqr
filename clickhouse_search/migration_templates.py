from string import Template

from settings import DATABASES, PIPELINE_RUNNER_SERVER

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
AS
EMPTY
SELECT
    DISTINCT ON (key)
    key,
    COLUMNS('.*') EXCEPT(version, variantId, key)
FROM `$reference_genome/$dataset_type/reference_data/$reference_dataset/all_variants` src
INNER JOIN `$reference_genome/$dataset_type/key_lookup` dst
ON assumeNotNull(src.variantId) = dst.variantId
""")


def conditionally_refresh_reference_dataset(reference_dataset: str):
    def inner(apps, schema_editor):
        if DATABASES['default']['NAME'].startswith('test_'):
            return
        requests.post(
            f"{PIPELINE_RUNNER_SERVER}/refresh_clickhouse_reference_dataset_enqueue",
            json={"reference_dataset": 'genomad_genomes'},
            timeout=60,
        )
    return inner


