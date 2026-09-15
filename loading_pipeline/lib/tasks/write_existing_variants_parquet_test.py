from typing import ClassVar

import hail as hl
import luigi.worker

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.misc.io import import_parquet
from loading_pipeline.lib.paths import existing_variants_parquet_path
from loading_pipeline.lib.tasks.write_existing_variants_parquet import (
    WriteExistingVariantsParquetTask,
)
from loading_pipeline.lib.test.clickhouse_schema_testcase import (
    ClickhouseSchemaTestCase,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_RUN_ID = 'manual__2024-04-03'


class WriteExistingVariantsParquetTest(
    MockedDatarootTestCase,
    ClickhouseSchemaTestCase,
):
    fixtures: ClassVar = ['clickhouse_test']

    def _run_task(
        self,
        dataset_type: DatasetType,
        reference_genome: ReferenceGenome = ReferenceGenome.GRCh38,
    ) -> hl.Table:
        worker = luigi.worker.Worker()
        task = WriteExistingVariantsParquetTask(
            reference_genome=reference_genome,
            dataset_type=dataset_type,
            sample_type=SampleType.WGS,
            callset_path='fake_callset',
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        return import_parquet(
            existing_variants_parquet_path(reference_genome, dataset_type, TEST_RUN_ID),
            reference_genome,
            dataset_type,
        )

    def test_snv_indel(self):
        ht = self._run_task(DatasetType.SNV_INDEL)
        self.assertEqual(list(ht.row), ['key_', 'locus', 'alleles'])
        self.assertEqual(
            ht.collect(),
            [
                hl.Struct(
                    key_=1,
                    locus=hl.Locus(
                        contig='chr1',
                        position=878314,
                        reference_genome='GRCh38',
                    ),
                    alleles=['G', 'C'],
                ),
                hl.Struct(
                    key_=7,
                    locus=hl.Locus(
                        contig='chr7',
                        position=1234567,
                        reference_genome='GRCh38',
                    ),
                    alleles=['AGT', 'A'],
                ),
                hl.Struct(
                    key_=10,
                    locus=hl.Locus(
                        contig='chr10',
                        position=987654,
                        reference_genome='GRCh38',
                    ),
                    alleles=['G', 'A'],
                ),
            ],
        )

    def test_grch37_snv_indel(self):
        ht = self._run_task(
            DatasetType.SNV_INDEL,
            reference_genome=ReferenceGenome.GRCh37,
        )
        self.assertEqual(list(ht.row), ['key_', 'locus', 'alleles'])
        self.assertEqual(ht.count(), 0)

    def test_mito(self):
        ht = self._run_task(DatasetType.MITO)
        self.assertEqual(list(ht.row), ['key_', 'locus', 'alleles'])
        self.assertEqual(ht.count(), 0)

    def test_sv(self):
        ht = self._run_task(DatasetType.SV)
        self.assertEqual(list(ht.row), ['key_', 'variant_id', 'end', 'endChrom'])
        self.assertEqual(ht.count(), 0)

    def test_gcnv(self):
        ht = self._run_task(DatasetType.GCNV)
        self.assertEqual(list(ht.row), ['key_', 'variant_id'])
        self.assertEqual(ht.count(), 0)
