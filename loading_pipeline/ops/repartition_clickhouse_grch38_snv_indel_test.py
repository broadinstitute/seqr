from django.db import connections

from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.test.clickhouse_schema_testcase import (
    ClickhouseSchemaTestCase,
)
from loading_pipeline.ops.repartition_clickhouse_grch38_snv_indel import (
    REPARTITION_DATABASE_NAME,
    main,
)

_ENTRIES_TABLE = f'{Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`'
_PRE_MIGRATION_ENTRIES_TABLE = (
    f'{Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries_pre_migration`'
)


class RepartitionGRCh38SnvIndelTest(ClickhouseSchemaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                CREATE TABLE {_PRE_MIGRATION_ENTRIES_TABLE}
                (
                    `key` UInt32,
                    `project_guid` LowCardinality(String),
                    `family_guid` String,
                    `is_annotated_in_any_gene` Boolean,
                    `sign` Int8,
                    `sample_type` Enum8('WES' = 1, 'WGS' = 2) MATERIALIZED CAST(1, 'Enum8(\\'WES\\' = 1, \\'WGS\\' = 2)'),
                    `calls` Array(Tuple(sampleId String, gt Nullable(Enum8('REF' = 0, 'HET' = 1, 'HOM' = 2)))) MATERIALIZED CAST([], 'Array(Tuple(sampleId String, gt Nullable(Enum8(\\'REF\\' = 0, \\'HET\\' = 1, \\'HOM\\' = 2))))'),
                    `n_partitions` UInt8 MATERIALIZED 2,
                    `partition_id` UInt8 MATERIALIZED farmHash64(family_guid) % n_partitions,
                    PROJECTION xpos_projection
                    (
                        SELECT * ORDER BY is_annotated_in_any_gene
                    )
                )
                ENGINE = CollapsingMergeTree(sign)
                PARTITION BY project_guid
                ORDER BY (project_guid, family_guid, key)
                SETTINGS deduplicate_merge_projection_mode = 'rebuild'
                """,
            )
            cursor.execute(
                f'EXCHANGE TABLES {_ENTRIES_TABLE} AND {_PRE_MIGRATION_ENTRIES_TABLE}',
            )

    @classmethod
    def tearDownClass(cls):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f'EXCHANGE TABLES {_ENTRIES_TABLE} AND {_PRE_MIGRATION_ENTRIES_TABLE}',
            )
            cursor.execute(f'DROP TABLE {_PRE_MIGRATION_ENTRIES_TABLE}')
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {_ENTRIES_TABLE}
                VALUES
                (0, 'project_a', 'family_a1', 0, 1),
                (1, 'project_a', 'family_a2', 0, 1),
                (2, 'project_a', 'family_a3', 0, 1),
                (0, 'project_b', 'family_b1', 0, 1),
                (1, 'project_b', 'family_b2', 0, 1),
                (2, 'project_b', 'family_b2', 0, 1),
                (0, 'project_c', 'family_c1', 1, 1),
                (3, 'project_c', 'family_c2', 1, 1),
                """,  # nosec B608
            )

    def tearDown(self):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS {REPARTITION_DATABASE_NAME}')
        super().tearDown()

    def test_main_all_projects(self):
        main(1, [])
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *, n_partitions, partition_id
                FROM {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
                """,  # nosec B608
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    (3, 'project_c', 'family_c2', True, 1, 2, 1),
                    (0, 'project_b', 'family_b1', 0, 1, 2, 1),
                    (1, 'project_b', 'family_b2', 0, 1, 2, 1),
                    (2, 'project_b', 'family_b2', 0, 1, 2, 1),
                    (2, 'project_a', 'family_a3', 0, 1, 2, 0),
                    (0, 'project_a', 'family_a1', 0, 1, 2, 1),
                    (1, 'project_a', 'family_a2', 0, 1, 2, 1),
                    (0, 'project_c', 'family_c1', True, 1, 2, 0),
                ],
            )

    def test_main_one_project(self):
        main(1, ['project_a'])
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *, n_partitions, partition_id
                FROM {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
                """,  # nosec B608
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    (2, 'project_a', 'family_a3', 0, 1, 2, 0),
                    (0, 'project_a', 'family_a1', 0, 1, 2, 1),
                    (1, 'project_a', 'family_a2', 0, 1, 2, 1),
                ],
            )
