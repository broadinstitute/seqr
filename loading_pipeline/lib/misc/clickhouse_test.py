import os
from typing import ClassVar
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

_FIVEUTR_ANNOTATION_TYPE = pa.struct(
    [
        ('AltStop', pa.string()),
        ('AltStopDistanceToCDS', pa.int32()),
        ('CapDistanceToStart', pa.int32()),
        ('DistanceToCDS', pa.int32()),
        ('DistanceToStop', pa.int32()),
        ('Evidence', pa.bool_()),
        ('FrameWithCDS', pa.string()),
        ('KozakContext', pa.string()),
        ('KozakStrength', pa.string()),
        ('StartDistanceToCDS', pa.int32()),
        ('alt_type', pa.string()),
        ('alt_type_length', pa.int32()),
        ('newSTOPDistanceToCDS', pa.int32()),
        ('ref_StartDistanceToCDS', pa.int32()),
        ('ref_type', pa.string()),
        ('ref_type_length', pa.int32()),
        ('type', pa.string()),
    ],
)
_UTRANNOTATOR_TYPE = pa.struct(
    [
        ('existingInframeOorfs', pa.int32()),
        ('existingOutofframeOorfs', pa.int32()),
        ('existingUorfs', pa.int32()),
        ('fiveutrAnnotation', _FIVEUTR_ANNOTATION_TYPE),
        ('fiveutrConsequence', pa.string()),
    ],
)
_TRANSCRIPT_TYPE = pa.struct(
    [
        ('alphamissense', pa.struct([('pathogenicity', pa.float64())])),
        ('aminoAcids', pa.string()),
        ('biotype', pa.string()),
        ('canonical', pa.int32()),
        ('codons', pa.string()),
        ('consequenceTerms', pa.list_(pa.string())),
        ('exon', pa.struct([('index', pa.int32()), ('total', pa.int32())])),
        ('geneId', pa.string()),
        ('hgvsc', pa.string()),
        ('hgvsp', pa.string()),
        ('intron', pa.struct([('index', pa.int32()), ('total', pa.int32())])),
        (
            'loftee',
            pa.struct(
                [('isLofNagnag', pa.bool_()), ('lofFilters', pa.list_(pa.string()))],
            ),
        ),
        ('majorConsequence', pa.string()),
        ('manePlusClinical', pa.string()),
        ('maneSelect', pa.string()),
        ('refseqTranscriptId', pa.string()),
        (
            'spliceregion',
            pa.struct([('extended_intronic_splice_region_variant', pa.bool_())]),
        ),
        ('transcriptId', pa.string()),
        ('transcriptRank', pa.int32()),
        ('utrannotator', _UTRANNOTATOR_TYPE),
    ],
)
_MOTIF_CONSEQUENCE_TYPE = pa.struct(
    [
        ('consequenceTerms', pa.list_(pa.string())),
        ('motifFeatureId', pa.string()),
    ],
)
_REGULATORY_CONSEQUENCE_TYPE = pa.struct(
    [
        ('biotype', pa.string()),
        ('consequenceTerms', pa.list_(pa.string())),
        ('regulatoryFeatureId', pa.string()),
    ],
)
VARIANT_DETAILS_SCHEMA = pa.schema(
    [
        ('key', pa.int64()),
        ('variantId', pa.string()),
        ('liftedOverChrom', pa.string()),
        ('liftedOverPos', pa.int64()),
        ('rsid', pa.string()),
        ('CAID', pa.string()),
        ('transcripts', pa.list_(_TRANSCRIPT_TYPE)),
        ('sortedMotifFeatureConsequences', pa.list_(_MOTIF_CONSEQUENCE_TYPE)),
        ('sortedRegulatoryFeatureConsequences', pa.list_(_REGULATORY_CONSEQUENCE_TYPE)),
    ],
)
_FULL_TRANSCRIPT = {
    'alphamissense': {'pathogenicity': 0.5},
    'aminoAcids': 'S/L',
    'biotype': 'protein_coding',
    'canonical': 1,
    'codons': 'tCg/tTg',
    'consequenceTerms': ['missense_variant'],
    'exon': {'index': 6, 'total': 14},
    'geneId': 'ENSG00000187634',
    'hgvsc': 'ENST00000616016.5:c.1049C>T',
    'hgvsp': 'ENSP00000478421.2:p.Ser350Leu',
    'intron': None,
    'loftee': {'isLofNagnag': False, 'lofFilters': []},
    'majorConsequence': 'missense_variant',
    'manePlusClinical': None,
    'maneSelect': 'NM_001385641.1',
    'refseqTranscriptId': 'NM_001385641.1',
    'spliceregion': {'extended_intronic_splice_region_variant': False},
    'transcriptId': 'ENST00000616016',
    'transcriptRank': 0,
    'utrannotator': {
        'existingInframeOorfs': None,
        'existingOutofframeOorfs': None,
        'existingUorfs': None,
        'fiveutrAnnotation': {
            'AltStop': None,
            'AltStopDistanceToCDS': None,
            'CapDistanceToStart': None,
            'DistanceToCDS': 41,
            'DistanceToStop': None,
            'Evidence': None,
            'FrameWithCDS': None,
            'KozakContext': 'CGCATGC',
            'KozakStrength': 'Weak',
            'StartDistanceToCDS': None,
            'alt_type': None,
            'alt_type_length': None,
            'newSTOPDistanceToCDS': None,
            'ref_StartDistanceToCDS': None,
            'ref_type': None,
            'ref_type_length': None,
            'type': 'OutOfFrame_oORF',
        },
        'fiveutrConsequence': None,
    },
}
_FULL_MOTIF_CONSEQUENCE = {
    'consequenceTerms': ['TFBS_ablation'],
    'motifFeatureId': 'ENSM00000123',
}
_FULL_REGULATORY_CONSEQUENCE = {
    'biotype': 'enhancer',
    'consequenceTerms': ['regulatory_region_ablation'],
    'regulatoryFeatureId': 'ENSR00000123',
}


class ClickhouseTest(MockedDatarootTestCase, ClickhouseSchemaTestCase):
    fixtures: ClassVar = ['clickhouse_test']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        #  Postgres dicts are not managed by django in this test suite and therefore cannot be loaded from fixtures
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                f'INSERT INTO {Env.CLICKHOUSE_DATABASE}.`seqrdb_gene_ids_src` VALUES',
                [('GENE1', 123), ('GENE2', 12), ('GENE3', 1)],
            )
            cursor.execute(
                f'SYSTEM RELOAD DICTIONARY {Env.CLICKHOUSE_DATABASE}.`seqrdb_gene_ids`',
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

        # Variant Details Parquet
        df = pd.DataFrame(
            {
                'key': [1, 2, 3, 4],
                'variantId': [
                    '1-13-A-C',
                    '2-14-A-T',
                    'Y-19-A-C',
                    'M-12-C-G',
                ],
                'transcripts': [[_FULL_TRANSCRIPT], [], [], []],
                'liftedOverChrom': ['1', None, None, None],
                'liftedOverPos': [13, None, None, None],
                'rsid': ['rs123', None, None, None],
                'CAID': ['CA123456', None, None, None],
                'sortedMotifFeatureConsequences': [
                    [_FULL_MOTIF_CONSEQUENCE],
                    [],
                    [],
                    [],
                ],
                'sortedRegulatoryFeatureConsequences': [
                    [_FULL_REGULATORY_CONSEQUENCE],
                    [],
                    [],
                    [],
                ],
            },
        )
        write_test_parquet(
            df,
            new_variant_details_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
            VARIANT_DETAILS_SCHEMA,
        )

        # New Variants parquet.
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

        # New Entries Parquet
        df = pd.DataFrame(
            {
                'key': [10, 3, 4],
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
        cursor = connections['clickhouse_write'].cursor()
        direct_insert_all_keys(
            ClickHouseTable.VARIANT_DETAILS,
            TableNameBuilder(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        cursor.execute(
            f'SELECT key, variantId FROM {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants/details`',  # nosec B608
        )
        ret = cursor.fetchall()
        self.assertEqual(
            ret,
            [
                (1, '1-13-A-C'),
                (2, '2-14-A-T'),
                (3, 'Y-19-A-C'),
                (4, 'M-12-C-G'),
                (7, 'c'),
                (10, 'b'),
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
            f'SELECT COUNT(*) FROM {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants/details`',  # nosec B608
        )
        ret = cursor.fetchone()
        self.assertEqual(ret[0], 6)

    @patch.object(
        ClickhouseReferenceDataset,
        'for_reference_genome_dataset_type',
        return_value=[ClickhouseReferenceDataset.CLINVAR],
    )
    def test_entries_insert_flow(self, mock_for_reference_genome_dataset_type):
        # Tests individual components of the atomic_insert_entries
        # to validate the state after each step.
        cursor = connections['clickhouse_write'].cursor()
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
            """,  # nosec B608
        )
        staged_projects = cursor.fetchall()
        self.assertCountEqual(
            [p[0] for p in staged_projects],
            ['project_a', 'project_b'],
        )
        cursor.execute(
            f"""
            SELECT project_guid, key, sample_type, sum(het_samples), sum(hom_samples)
            FROM
            {STAGING_CLICKHOUSE_DATABASE}.`{table_name_builder.run_id_hash}/GRCh38/SNV_INDEL/project_gt_stats`
            FINAL
            GROUP BY project_guid, key, sample_type
            """,  # nosec B608
        )
        staged_project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            staged_project_gt_stats,
            [
                ('project_a', 10, 'WES', 0, 1),
                ('project_a', 1, 'WGS', 1, 0),
                ('project_a', 2, 'WGS', 0, 1),
                ('project_a', 3, 'WES', 0, 0),
                ('project_a', 4, 'WES', 1, 0),
                ('project_a', 4, 'WGS', 0, 1),
                ('project_b', 10, 'WES', 0, 0),
                ('project_b', 1, 'WES', 1, 0),
                ('project_b', 2, 'WES', 0, 0),
                ('project_b', 3, 'WES', 0, 1),
                ('project_b', 4, 'WES', 0, 1),
                # project_gt_stats stages all projects, not just
                # those requested for loading.
                ('project_c', 0, 'WES', 0, 0),
                ('project_c', 3, 'WES', 0, 0),
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
            FINAL
            GROUP BY project_guid, key, sample_type
            """,  # nosec B608
        )
        staged_project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            staged_project_gt_stats,
            [
                ('project_a', 1, 'WGS', 1, 0),
                ('project_a', 2, 'WGS', 0, 1),
                ('project_b', 10, 'WES', 0, 0),
                ('project_b', 1, 'WES', 1, 0),
                ('project_b', 2, 'WES', 0, 0),
                ('project_b', 3, 'WES', 0, 1),
                ('project_b', 4, 'WES', 0, 1),
                ('project_c', 0, 'WES', 0, 0),
                ('project_c', 3, 'WES', 0, 0),
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
            FINAL
            GROUP BY project_guid, key, sample_type
            """,  # nosec B608
        )
        staged_project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            staged_project_gt_stats,
            [
                ('project_a', 1, 'WGS', 1, 0),
                ('project_a', 2, 'WGS', 0, 1),
                ('project_b', 10, 'WES', 0, 0),
                ('project_b', 1, 'WES', 1, 0),
                ('project_b', 2, 'WES', 0, 0),
                ('project_b', 3, 'WES', 0, 1),
                ('project_b', 4, 'WES', 0, 1),
                ('project_c', 0, 'WES', 0, 0),
                ('project_c', 3, 'WES', 0, 0),
                ('project_c', 4, 'WES', 0, 1),
                ('project_c', 5, 'WES', 0, 1),
                ('project_d', 10, 'WES', 0, 1),
                ('project_d', 3, 'WES', 0, 0),
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
            """,  # nosec B608
        )
        new_entries = cursor.fetchall()
        self.assertCountEqual(
            new_entries,
            [
                (
                    10,
                    'project_b',
                    'family_b1',
                    'WES',
                    123456789,
                    [],
                    [],
                    [('sample_b4', 'REF', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    1,
                    'project_b',
                    'family_b2',
                    'WES',
                    123456789,
                    [],
                    [],
                    [('sample_b5', 'HET', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    2,
                    'project_b',
                    'family_b2',
                    'WES',
                    123456789,
                    [],
                    [],
                    [('sample_b5', 'REF', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    3,
                    'project_b',
                    'family_b3',
                    'WES',
                    133456789,
                    [],
                    [],
                    [('sample_b6', 'HOM', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    4,
                    'project_b',
                    'family_b3',
                    'WES',
                    133456789,
                    [],
                    [],
                    [('sample_b6', 'HOM', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    1,
                    'project_a',
                    'family_a2',
                    'WGS',
                    123456789,
                    [],
                    [],
                    [('sample_a2', 'HET', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    2,
                    'project_a',
                    'family_a3',
                    'WGS',
                    133456789,
                    [],
                    [],
                    [('sample_a3', 'HOM', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    3,
                    'project_a',
                    'family_a4',
                    'WES',
                    133456789,
                    [],
                    [],
                    [('sample_a4', 'REF', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    10,
                    'project_d',
                    'family_d1',
                    'WES',
                    123456789,
                    [],
                    [],
                    [
                        ('sample_d1', 'REF', None, None, None),
                        ('sample_d11', 'HOM', None, None, None),
                    ],
                    1,
                    1,
                    0,
                ),
                (
                    3,
                    'project_d',
                    'family_d2',
                    'WES',
                    123456789,
                    [123, 12],
                    [],
                    [('sample_d2', 'REF', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    4,
                    'project_d',
                    'family_d3',
                    'WES',
                    123456789,
                    [1],
                    [],
                    [('sample_d3', 'HET', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    0,
                    'project_c',
                    'family_c1',
                    'WES',
                    123456789,
                    [1],
                    [],
                    [('sample_c7', 'REF', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    3,
                    'project_c',
                    'family_c2',
                    'WES',
                    123456789,
                    [1],
                    [],
                    [('sample_c8', 'REF', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    4,
                    'project_c',
                    'family_c3',
                    'WES',
                    133456789,
                    [1],
                    [],
                    [('sample_c9', 'HOM', None, None, None)],
                    1,
                    1,
                    0,
                ),
                (
                    5,
                    'project_c',
                    'family_c4',
                    'WES',
                    133456789,
                    [1],
                    [],
                    [('sample_c9', 'HOM', None, None, None)],
                    1,
                    1,
                    0,
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
        existing_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            existing_gt_stats,
            [
                (1, 1, 0, 0, 0, 0, 0),
                (2, 0, 2, 0, 0, 1, 0),
                (3, 2, 0, 0, 1, 0, 0),
                (4, 5, 2, 0, 2, 1, 0),
                (5, 2, 0, 0, 1, 0, 0),
            ],
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
        new_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            new_gt_stats,
            [
                (1, 1, 0, 0, 0, 0, 0),
                (2, 0, 2, 0, 0, 1, 0),
                (3, 2, 0, 0, 1, 0, 0),
                (4, 5, 2, 0, 2, 1, 0),
                (5, 2, 0, 0, 1, 0, 0),
            ],
        )
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
        new_gt_stats_post_reload = cursor.fetchall()
        self.assertEqual(
            new_gt_stats_post_reload,
            [
                (1, 1, 1, 0, 0, 0, 0),
                (2, 0, 2, 0, 0, 1, 0),
                (3, 2, 0, 0, 1, 0, 0),
                (4, 5, 0, 0, 2, 0, 0),
                (5, 2, 0, 0, 1, 0, 0),
                (10, 2, 0, 0, 1, 0, 0),
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
        cursor = connections['clickhouse_write'].cursor()
        cursor.execute(
            f"""
           SELECT project_guid, key, sample_type, sum(het_samples), sum(hom_samples)
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
           WHERE project_guid = 'project_d'
           GROUP BY project_guid, key, sample_type
           """,
        )
        project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            project_gt_stats,
            [
                ('project_d', 10, 'WES', 0, 1),
                ('project_d', 4, 'WES', 1, 0),
                ('project_d', 3, 'WES', 0, 0),
            ],
        )
        cursor.execute(
            f"""
           SELECT *
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
           """,
        )
        gt_stats = cursor.fetchall()
        self.assertCountEqual(
            gt_stats,
            [
                (1, 1, 1, 0, 0, 0, 0),
                (2, 0, 2, 0, 0, 1, 0),
                (3, 2, 0, 0, 1, 0, 0),
                (4, 6, 2, 0, 2, 1, 0),
                (5, 2, 0, 0, 1, 0, 0),
                (10, 4, 0, 0, 2, 0, 0),
            ],
        )
        cursor.execute(
            f"""
           SELECT *
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats_dict`
           """,
        )
        gt_stats_dict = cursor.fetchall()
        self.assertCountEqual(
            gt_stats_dict,
            [
                (1, 1, 1, 0, 0, 0, 0),
                (2, 0, 2, 0, 0, 1, 0),
                (3, 2, 0, 0, 1, 0, 0),
                (4, 6, 2, 0, 2, 1, 0),
                (5, 2, 0, 0, 1, 0, 0),
                (10, 4, 0, 0, 2, 0, 0),
            ],
        )
        cursor.execute(
            f"""
           SELECT *
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants_memory`
           """,
        )
        variants_memory = cursor.fetchall()
        self.assertCountEqual(
            variants_memory,
            [
                (10, [], [], []),
                (11, [], [], []),
                (12, [], [], []),
                (13, [], [], []),
            ],
        )
        cursor.execute(
            f"""
           SELECT *
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants_disk`
           """,
        )
        variants_disk = cursor.fetchall()
        self.assertCountEqual(
            variants_disk,
            [
                (10, [], [], []),
                (11, [], [], []),
                (12, [], [], []),
                (13, [], [], []),
            ],
        )
        cursor.execute(
            f"""
                       SELECT key, variantId
                       FROM
                       {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/variants/details`
                       """,  # nosec B608
        )
        variants_details = cursor.fetchall()
        self.assertCountEqual(
            variants_details,
            [
                (1, '1-13-A-C'),
                (2, '2-14-A-T'),
                (3, 'Y-19-A-C'),
                (4, 'M-12-C-G'),
                (7, 'c'),
                (10, 'b'),
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
        cursor = connections['clickhouse_write'].cursor()
        cursor.execute(
            f"""
           SELECT COUNT(*)
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/variants_memory`
           """,  # nosec B608
        )
        variants_disk_count = cursor.fetchone()[0]
        self.assertEqual(variants_disk_count, 4)
        cursor.execute(
            f"""
           SELECT COUNT(*)
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/variants_disk`
           """,  # nosec B608
        )
        variants_disk_count = cursor.fetchone()[0]
        self.assertEqual(variants_disk_count, 4)
        cursor.execute(
            f"""
           SELECT COUNT(*)
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/key_lookup`
           """,  # nosec B608
        )
        key_lookup_count = cursor.fetchone()[0]
        self.assertEqual(key_lookup_count, 4)
        cursor.execute(
            f"""
           SELECT COUNT(*)
           FROM
           {Env.CLICKHOUSE_DATABASE}.`GRCh38/GCNV/entries`
           """,  # nosec B608
        )
        entries_count = cursor.fetchone()[0]
        self.assertEqual(entries_count, 3)

    def test_delete_families(self):
        table_name_builder = TableNameBuilder(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            TEST_RUN_ID,
        )
        cursor = connections['clickhouse_write'].cursor()
        cursor.execute(
            f"""
            SELECT project_guid, sum(het_samples), sum(hom_samples)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
            FINAL
            GROUP BY project_guid
            """,  # nosec B608
        )
        project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            project_gt_stats,
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
            """,  # nosec B608
        )
        gt_stats = cursor.fetchall()
        self.assertCountEqual(gt_stats, [(12,)])
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
            FINAL
            GROUP BY project_guid
            """,  # nosec B608
        )
        project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            project_gt_stats,
            [('project_a', 1, 2), ('project_c', 0, 2), ('project_b', 1, 2)],
        )
        cursor.execute(
            f"""
            SELECT sum(ac_wes)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
            """,  # nosec B608
        )
        gt_stats = cursor.fetchall()
        self.assertCountEqual(gt_stats, [(10,)])
        cursor.execute(
            f"""
            SELECT sum(ac_wes)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats_dict`
            """,  # nosec B608
        )
        gt_stats_dict = cursor.fetchall()
        self.assertCountEqual(gt_stats_dict, [(10,)])

    def test_rebuild_gt_stats(self):
        table_name_builder = TableNameBuilder(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            TEST_RUN_ID,
        )
        cursor = connections['clickhouse_write'].cursor()
        logged_query(  # DROP the partition from the non-staging entries to as a non-mv-impacting change.
            f"""
            ALTER TABLE {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`
            DROP PARTITION (%(project_guid)s, %(partition_id)s)
            """,  # nosec B608
            {'project_guid': 'project_a', 'partition_id': 0},
        )
        cursor.execute(
            f"""
            SELECT project_guid, sum(het_samples), sum(hom_samples)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_gt_stats`
            WHERE project_guid IN ('project_a', 'project_b')
            GROUP BY project_guid
            """,  # nosec B608
        )
        project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            project_gt_stats,
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
            """,  # nosec B608
        )
        gt_stats = cursor.fetchall()
        self.assertCountEqual(gt_stats, [(12, 5)])
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
            """,  # nosec B608
        )
        project_gt_stats = cursor.fetchall()
        self.assertCountEqual(
            project_gt_stats,
            [('project_b', 1, 2)],
        )
        cursor.execute(
            f"""
            SELECT sum(ac_wes), sum(ac_wgs)
            FROM
            {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/gt_stats`
            """,
        )
        gt_stats = cursor.fetchall()
        self.assertCountEqual(gt_stats, [(9, 0)])
