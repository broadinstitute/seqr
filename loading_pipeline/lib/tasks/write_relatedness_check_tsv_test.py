import shutil

import luigi.worker

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.paths import relatedness_check_table_path
from loading_pipeline.lib.tasks.write_relatedness_check_tsv import (
    WriteRelatednessCheckTsvTask,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_RELATEDNESS_CHECK_1 = (
    'loading_pipeline/var/test/relatedness_check/test_relatedness_check_1.ht'
)
TEST_VCF = 'loading_pipeline/var/test/callsets/1kg_30variants.vcf'
TEST_RUN_ID = 'manual__2024-04-03'


class WriteRelatednessCheckTsvTaskTest(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()
        shutil.copytree(
            TEST_RELATEDNESS_CHECK_1,
            relatedness_check_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_VCF,
            ),
        )

    def test_write_relatedness_check_tsv_task(
        self,
    ) -> None:
        worker = luigi.worker.Worker()
        task = WriteRelatednessCheckTsvTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            callset_path=TEST_VCF,
            run_id=TEST_RUN_ID,
            sample_type=SampleType.WES,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.complete())
        with task.output().open('r') as f:
            lines = f.readlines()
            expected_lines = [
                'i\tj\tibd0\tibd1\tibd2\tpi_hat\n',
                'HG00731_1\tHG00733_1\t0\t1\t0\t5.0000e-01\n',
                'HG00732_1\tHG00733_1\t0\t1\t0\t5.0000e-01\n',
            ]
            for expected_line, actual_line in zip(expected_lines, lines, strict=False):
                self.assertEqual(expected_line, actual_line)
