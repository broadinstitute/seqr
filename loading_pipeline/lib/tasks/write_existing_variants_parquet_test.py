from typing import ClassVar

import luigi.worker
import pandas as pd

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
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
    ) -> pd.DataFrame:
        worker = luigi.worker.Worker()
        task = WriteExistingVariantsParquetTask(
            reference_genome=reference_genome,
            dataset_type=dataset_type,
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        return pd.read_parquet(
            existing_variants_parquet_path(reference_genome, dataset_type, TEST_RUN_ID),
        )

    def test_snv_indel(self):
        df = self._run_task(DatasetType.SNV_INDEL)
        self.assertEqual(list(df.columns), ['key_', 'variant_id', 'geneIds'])
        df = df.sort_values('key_').reset_index(drop=True)
        self.assertEqual(
            df[['key_', 'variant_id', 'geneIds']].to_dict('records'),
            [
                {'key_': 1, 'variant_id': '1-10059-C-T', 'geneIds': ['ENSG00000177000']},
                {'key_': 7, 'variant_id': '7-1234567-AGT-A', 'geneIds': []},
                {'key_': 10, 'variant_id': '10-987654-G-A', 'geneIds': []},
            ],
        )

    def test_grch37_snv_indel(self):
        df = self._run_task(
            DatasetType.SNV_INDEL,
            reference_genome=ReferenceGenome.GRCh37,
        )
        self.assertEqual(list(df.columns), ['key_', 'variant_id', 'geneIds'])
        self.assertEqual(len(df), 0)

    def test_mito(self):
        df = self._run_task(DatasetType.MITO)
        self.assertEqual(list(df.columns), ['key_', 'variant_id'])
        self.assertEqual(len(df), 0)

    def test_sv(self):
        df = self._run_task(DatasetType.SV)
        self.assertEqual(
            list(df.columns),
            ['key_', 'variant_id', 'xpos', 'end', 'endChrom', 'geneIds'],
        )
        self.assertEqual(len(df), 0)

    def test_gcnv(self):
        df = self._run_task(DatasetType.GCNV)
        self.assertEqual(
            list(df.columns),
            ['key_', 'variant_id', 'xpos', 'start', 'end', 'num_exon', 'gene_ids'],
        )
        self.assertEqual(len(df), 0)
