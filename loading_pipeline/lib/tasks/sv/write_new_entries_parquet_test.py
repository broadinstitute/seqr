import os

import luigi.worker
import pandas as pd

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.misc.validation import ALL_VALIDATIONS
from loading_pipeline.lib.paths import (
    existing_variants_parquet_path,
    new_entries_parquet_path,
)
from loading_pipeline.lib.tasks.sv.write_new_entries_parquet import (
    WriteNewSvEntriesParquetTask,
)
from loading_pipeline.lib.test.misc import (
    convert_ndarray_to_list,
    copy_project_pedigree_to_mocked_dir,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'
TEST_SV_VCF_2 = 'loading_pipeline/var/test/callsets/sv_2.vcf'

TEST_RUN_ID = 'manual__2024-04-03'


class WriteNewEntriesParquetTest(MockedDatarootTestCase):
    def test_sv_write_new_entries_parquet(self):
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0115_test_project2',
        )
        existing_variants_path = existing_variants_parquet_path(
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            TEST_RUN_ID,
        )
        os.makedirs(os.path.dirname(existing_variants_path), exist_ok=True)
        pd.DataFrame(
            {
                'variant_id': ['BND_chr1_6'],
                'key_': [727],
                'end': [180928],
                'endChrom': ['chr5'],
            },
        ).to_parquet(existing_variants_path)
        worker = luigi.worker.Worker()
        task = WriteNewSvEntriesParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SV,
            sample_type=SampleType.WGS,
            callset_path=TEST_SV_VCF_2,
            project_guids=['R0115_test_project2'],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_entries_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SV,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.to_dict('records'))
        self.assertEqual(len(export_json), 2)
        self.assertEqual(
            export_json[:1],
            [
                {
                    'variantId': 'BND_chr1_6',
                    'project_guid': 'R0115_test_project2',
                    'family_guid': 'family_2_1',
                    'filters': ['HIGH_SR_BACKGROUND', 'UNRESOLVED'],
                    'calls': [
                        {
                            'sampleId': 'RGP_164_1',
                            'gt': 0,
                            'cn': None,
                            'gq': 99,
                            'newCall': True,
                            'prevCall': False,
                            'prevNumAlt': None,
                        },
                        {
                            'sampleId': 'RGP_164_2',
                            'gt': 1,
                            'cn': None,
                            'gq': 31,
                            'newCall': True,
                            'prevCall': False,
                            'prevNumAlt': None,
                        },
                        {
                            'sampleId': 'RGP_164_3',
                            'gt': 0,
                            'cn': None,
                            'gq': 99,
                            'newCall': True,
                            'prevCall': False,
                            'prevNumAlt': None,
                        },
                        {
                            'sampleId': 'RGP_164_4',
                            'gt': 0,
                            'cn': None,
                            'gq': 99,
                            'newCall': True,
                            'prevCall': False,
                            'prevNumAlt': None,
                        },
                    ],
                    'sign': 1,
                },
            ],
        )
