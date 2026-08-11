import hail as hl
import luigi.worker
import pandas as pd

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.misc.validation import ALL_VALIDATIONS
from loading_pipeline.lib.paths import (
    new_entries_parquet_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.exports.write_new_entries_parquet import (
    WriteNewEntriesParquetTask,
)
from loading_pipeline.lib.test.misc import (
    convert_ndarray_to_list,
    copy_project_pedigree_to_mocked_dir,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_PEDIGREE_3_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_3_remap.tsv'
TEST_PEDIGREE_4_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_4_remap.tsv'
TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'
TEST_MITO_EXPORT_PEDIGREE = (
    'loading_pipeline/var/test/pedigrees/test_mito_export_pedigree.tsv'
)
TEST_SNV_INDEL_VCF = 'loading_pipeline/var/test/callsets/1kg_30variants.vcf'
TEST_MITO_CALLSET = 'loading_pipeline/var/test/callsets/mito_1.mt'
TEST_SV_VCF_2 = 'loading_pipeline/var/test/callsets/sv_2.vcf'
TEST_GCNV_BED_FILE = 'loading_pipeline/var/test/callsets/gcnv_1.tsv'
TEST_SNV_INDEL_ANNOTATIONS = (
    'loading_pipeline/var/test/exports/GRCh38/SNV_INDEL/annotations.ht'
)
TEST_MITO_ANNOTATIONS = 'loading_pipeline/var/test/exports/GRCh38/MITO/annotations.ht'
TEST_SV_ANNOTATIONS = 'loading_pipeline/var/test/exports/GRCh38/SV/annotations.ht'
TEST_GCNV_ANNOTATIONS = 'loading_pipeline/var/test/exports/GRCh38/GCNV/annotations.ht'

TEST_RUN_ID = 'manual__2024-04-03'


class WriteNewEntriesParquetTest(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()
        ht = hl.read_table(
            TEST_SNV_INDEL_ANNOTATIONS,
        )
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
            ),
        )
        ht = hl.read_table(
            TEST_MITO_ANNOTATIONS,
        )
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.MITO,
            ),
        )
        ht = hl.read_table(
            TEST_SV_ANNOTATIONS,
        )
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SV,
            ),
        )
        ht = hl.read_table(TEST_GCNV_ANNOTATIONS)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
            ),
        )

    def test_write_new_entries_parquet(self):
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0113_test_project',
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_4_REMAP,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0114_project4',
        )
        worker = luigi.worker.Worker()
        task = WriteNewEntriesParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_SNV_INDEL_VCF,
            project_guids=['R0113_test_project', 'R0114_project4'],
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
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.to_dict('records'))
        self.assertEqual(
            export_json[:2],
            [
                {
                    'key': 0,
                    'project_guid': 'R0113_test_project',
                    'family_guid': 'abc_1',
                    'sample_type': 'WGS',
                    'xpos': 1000876499,
                    'geneIds': ['ENSG00000187634'],
                    'filters': [],
                    'calls': [
                        {
                            'sampleId': 'HG00731_1',
                            'gt': 2,
                            'gq': 21,
                            'ab': 1.0,
                            'dp': 7,
                        },
                        {
                            'sampleId': 'HG00732_1',
                            'gt': 2,
                            'gq': 24,
                            'ab': 1.0,
                            'dp': 8,
                        },
                        {
                            'sampleId': 'HG00733_1',
                            'gt': 2,
                            'gq': 12,
                            'ab': 1.0,
                            'dp': 4,
                        },
                    ],
                    'sign': 1,
                },
                {
                    'key': 1,
                    'project_guid': 'R0113_test_project',
                    'family_guid': 'abc_1',
                    'sample_type': 'WGS',
                    'xpos': 1000878314,
                    'geneIds': ['ENSG00000187634'],
                    'filters': ['VQSRTrancheSNP99.00to99.90'],
                    'calls': [
                        {
                            'sampleId': 'HG00731_1',
                            'gt': 1,
                            'gq': 30,
                            'ab': 0.3333333432674408,
                            'dp': 3,
                        },
                        {'sampleId': 'HG00732_1', 'gt': 0, 'gq': 6, 'ab': 0.0, 'dp': 2},
                        {
                            'sampleId': 'HG00733_1',
                            'gt': 1,
                            'gq': 61,
                            'ab': 0.6000000238418579,
                            'dp': 5,
                        },
                    ],
                    'sign': 1,
                },
            ],
        )

    def test_mito_write_new_entries_parquet(self):
        copy_project_pedigree_to_mocked_dir(
            TEST_MITO_EXPORT_PEDIGREE,
            ReferenceGenome.GRCh38,
            DatasetType.MITO,
            SampleType.WGS,
            'R0116_test_project3',
        )
        worker = luigi.worker.Worker()
        task = WriteNewEntriesParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.MITO,
            sample_type=SampleType.WGS,
            callset_path=TEST_MITO_CALLSET,
            project_guids=['R0116_test_project3'],
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
                DatasetType.MITO,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.to_dict('records'))
        self.assertEqual(
            export_json,
            [
                {
                    'key': 998,
                    'project_guid': 'R0116_test_project3',
                    'family_guid': 'family_1',
                    'sample_type': 'WGS',
                    'xpos': 25000000008,
                    'filters': [],
                    'calls': [
                        {
                            'sampleId': 'RGP_1270_2',
                            'gt': 2,
                            'dp': 4216,
                            'hl': 0.999,
                            'mitoCn': 224,
                            'contamination': 0.0,
                        },
                    ],
                    'sign': 1,
                },
            ],
        )

    def test_sv_write_new_entries_parquet(self):
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        task = WriteNewEntriesParquetTask(
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
        self.assertEqual(
            export_json,
            [
                {
                    'key': 727,
                    'project_guid': 'R0115_test_project2',
                    'family_guid': 'family_2_1',
                    'xpos': 1001025886,
                    'geneIds': ['ENSG00000188157'],
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

    def test_gcnv_write_new_entries_parquet(self):
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.GCNV,
            SampleType.WES,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        task = WriteNewEntriesParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.GCNV,
            sample_type=SampleType.WES,
            callset_path=TEST_GCNV_BED_FILE,
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
                DatasetType.GCNV,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.to_dict('records'))
        self.assertEqual(
            export_json,
            [
                {
                    'key': 0,
                    'project_guid': 'R0115_test_project2',
                    'family_guid': 'family_2_1',
                    'xpos': 1000939203,
                    'filters': [],
                    'calls': [
                        {
                            'sampleId': 'RGP_164_1',
                            'gt': 1,
                            'cn': 1,
                            'qs': 4,
                            'defragged': False,
                            'start': 100006937,
                            'end': 100007881,
                            'numExon': 2,
                            'geneIds': ['ENSG00000117620', 'ENSG00000283761'],
                            'newCall': False,
                            'prevCall': True,
                            'prevOverlap': False,
                        },
                        {
                            'sampleId': 'RGP_164_2',
                            'gt': 1,
                            'cn': 1,
                            'qs': 5,
                            'defragged': False,
                            'start': 100017585,
                            'end': 100023213,
                            'numExon': 1,
                            'geneIds': ['ENSG00000117620', 'ENSG00000283761'],
                            'newCall': False,
                            'prevCall': False,
                            'prevOverlap': False,
                        },
                        {
                            'sampleId': 'RGP_164_3',
                            'gt': 2,
                            'cn': 0,
                            'qs': 30,
                            'defragged': False,
                            'start': 100017585,
                            'end': 100023213,
                            'numExon': 1,
                            'geneIds': ['ENSG00000117620', 'ENSG00000283761'],
                            'newCall': False,
                            'prevCall': True,
                            'prevOverlap': False,
                        },
                        {
                            'sampleId': 'RGP_164_4',
                            'gt': 2,
                            'cn': 0,
                            'qs': 30,
                            'defragged': False,
                            'start': 100017586,
                            'end': 100023212,
                            'numExon': 2,
                            'geneIds': ['ENSG00000283761', 'ENSG22222222222'],
                            'newCall': False,
                            'prevCall': True,
                            'prevOverlap': False,
                        },
                    ],
                    'sign': 1,
                },
            ],
        )
