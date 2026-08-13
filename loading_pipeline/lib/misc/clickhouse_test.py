import os
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from django.db import connections

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.misc.clickhouse import (
    STAGING_CLICKHOUSE_DATABASE,
    ClickHouseDictionary,
    ClickHouseMaterializedView,
    ClickhouseReferenceDataset,
    ClickHouseTable,
    TableNameBuilder,
    create_staging_materialized_views,
    create_staging_tables,
    delete_existing_families_from_staging_entries,
    delete_family_guids,
    direct_insert_all_keys,
    exchange_tables,
    get_clickhouse_client,
    insert_new_entries,
    load_complete_run,
    logged_query,
    normalize_partition,
    optimize_entries,
    rebuild_gt_stats,
    refresh_materialized_views,
    reload_dictionaries,
    replace_project_partitions,
    stage_existing_project_partitions,
)
from loading_pipeline.lib.paths import (
    new_entries_parquet_path,
    new_variant_details_parquet_path,
    new_variants_parquet_path,
    runs_path,
)
from loading_pipeline.lib.test.clickhouse_schema_testcase import (
    ClickhouseSchemaTestCase,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_RUN_ID = 'manual__2025-05-07T17-20-59.702114+00-00'


class ClickhouseTest(MockedDatarootTestCase, ClickhouseSchemaTestCase):
    fixtures = ['clickhouse_test']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # seqrdb_gene_ids/seqrdb_affected_status_dict are Postgres-sourced in production (see
        # postgres_dicts.py) - no ClickHouse-side model backs them, so override with
        # deterministic ClickHouse-sourced versions. Runs once for the class: inserting the
        # `entries` fixture rows (loaded per-test, before setUp()) triggers
        # entries_to_project_gt_stats_mv, which queries seqrdb_affected_status_dict.
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {Env.CLICKHOUSE_DATABASE}.seqrdb_gene_ids_src (
                    gene_id String,
                    seqrdb_id UInt32
                ) ENGINE = Memory;
                """,
            )
            cursor.execute(
                f'INSERT INTO {Env.CLICKHOUSE_DATABASE}.`seqrdb_gene_ids_src` VALUES',
                [('GENE1', 123), ('GENE2', 12), ('GENE3', 1)],
            )
            cursor.execute(
                f"""
                CREATE OR REPLACE DICTIONARY {Env.CLICKHOUSE_DATABASE}.seqrdb_gene_ids
                (
                    gene_id String,
                    seqrdb_id UInt32
                )
                PRIMARY KEY gene_id
                SOURCE(CLICKHOUSE(
                    USER {Env.CLICKHOUSE_WRITER_USER} PASSWORD {Env.CLICKHOUSE_WRITER_PASSWORD}
                    DB {Env.CLICKHOUSE_DATABASE} TABLE `seqrdb_gene_ids_src`
                ))
                LAYOUT(HASHED())
                LIFETIME(0);
                """,
            )
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {Env.CLICKHOUSE_DATABASE}.seqrdb_affected_status_dict_src (
                    family_guid String,
                    sampleId String,
                    affected String
                ) ENGINE = Memory;
                """,
            )
            cursor.execute(
                f"""
                CREATE OR REPLACE DICTIONARY {Env.CLICKHOUSE_DATABASE}.seqrdb_affected_status_dict
                (
                    family_guid String,
                    sampleId String,
                    affected String
                )
                PRIMARY KEY family_guid, sampleId
                SOURCE(CLICKHOUSE(
                    USER {Env.CLICKHOUSE_WRITER_USER} PASSWORD {Env.CLICKHOUSE_WRITER_PASSWORD}
                    DB {Env.CLICKHOUSE_DATABASE} TABLE `seqrdb_affected_status_dict_src`
                ))
                LAYOUT(COMPLEX_KEY_HASHED())
                LIFETIME(0);
                """,
            )

    def setUp(self):
        super().setUp()
        base_path = runs_path(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
        )
        os.makedirs(os.path.join(base_path, TEST_RUN_ID), exist_ok=True)

        def write_test_parquet(df: pd.DataFrame, parquet_path: str, schema=None):
            if schema:
                table = pa.Table.from_pandas(df, schema=schema)
            else:
                table = pa.Table.from_pandas(df)
            os.makedirs(parquet_path)
            pq.write_table(
                table,
                os.path.join(
                    parquet_path,
                    'test.parquet',
                ),
            )

        df = pd.DataFrame(
            {
                'key': [1, 2, 3, 4],
                'variantId': [
                    '1-13-A-C',
                    '2-14-A-T',
                    'Y-19-A-C',
                    'M-12-C-G',
                ],
                'transcripts': ['a', 'b', 'c', 'd'],
            },
        )
        write_test_parquet(
            df,
            new_variant_details_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )

        df = pd.DataFrame(
            {
                'key': [10, 11, 12, 13],
                'variantId': [
                    '1-3-A-C',
                    '2-4-A-T',
                    'Y-9-A-C',
                    'M-2-C-G',
                ],
            },
        )
        write_test_parquet(
            df,
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        write_test_parquet(
            df,
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                TEST_RUN_ID,
            ),
        )

        df = pd.DataFrame(
            {
                'key': [0, 3, 4],
                'project_guid': [
                    'project_d',
                    'project_d',
                    'project_d',
                ],
                'family_guid': [
                    'family_d1',
                    'family_d2',
                    'family_d3',
                ],
                'xpos': [
                    123456789,
                    123456789,
                    123456789,
                ],
                'sample_type': [
                    'WES',
                    'WES',
                    'WES',
                ],
                'geneIds': [
                    [],
                    ['GENE1', 'GENE2'],
                    ['GENE3'],
                ],
                'calls': [
                    [('sample_d1', 0), ('sample_d11', 2)],
                    [('sample_d2', 0)],
                    [('sample_d3', 1)],
                ],
                'sign': [
                    1,
                    1,
                    1,
                ],
            },
        )
        schema = pa.schema(
            [
                ('key', pa.int64()),
                ('project_guid', pa.string()),
                ('family_guid', pa.string()),
                ('xpos', pa.int64()),
                ('sample_type', pa.string()),
                ('geneIds', pa.list_(pa.string())),
                (
                    'calls',
                    pa.list_(
                        pa.struct([('sampleId', pa.string()), ('gt', pa.int64())]),
                    ),
                ),
                ('sign', pa.int64()),
            ],
        )
        write_test_parquet(
            df,
            new_entries_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
            schema,
        )
        write_test_parquet(
            df.drop('geneIds', axis=1),
            new_entries_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                TEST_RUN_ID,
            ),
            schema.remove(5).remove(5),
        )

    def test_get_clickhouse_client(self):
        client = get_clickhouse_client()
        result = client.execute('SELECT 1')
        self.assertEqual(result[0][0], 1)

    def test_normalize_partition(self):
        self.assertEqual(normalize_partition('project_d'), ('project_d',))
        self.assertEqual(
            normalize_partition("('project_d', 0)"),
            ('project_d', 0),
        )

    def test_table_name_builder(self):
        table_name_builder = TableNameBuilder(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            TEST_RUN_ID,
        )
        self.assertEqual(
            table_name_builder.dst_table(
                ClickHouseTable.ENTRIES,
            ),
            f'{Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`',
        )
        self.assertEqual(
            table_name_builder.src_table(
                ClickHouseTable.ENTRIES,
            ),
            f"file('{runs_path(ReferenceGenome.GRCh38, DatasetType.SNV_INDEL)}/manual__2025-05-07T17-20-59.702114+00-00/new_entries.parquet/*.parquet', 'Parquet')",
        )
        with patch('loading_pipeline.lib.paths.Env') as mock_env:
            mock_env.PIPELINE_DATA_DIR = 'gs://mock_bucket/v3.1'
            self.assertEqual(
                table_name_builder.src_table(
                    ClickHouseTable.ENTRIES,
                ),
                "gcs(pipeline_data_access, url='https://storage.googleapis.com/mock_bucket/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-05-07T17-20-59.702114+00-00/new_entries.parquet/*.parquet')",
            )

    def test_direct_insert_all_keys(self):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f'INSERT INTO {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants/details` VALUES',
                [(1, 'a', 'e'), (10, 'b', 'f'), (7, 'c', 'g')],
            )
            direct_insert_all_keys(
                ClickHouseTable.VARIANT_DETAILS,
                TableNameBuilder(
                    ReferenceGenome.GRCh38,
                    DatasetType.SNV_INDEL,
                    TEST_RUN_ID,
                ),
            )
            cursor.execute(
                f'SELECT * FROM {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants/details`',
            )
            self.assertEqual(
                cursor.fetchall(),
                [
                    (1, '1-13-A-C', 'a'),
                    (2, '2-14-A-T', 'b'),
                    (3, 'Y-19-A-C', 'c'),
                    (4, 'M-12-C-G', 'd'),
                    (7, 'c', 'g'),
                    (10, 'b', 'f'),
                ],
            )

            # ensure multiple calls are idempotent
            direct_insert_all_keys(
                ClickHouseTable.VARIANT_DETAILS,
                TableNameBuilder(
                    ReferenceGenome.GRCh38,
                    DatasetType.SNV_INDEL,
                    TEST_RUN_ID,
                ),
            )
            cursor.execute(
                f'SELECT COUNT(*) FROM {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants/details`',
            )
            self.assertEqual(cursor.fetchone()[0], 6)

    @patch.object(
        ClickhouseReferenceDataset,
        'for_reference_genome_dataset_type',
        return_value=[ClickhouseReferenceDataset.CLINVAR],
    )
    def test_entries_insert_flow(self, mock_for_reference_genome_dataset_type):
        # Tests individual components of atomic_insert_entries, validating state after each step.
        with connections['clickhouse_write'].cursor() as cursor:
            table_name_builder = TableNameBuilder(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            )
            create_staging_tables(
                table_name_builder,
                ClickHouseTable.for_dataset_type_atomic_entries_update(
                    DatasetType.SNV_INDEL,
                ),
            )
            create_staging_materialized_views(
                table_name_builder,
                ClickHouseMaterializedView.for_dataset_type_atomic_entries_update(
                    DatasetType.SNV_INDEL,
                ),
            )
            stage_existing_project_partitions(
                table_name_builder,
                [
                    'project_a',
                    'project_b',
                    'project_d',  # Partition does not exist already.
                ],
                ClickHouseTable.for_dataset_type_atomic_entries_update_project_partitioned(
                    DatasetType.SNV_INDEL,
                ),
            )
            cursor.execute(
                f"""
                SELECT DISTINCT project_guid FROM {STAGING_CLICKHOUSE_DATABASE}.`{table_name_builder.run_id_hash}/GRCh38/SNV_INDEL/entries`
                """,
            )
            self.assertCountEqual(
                [p[0] for p in cursor.fetchall()],
                ['project_a', 'project_b'],
            )
            cursor.execute(
                f"""
                SELECT project_guid, key, sample_type, sum(het_samples), sum(hom_samples)
                FROM
                {STAGING_CLICKHOUSE_DATABASE}.`{table_name_builder.run_id_hash}/GRCh38/SNV_INDEL/project_gt_stats`
                GROUP BY project_guid, key, sample_type
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    ('project_a', 0, 'WES', 0, 1),
                    ('project_a', 1, 'WGS', 1, 0),
                    ('project_a', 2, 'WGS', 0, 1),
                    ('project_a', 4, 'WES', 1, 0),
                    ('project_a', 4, 'WGS', 0, 1),
                    ('project_b', 1, 'WES', 1, 0),
                    ('project_b', 3, 'WES', 0, 1),
                    ('project_b', 4, 'WES', 0, 1),
                    # project_gt_stats stages all projects, not just
                    # those requested for loading.
                    ('project_c', 4, 'WES', 0, 1),
                    ('project_c', 5, 'WES', 0, 1),
                ],
            )
            delete_existing_families_from_staging_entries(
                table_name_builder,
                ['family_a1', 'family_a5', 'family_a6'],
            )
            cursor.execute(
                f"""
                SELECT project_guid, key, sample_type, sum(het_samples), sum(hom_samples)
                FROM
                {STAGING_CLICKHOUSE_DATABASE}.`{table_name_builder.run_id_hash}/GRCh38/SNV_INDEL/project_gt_stats`
                GROUP BY project_guid, key, sample_type
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    ('project_a', 0, 'WES', 0, 0),
                    ('project_a', 1, 'WGS', 1, 0),
                    ('project_a', 2, 'WGS', 0, 1),
                    ('project_a', 4, 'WES', 0, 0),
                    ('project_a', 4, 'WGS', 0, 0),
                    ('project_b', 1, 'WES', 1, 0),
                    ('project_b', 3, 'WES', 0, 1),
                    ('project_b', 4, 'WES', 0, 1),
                    ('project_c', 4, 'WES', 0, 1),
                    ('project_c', 5, 'WES', 0, 1),
                ],
            )
            insert_new_entries(table_name_builder)
            optimize_entries(
                table_name_builder,
                ['project_a', 'project_b', 'project_c'],
            )
            cursor.execute(
                f"""
                SELECT project_guid, key, sample_type, sum(het_samples), sum(hom_samples)
                FROM
                {STAGING_CLICKHOUSE_DATABASE}.`{table_name_builder.run_id_hash}/GRCh38/SNV_INDEL/project_gt_stats`
                GROUP BY project_guid, key, sample_type
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    ('project_a', 0, 'WES', 0, 0),
                    ('project_a', 1, 'WGS', 1, 0),
                    ('project_a', 2, 'WGS', 0, 1),
                    ('project_a', 4, 'WES', 0, 0),
                    ('project_a', 4, 'WGS', 0, 0),
                    ('project_b', 1, 'WES', 1, 0),
                    ('project_b', 3, 'WES', 0, 1),
                    ('project_b', 4, 'WES', 0, 1),
                    ('project_c', 4, 'WES', 0, 1),
                    ('project_c', 5, 'WES', 0, 1),
                    ('project_d', 0, 'WES', 0, 1),
                    ('project_d', 4, 'WES', 1, 0),
                ],
            )
            refresh_materialized_views(
                table_name_builder,
                ClickHouseMaterializedView.for_dataset_type_atomic_entries_update_refreshable(
                    DatasetType.SNV_INDEL,
                ),
                staging=True,
            )
            replace_project_partitions(
                table_name_builder,
                ClickHouseTable.for_dataset_type_atomic_entries_update_project_partitioned(
                    DatasetType.SNV_INDEL,
                ),
                ['project_a', 'project_d'],
            )
            cursor.execute(
                f"""
                SELECT COLUMNS('.*') EXCEPT(is_annotated_in_any_gene, is_gnomad_gt_5_percent)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    (
                        0,
                        'project_b',
                        'family_b1',
                        123456789,
                        'WES',
                        [],
                        [('sample_b4', 'REF')],
                        1,
                    ),
                    (
                        1,
                        'project_b',
                        'family_b2',
                        123456789,
                        'WES',
                        [],
                        [('sample_b5', 'HET')],
                        1,
                    ),
                    (
                        2,
                        'project_b',
                        'family_b2',
                        123456789,
                        'WES',
                        [],
                        [('sample_b5', 'REF')],
                        1,
                    ),
                    (
                        3,
                        'project_b',
                        'family_b3',
                        133456789,
                        'WES',
                        [],
                        [('sample_b6', 'HOM')],
                        1,
                    ),
                    (
                        4,
                        'project_b',
                        'family_b3',
                        133456789,
                        'WES',
                        [],
                        [('sample_b6', 'HOM')],
                        1,
                    ),
                    (
                        1,
                        'project_a',
                        'family_a2',
                        123456789,
                        'WGS',
                        [],
                        [('sample_a2', 'HET')],
                        1,
                    ),
                    (
                        2,
                        'project_a',
                        'family_a3',
                        133456789,
                        'WGS',
                        [],
                        [('sample_a3', 'HOM')],
                        1,
                    ),
                    (
                        3,
                        'project_a',
                        'family_a4',
                        133456789,
                        'WES',
                        [],
                        [('sample_a4', 'REF')],
                        1,
                    ),
                    (
                        0,
                        'project_d',
                        'family_d1',
                        123456789,
                        'WES',
                        [],
                        [('sample_d1', 'REF'), ('sample_d11', 'HOM')],
                        1,
                    ),
                    (
                        3,
                        'project_d',
                        'family_d2',
                        123456789,
                        'WES',
                        [123, 12],
                        [('sample_d2', 'REF')],
                        1,
                    ),
                    (
                        4,
                        'project_d',
                        'family_d3',
                        123456789,
                        'WES',
                        [1],
                        [('sample_d3', 'HET')],
                        1,
                    ),
                    (
                        0,
                        'project_c',
                        'family_c1',
                        123456789,
                        'WES',
                        [1],
                        [('sample_c7', 'REF')],
                        1,
                    ),
                    (
                        3,
                        'project_c',
                        'family_c2',
                        123456789,
                        'WES',
                        [1],
                        [('sample_c8', 'REF')],
                        1,
                    ),
                    (
                        4,
                        'project_c',
                        'family_c3',
                        133456789,
                        'WES',
                        [1],
                        [('sample_c9', 'HOM')],
                        1,
                    ),
                    (
                        5,
                        'project_c',
                        'family_c4',
                        133456789,
                        'WES',
                        [1],
                        [('sample_c9', 'HOM')],
                        1,
                    ),
                ],
            )
            cursor.execute(
                f"""
                SELECT *
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats_dict`
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [],
            )
            exchange_tables(
                table_name_builder,
                ClickHouseTable.for_dataset_type_atomic_entries_update_unpartitioned(
                    DatasetType.SNV_INDEL,
                ),
            )
            cursor.execute(
                f"""
                SELECT *
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats_dict`
                """,
            )
            self.assertCountEqual(cursor.fetchall(), [])
            reload_dictionaries(
                table_name_builder,
                ClickHouseDictionary.for_dataset_type(DatasetType.SNV_INDEL),
            )
            cursor.execute(
                f"""
                SELECT *
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats_dict`
                """,
            )
            self.assertEqual(
                cursor.fetchall(),
                [
                    (0, 2, 0),
                    (1, 1, 1),
                    (2, 0, 2),
                    (3, 2, 0),
                    (4, 5, 0),
                    (5, 2, 0),
                ],
            )

    @patch.object(
        ClickhouseReferenceDataset,
        'for_reference_genome_dataset_type',
        return_value=[ClickhouseReferenceDataset.CLINVAR],
    )
    def test_load_complete_run_snv_indel(self, mock_for_reference_genome_dataset_type):
        load_complete_run(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            TEST_RUN_ID,
            ['project_d'],
            ['family_d1', 'family_d2'],
        )
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
               SELECT project_guid, key, sample_type, sum(het_samples), sum(hom_samples)
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
               GROUP BY project_guid, key, sample_type
               """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    ('project_d', 0, 'WES', 0, 1),
                    ('project_d', 4, 'WES', 1, 0),
                ],
            )
            cursor.execute(
                f"""
               SELECT *
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
               """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    (0, 2, 0),
                    (4, 1, 0),
                ],
            )
            cursor.execute(
                f"""
               SELECT *
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats_dict`
               """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    (0, 2, 0),
                    (4, 1, 0),
                ],
            )
            cursor.execute(
                f"""
               SELECT *
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants_memory`
               """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    (10, '1-3-A-C'),
                    (11, '2-4-A-T'),
                    (12, 'Y-9-A-C'),
                    (13, 'M-2-C-G'),
                ],
            )
            cursor.execute(
                f"""
               SELECT *
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants_disk`
               """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [
                    (10, '1-3-A-C'),
                    (11, '2-4-A-T'),
                    (12, 'Y-9-A-C'),
                    (13, 'M-2-C-G'),
                ],
            )

    def test_load_complete_gcnv(self):
        load_complete_run(
            ReferenceGenome.GRCh38,
            DatasetType.GCNV,
            TEST_RUN_ID,
            ['project_d'],
            ['family_d1', 'family_d2'],
        )
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
               SELECT COUNT(*)
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/variants_memory`
               """,
            )
            self.assertEqual(cursor.fetchone()[0], 4)
            cursor.execute(
                f"""
               SELECT COUNT(*)
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/variants_disk`
               """,
            )
            self.assertEqual(cursor.fetchone()[0], 4)
            cursor.execute(
                f"""
               SELECT COUNT(*)
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/key_lookup`
               """,
            )
            self.assertEqual(cursor.fetchone()[0], 4)
            cursor.execute(
                f"""
               SELECT COUNT(*)
               FROM
               {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/entries`
               """,
            )
            self.assertEqual(cursor.fetchone()[0], 3)

    def test_delete_families(self):
        table_name_builder = TableNameBuilder(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            TEST_RUN_ID,
        )
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT project_guid, sum(het_samples), sum(hom_samples)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
                GROUP BY project_guid
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [('project_a', 2, 3), ('project_c', 0, 2), ('project_b', 1, 2)],
            )
            refresh_materialized_views(
                table_name_builder,
                ClickHouseMaterializedView.for_dataset_type_atomic_entries_update_refreshable(
                    DatasetType.SNV_INDEL,
                ),
                staging=False,
            )
            cursor.execute(
                f"""
                SELECT sum(ac_wes)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
                """,
            )
            self.assertCountEqual(cursor.fetchall(), [(12,)])
            delete_family_guids(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
                'project_a',
                ['family_a1', 'family_a2'],
            )
            cursor.execute(
                f"""
                SELECT project_guid, sum(het_samples), sum(hom_samples)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
                GROUP BY project_guid
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [('project_a', 1, 2), ('project_c', 0, 2), ('project_b', 1, 2)],
            )
            cursor.execute(
                f"""
                SELECT sum(ac_wes)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
                """,
            )
            self.assertCountEqual(cursor.fetchall(), [(10,)])
            cursor.execute(
                f"""
                SELECT sum(ac_wes)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats_dict`
                """,
            )
            self.assertCountEqual(cursor.fetchall(), [(10,)])

    def test_rebuild_gt_stats(self):
        table_name_builder = TableNameBuilder(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            TEST_RUN_ID,
        )
        with connections['clickhouse_write'].cursor() as cursor:
            logged_query(  # DROP the partition from the non-staging entries to as a non-mv-impacting change.
                f"""
                ALTER TABLE {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`
                DROP PARTITION (%(project_guid)s, %(partition_id)s)
                """,
                # project_partitions_dict has no row for project_a, so n_partitions (and thus
                # partition_id) defaults to 0.
                {'project_guid': 'project_a', 'partition_id': 0},
            )
            cursor.execute(
                f"""
                SELECT project_guid, sum(het_samples), sum(hom_samples)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
                WHERE project_guid IN ('project_a', 'project_b')
                GROUP BY project_guid
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [('project_a', 2, 3), ('project_b', 1, 2)],
            )
            refresh_materialized_views(
                table_name_builder,
                ClickHouseMaterializedView.for_dataset_type_atomic_entries_update_refreshable(
                    DatasetType.SNV_INDEL,
                ),
                staging=False,
            )
            cursor.execute(
                f"""
                SELECT sum(ac_wes), sum(ac_wgs)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
                """,
            )
            # gt_stats has no project dimension (keyed globally by `key`), so project_c's rows
            # (sharing key values with project_a/b in the fixture) also contribute here.
            self.assertCountEqual(cursor.fetchall(), [(12, 5)])
            rebuild_gt_stats(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
                ['project_a', 'project_b'],
            )
            cursor.execute(
                f"""
                SELECT project_guid, sum(het_samples), sum(hom_samples)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
                WHERE project_guid IN ('project_a', 'project_b')
                GROUP BY project_guid
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [('project_b', 1, 2)],
            )
            cursor.execute(
                f"""
                SELECT sum(ac_wes), sum(ac_wgs)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
                """,
            )
            self.assertCountEqual(cursor.fetchall(), [(9, 0)])

    @patch.object(
        ClickhouseReferenceDataset,
        'for_reference_genome_dataset_type',
        return_value=[ClickhouseReferenceDataset.CLINVAR],
    )
    def test_repartitioned_entries_table(self, mock_for_reference_genome_dataset_type):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f"""
                REPLACE TABLE {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries` (
                    `key` UInt32,
                    `project_guid` LowCardinality(String),
                    `family_guid` String,
                    `xpos` UInt64 CODEC(Delta(8), ZSTD(1)),
                    `sample_type` Enum8('WES' = 0, 'WGS' = 1),
                    `is_gnomad_gt_5_percent` Boolean,
                    `is_annotated_in_any_gene` Boolean DEFAULT length(geneId_ids) > 0,
                    `geneId_ids` Array(UInt32),
                    `calls` Array(
                        Tuple(
                            sampleId String,
                            gt Nullable(Enum8('REF' = 0, 'HET' = 1, 'HOM' = 2)),
                        )
                    ),
                    `sign` Int8,
                    `n_partitions` UInt8 MATERIALIZED 2,
                    `partition_id` UInt8 MATERIALIZED farmHash64(family_guid) % n_partitions,
                    PROJECTION xpos_projection
                    (
                        SELECT *
                        ORDER BY is_annotated_in_any_gene, xpos
                    )
                )
                ENGINE = CollapsingMergeTree(sign)
                PARTITION BY (project_guid, partition_id)
                ORDER BY (project_guid, family_guid, key)
                SETTINGS deduplicate_merge_projection_mode = 'rebuild';
                """,
            )
            load_complete_run(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
                ['project_d'],
                ['family_d1', 'family_d2', 'family_d3'],
            )
            cursor.execute(
                f"""
                SELECT project_guid, sum(het_samples), sum(hom_samples)
                FROM
                {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
                GROUP BY project_guid
                """,
            )
            self.assertCountEqual(
                cursor.fetchall(),
                [('project_d', 1, 1)],
            )
