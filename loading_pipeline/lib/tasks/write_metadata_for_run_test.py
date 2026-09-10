import json
from unittest import mock
from unittest.mock import Mock

import luigi.worker

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.misc.validation import ALL_VALIDATIONS
from loading_pipeline.lib.paths import relatedness_check_tsv_path
from loading_pipeline.lib.tasks.write_metadata_for_run import WriteMetadataForRunTask
from loading_pipeline.lib.test.misc import copy_project_pedigree_to_mocked_dir
from loading_pipeline.lib.test.mock_complete_task import MockCompleteTask
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_VCF = 'loading_pipeline/var/test/callsets/1kg_30variants.vcf'
TEST_PEDIGREE_3_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_3_remap.tsv'
TEST_PEDIGREE_4_REMAP_2 = (
    'loading_pipeline/var/test/pedigrees/test_pedigree_4_remap_2.tsv'
)
TEST_SAMPLE_QC_JSON = 'loading_pipeline/var/test/sample_qc_1.json'


class WriteMetadataForRunTaskTest(MockedDatarootTestCase):
    @mock.patch(
        'loading_pipeline.lib.tasks.write_metadata_for_run.sample_qc_json_path',
        lambda *_: TEST_SAMPLE_QC_JSON,
    )
    @mock.patch('loading_pipeline.lib.tasks.write_metadata_for_run.FeatureFlag')
    @mock.patch(
        'loading_pipeline.lib.tasks.write_sex_check_table.WriteTDRMetricsFilesTask',
    )
    @mock.patch(
        'loading_pipeline.lib.tasks.write_metadata_for_run.WriteSampleQCJsonTask',
    )
    def test_write_metadata_for_run_task(
        self,
        write_sample_qc_json_task: Mock,
        write_tdr_metrics_task: Mock,
        mock_ff: Mock,
    ) -> None:
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0113_test_project',
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_4_REMAP_2,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0114_project4',
        )
        mock_ff.EXPECT_TDR_METRICS = True
        write_tdr_metrics_task.return_value = MockCompleteTask()
        write_sample_qc_json_task.return_value = MockCompleteTask()
        worker = luigi.worker.Worker()
        write_metadata_for_run_task = WriteMetadataForRunTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_VCF,
            project_guids=['R0113_test_project', 'R0114_project4'],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id='run_123456',
        )
        worker.add(write_metadata_for_run_task)
        worker.run()
        self.assertTrue(
            'run_123456/metadata.json' in write_metadata_for_run_task.output().path,
        )
        self.assertTrue(write_metadata_for_run_task.complete())
        with write_metadata_for_run_task.output().open('r') as f:
            self.assertDictEqual(
                json.load(f),
                {
                    'callsets': [TEST_VCF],
                    'project_guids': ['R0113_test_project', 'R0114_project4'],
                    'failed_family_samples': {
                        'missing_samples': {
                            'efg_1': {
                                # This sample is present in the callset, but intentionally
                                # mapped away
                                'samples': ['NA20888_1'],
                                'reasons': ["Missing samples: {'NA20888_1'}"],
                            },
                        },
                        'relatedness_check': {},
                        'sex_check': {},
                        'ploidy_check': {},
                    },
                    'family_samples': {
                        'abc_1': [
                            'HG00731_1',
                            'HG00732_1',
                            'HG00733_1',
                        ],
                        '123_1': ['NA19675_1'],
                        '234_1': ['NA19678_1'],
                        '345_1': ['NA19679_1'],
                        '456_1': ['NA20870_1'],
                        '567_1': ['NA20872_1'],
                        '678_1': ['NA20874_1'],
                        '789_1': ['NA20875_1'],
                        '890_1': ['NA20876_1'],
                        '901_1': ['NA20877_1'],
                        'bcd_1': ['NA20878_1'],
                        'cde_1': ['NA20881_1'],
                        'def_1': ['NA20885_1'],
                    },
                    'run_id': 'run_123456',
                    'sample_type': SampleType.WGS.value,
                    'relatedness_check_file_path': relatedness_check_tsv_path(
                        ReferenceGenome.GRCh38,
                        DatasetType.SNV_INDEL,
                        TEST_VCF,
                    ),
                    'sample_qc': {
                        'HG00731_1': {'filter_flags': ['coverage', 'contamination']},
                        'HG00732_1': {'filter_flags': ['coverage']},
                        'HG00733_1': {'filter_flags': ['contamination']},
                        'NA19675_1': {'filter_flags': []},
                        'NA20888_1': {'filter_flags': ['sample_failed']},
                    },
                },
            )

    @mock.patch('loading_pipeline.lib.tasks.write_metadata_for_run.FeatureFlag')
    def test_write_metadata_for_run_task_without_tdr_metrics(
        self,
        mock_ff: Mock,
    ) -> None:
        # When WriteSampleQCJsonTask is not a requirement, every project's
        # remapped and subsetted callset must still be collected.
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0113_test_project',
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_4_REMAP_2,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0114_project4',
        )
        mock_ff.EXPECT_TDR_METRICS = False
        worker = luigi.worker.Worker()
        write_metadata_for_run_task = WriteMetadataForRunTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_VCF,
            project_guids=['R0113_test_project', 'R0114_project4'],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id='run_123457',
        )
        worker.add(write_metadata_for_run_task)
        worker.run()
        self.assertTrue(write_metadata_for_run_task.complete())
        with write_metadata_for_run_task.output().open('r') as f:
            metadata_json = json.load(f)
        self.assertDictEqual(
            metadata_json['family_samples'],
            {
                'abc_1': [
                    'HG00731_1',
                    'HG00732_1',
                    'HG00733_1',
                ],
                '123_1': ['NA19675_1'],
                '234_1': ['NA19678_1'],
                '345_1': ['NA19679_1'],
                '456_1': ['NA20870_1'],
                '567_1': ['NA20872_1'],
                '678_1': ['NA20874_1'],
                '789_1': ['NA20875_1'],
                '890_1': ['NA20876_1'],
                '901_1': ['NA20877_1'],
                'bcd_1': ['NA20878_1'],
                'cde_1': ['NA20881_1'],
                'def_1': ['NA20885_1'],
            },
        )
        self.assertDictEqual(metadata_json['sample_qc'], {})
