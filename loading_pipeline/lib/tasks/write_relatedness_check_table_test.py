import shutil
from unittest.mock import patch

import hail as hl
import luigi.worker

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.misc.io import import_vcf
from loading_pipeline.lib.paths import (
    postprocessed_callset_path,
    relatedness_check_table_path,
    valid_reference_dataset_path,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.write_relatedness_check_table import (
    WriteRelatednessCheckTableTask,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_GNOMAD_QC_HT = (
    'loading_pipeline/var/test/reference_datasets/GRCh38/gnomad_qc/1.0.ht'
)
TEST_VCF = 'loading_pipeline/var/test/callsets/1kg_30variants.vcf'
TEST_RUN_ID = 'manual__2024-04-03'


class WriteRelatednessCheckTableTaskTest(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()
        shutil.copytree(
            TEST_GNOMAD_QC_HT,
            valid_reference_dataset_path(
                ReferenceGenome.GRCh38,
                ReferenceDataset.gnomad_qc,
            ),
        )

        # Force imported callset to be complete
        ht = import_vcf(TEST_VCF, ReferenceGenome.GRCh38)
        ht = ht.annotate_globals(validated_sample_type=SampleType.WGS.value)
        ht = ht.annotate_rows(**{'info.AF': ht.info.AF})
        ht.write(
            postprocessed_callset_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_VCF,
            ),
        )

    def test_relatedness_check_table_task_gnomad_qc_updated(
        self,
    ) -> None:
        self.assertEqual(
            hl.eval(
                hl.read_table(
                    valid_reference_dataset_path(
                        ReferenceGenome.GRCh38,
                        ReferenceDataset.gnomad_qc,
                    ),
                ).version,
            ),
            '1.0',
        )
        with (
            patch.object(
                ReferenceDataset,
                'version',
                return_value='2.0',
            ),
            patch.object(
                ReferenceDataset,
                'get_ht',
                lambda *_: hl.Table.parallelize(
                    [],
                    hl.tstruct(
                        locus=hl.tlocus('GRCh38'),
                        alleles=hl.tarray(hl.tstr),
                    ),
                    key=['locus', 'alleles'],
                    globals=hl.Struct(version='2.0'),
                ),
            ),
        ):
            worker = luigi.worker.Worker()
            task = WriteRelatednessCheckTableTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.SNV_INDEL,
                run_id=TEST_RUN_ID,
                sample_type=SampleType.WGS,
                callset_path=TEST_VCF,
            )
            worker.add(task)
            worker.run()
            self.assertTrue(task.complete())
            self.assertEqual(
                hl.eval(
                    hl.read_table(
                        valid_reference_dataset_path(
                            ReferenceGenome.GRCh38,
                            ReferenceDataset.gnomad_qc,
                        ),
                    ).version,
                ),
                '2.0',
            )
            ht = hl.read_table(
                relatedness_check_table_path(
                    ReferenceGenome.GRCh38,
                    DatasetType.SNV_INDEL,
                    TEST_VCF,
                ),
            )
            self.assertEqual(
                ht.collect(),
                [],
            )
