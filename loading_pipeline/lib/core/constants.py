import os

MIGRATION_RUN_ID = 'hail_search_to_clickhouse_migration'
VARIANTS_MIGRATION_RUN_ID = 'annotations_to_variants_tables'
GRCH37_TO_GRCH38_LIFTOVER_REF_PATH = (
    'gs://hail-common/references/grch37_to_grch38.over.chain.gz'
    if os.environ.get('HAIL_DATAPROC') == '1'
    else 'loading_pipeline/var/liftover/grch37_to_grch38.over.chain.gz'
)
GRCH38_TO_GRCH37_LIFTOVER_REF_PATH = (
    'gs://hail-common/references/grch38_to_grch37.over.chain.gz'
    if os.environ.get('HAIL_DATAPROC') == '1'
    else 'loading_pipeline/var/liftover/grch38_to_grch37.over.chain.gz'
)
