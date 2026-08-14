from decimal import Decimal
from unittest.mock import Mock, patch

import google.cloud.bigquery
import hail as hl
import luigi.worker

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.paths import sex_check_table_path, tdr_metrics_path
from loading_pipeline.lib.tasks.write_sex_check_table import (
    WriteSexCheckTableTask,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_SEX_AND_RELATEDNESS_CALLSET_MT = (
    'loading_pipeline/var/test/callsets/sex_and_relatedness_1.mt'
)


class WriteSexCheckTableTaskTest(MockedDatarootTestCase):
    @patch('loading_pipeline.lib.tasks.write_tdr_metrics_files.gen_bq_table_names')
    @patch('loading_pipeline.lib.tasks.write_tdr_metrics_file.bq_metrics_query')
    @patch(
        'loading_pipeline.lib.tasks.write_sex_check_table.FeatureFlag',
    )
    def test_snv_sex_check_table_task(
        self,
        mock_ff: Mock,
        mock_bq_metrics_query: Mock,
        mock_gen_bq_table_names: Mock,
    ) -> None:
        mock_ff.EXPECT_TDR_METRICS = True
        mock_gen_bq_table_names.return_value = [
            'datarepo-7242affb.datarepo_RP_3053',
            'datarepo-5a72e31b.datarepo_RP_3056',
        ]
        mock_bq_metrics_query.side_effect = [
            iter(
                [
                    google.cloud.bigquery.table.Row(
                        (
                            'SM-NJ8MF',
                            'Unknown',
                            Decimal('0'),
                            Decimal('0'),
                            Decimal('0'),
                        ),
                        {
                            'collaborator_sample_id': 0,
                            'predicted_sex': 1,
                            'contamination_rate': 2,
                            'percent_bases_at_20x': 3,
                            'mean_coverage': 4,
                        },
                    ),
                    google.cloud.bigquery.table.Row(
                        (
                            'SM-MWOGC',
                            'Female',
                            Decimal('0'),
                            Decimal('0'),
                            Decimal('0'),
                        ),
                        {
                            'collaborator_sample_id': 0,
                            'predicted_sex': 1,
                            'contamination_rate': 2,
                            'percent_bases_at_20x': 3,
                            'mean_coverage': 4,
                        },
                    ),
                    google.cloud.bigquery.table.Row(
                        ('SM-MWKWL', 'Male', Decimal('0'), Decimal('0'), Decimal('0')),
                        {
                            'collaborator_sample_id': 0,
                            'predicted_sex': 1,
                            'contamination_rate': 2,
                            'percent_bases_at_20x': 3,
                            'mean_coverage': 4,
                        },
                    ),
                ],
            ),
            iter(
                [
                    google.cloud.bigquery.table.Row(
                        ('SM-NGE65', 'Male', Decimal('0'), Decimal('0'), Decimal('0')),
                        {
                            'collaborator_sample_id': 0,
                            'predicted_sex': 1,
                            'contamination_rate': 2,
                            'percent_bases_at_20x': 3,
                            'mean_coverage': 4,
                        },
                    ),
                    google.cloud.bigquery.table.Row(
                        ('SM-NGE5G', 'Male', Decimal('0'), Decimal('0'), Decimal('0')),
                        {
                            'collaborator_sample_id': 0,
                            'predicted_sex': 1,
                            'contamination_rate': 2,
                            'percent_bases_at_20x': 3,
                            'mean_coverage': 4,
                        },
                    ),
                    google.cloud.bigquery.table.Row(
                        ('SM-NC6LM', 'Male', Decimal('0'), Decimal('0'), Decimal('0')),
                        {
                            'collaborator_sample_id': 0,
                            'predicted_sex': 1,
                            'contamination_rate': 2,
                            'percent_bases_at_20x': 3,
                            'mean_coverage': 4,
                        },
                    ),
                ],
            ),
        ]
        worker = luigi.worker.Worker()
        write_sex_check_table = WriteSexCheckTableTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path='na',
            project_guids=['R0113_test_project'],
            run_id='manual__2024-04-03',
        )
        worker.add(write_sex_check_table)
        worker.run()
        self.assertTrue(write_sex_check_table.complete())
        sex_check_ht = hl.read_table(
            sex_check_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                'na',
            ),
        )
        self.assertEqual(
            sex_check_ht.collect(),
            [
                hl.Struct(s='SM-MWKWL', predicted_sex='M'),
                hl.Struct(s='SM-MWOGC', predicted_sex='F'),
                hl.Struct(s='SM-NC6LM', predicted_sex='M'),
                hl.Struct(s='SM-NGE5G', predicted_sex='M'),
                hl.Struct(s='SM-NGE65', predicted_sex='M'),
                hl.Struct(s='SM-NJ8MF', predicted_sex='U'),
            ],
        )
        # Check underlying tdr metrics file.
        with open(
            tdr_metrics_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                'datarepo-5a72e31b.datarepo_RP_3056',
            ),
        ) as f:
            self.assertTrue('collaborator_sample_id' in f.read())
