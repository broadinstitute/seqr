from typing import ClassVar

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
    # Fixture data for the properly migrated `GRCh38/SNV_INDEL/entries` table,
    # loaded normally via the shared clickhouse schema/fixture setup.
    fixtures: ClassVar = ['clickhouse_test']

    def setUp(self):
        super().setUp()
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT key, project_guid, family_guid, is_annotated_in_any_gene, sign
                FROM {_ENTRIES_TABLE}
                """,
            )
            self.entries_rows = cursor.fetchall()

            # This script exists to repartition entries tables that predate
            # per-project subpartitioning, where `n_partitions` is a hardcoded
            # value rather than sourced from `project_partitions_dict`. Swap
            # the migrated entries table for one in that improper state,
            # carrying over the fixture data, to exercise that behavior.
            cursor.execute(
                f"""
                CREATE TABLE {_PRE_MIGRATION_ENTRIES_TABLE}
                (
                    `key` UInt32,
                    `project_guid` LowCardinality(String),
                    `family_guid` String,
                    `is_annotated_in_any_gene` Boolean,
                    `sign` Int8,
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
                f'INSERT INTO {_PRE_MIGRATION_ENTRIES_TABLE} VALUES',
                self.entries_rows,
            )
            cursor.execute(
                f'EXCHANGE TABLES {_ENTRIES_TABLE} AND {_PRE_MIGRATION_ENTRIES_TABLE}',
            )

    def tearDown(self):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f'EXCHANGE TABLES {_ENTRIES_TABLE} AND {_PRE_MIGRATION_ENTRIES_TABLE}',
            )
            cursor.execute(f'DROP TABLE {_PRE_MIGRATION_ENTRIES_TABLE}')
            cursor.execute(f'DROP DATABASE IF EXISTS {REPARTITION_DATABASE_NAME}')
        super().tearDown()

    def _partition_id(self, family_guid: str) -> int:
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                'SELECT farmHash64(%(family_guid)s) %% 2',
                {'family_guid': family_guid},
            )
            return cursor.fetchone()[0]

    def _expected_rows(self, project_guids):
        return [
            (
                key,
                project_guid,
                family_guid,
                is_annotated_in_any_gene,
                sign,
                2,
                self._partition_id(family_guid),
            )
            for key, project_guid, family_guid, is_annotated_in_any_gene, sign in self.entries_rows
            if not project_guids or project_guid in project_guids
        ]

    def test_main_all_projects(self):
        main(1, [])
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *, n_partitions, partition_id
                FROM {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
                """,
            )
            self.assertCountEqual(cursor.fetchall(), self._expected_rows([]))

    def test_main_one_project(self):
        main(1, ['project_a'])
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *, n_partitions, partition_id
                FROM {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                self._expected_rows(['project_a']),
            )
