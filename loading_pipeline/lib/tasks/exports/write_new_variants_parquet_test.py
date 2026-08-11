from unittest import mock
from unittest.mock import Mock

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
    new_variants_parquet_path,
    new_variants_table_path,
    remapped_and_subsetted_callset_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.exports.write_new_variants_parquet import (
    WriteNewVariantsParquetTask,
)
from loading_pipeline.lib.test.misc import convert_ndarray_to_list
from loading_pipeline.lib.test.mock_complete_task import MockCompleteTask
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

TEST_SNV_INDEL_ANNOTATIONS = (
    'loading_pipeline/var/test/exports/GRCh38/SNV_INDEL/annotations.ht'
)
TEST_GRCH37_SNV_INDEL_ANNOTATIONS = (
    'loading_pipeline/var/test/exports/GRCh37/SNV_INDEL/annotations.ht'
)
TEST_MITO_ANNOTATIONS = 'loading_pipeline/var/test/exports/GRCh38/MITO/annotations.ht'
TEST_SV_ANNOTATIONS = 'loading_pipeline/var/test/exports/GRCh38/SV/annotations.ht'
TEST_GCNV_ANNOTATIONS = 'loading_pipeline/var/test/exports/GRCh38/GCNV/annotations.ht'

TEST_RUN_ID = 'manual__2024-04-03'


class WriteNewVariantsParquetTest(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()
        ht = hl.read_table(
            TEST_SNV_INDEL_ANNOTATIONS,
        )
        ht.write(
            new_variants_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        ht = hl.read_table(
            TEST_GRCH37_SNV_INDEL_ANNOTATIONS,
        )
        ht.write(
            new_variants_table_path(
                ReferenceGenome.GRCh37,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        ht = hl.read_table(
            TEST_MITO_ANNOTATIONS,
        )
        ht.write(
            new_variants_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.MITO,
                TEST_RUN_ID,
            ),
        )
        ht = hl.read_table(
            TEST_SV_ANNOTATIONS,
        )
        ht.write(
            new_variants_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SV,
                TEST_RUN_ID,
            ),
        )
        ht = hl.read_table(TEST_GCNV_ANNOTATIONS)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
            ),
        )
        ht.write(
            remapped_and_subsetted_callset_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                'fake_callset',
                'fake_project',
            ),
        )

    @mock.patch(
        'loading_pipeline.lib.tasks.exports.write_new_variants_parquet.WriteNewVariantsTableTask',
    )
    def test_write_new_variants_parquet_test(
        self,
        mock_write_new_variants_task,
    ) -> None:
        mock_write_new_variants_task.return_value = MockCompleteTask()
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path='fake_callset',
            project_guids=[
                'fake_project',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        export_json[0]['sortedTranscriptConsequences'] = [
            export_json[0]['sortedTranscriptConsequences'][0],
        ]
        self.assertEqual(
            export_json,
            [
                {
                    'key': 0,
                    'sortedMotifFeatureConsequences': [
                        {
                            'consequenceTerms': ['TF_binding_site_variant'],
                        },
                    ],
                    'sortedRegulatoryFeatureConsequences': [
                        {
                            'consequenceTerms': ['regulatory_region_variant'],
                        },
                    ],
                    'sortedTranscriptConsequences': [
                        {
                            'alphamissensePathogenicity': None,
                            'canonical': 1,
                            'consequenceTerms': ['missense_variant'],
                            'extendedIntronicSpliceRegionVariant': False,
                            'fiveutrConsequence': None,
                            'geneId': 'ENSG00000187634',
                            'isManeSelect': True,
                        },
                    ],
                },
            ],
        )

    @mock.patch(
        'loading_pipeline.lib.tasks.exports.write_new_variants_parquet.WriteNewVariantsTableTask',
    )
    def test_grch37_write_new_variants_parquet_test(
        self,
        mock_write_new_variants_task,
    ) -> None:
        mock_write_new_variants_task.return_value = MockCompleteTask()
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh37,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path='fake_callset',
            project_guids=[
                'fake_project',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh37,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        export_json[0]['sortedTranscriptConsequences'] = [
            export_json[0]['sortedTranscriptConsequences'][0],
        ]
        self.assertEqual(
            export_json,
            [
                {
                    'key': 1424,
                    'sortedTranscriptConsequences': [
                        {
                            'canonical': 1,
                            'consequenceTerms': ['missense_variant'],
                            'geneId': 'ENSG00000186092',
                        },
                    ],
                },
            ],
        )

    @mock.patch(
        'loading_pipeline.lib.tasks.exports.write_new_variants_parquet.WriteNewVariantsTableTask',
    )
    def test_mito_write_new_variants_parquet_test(
        self,
        write_new_variants_table_task: Mock,
    ) -> None:
        write_new_variants_table_task.return_value = MockCompleteTask()
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.MITO,
            sample_type=SampleType.WGS,
            callset_path='fake_callset',
            project_guids=[
                'fake_project',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.MITO,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        export_json[0]['sortedTranscriptConsequences'] = [
            export_json[0]['sortedTranscriptConsequences'][0],
        ]
        self.assertEqual(
            export_json,
            [
                {
                    'key': 998,
                    'variantId': 'M-8-G-T',
                    'rsid': 'rs1603218446',
                    'liftedOverPos': 578,
                    'commonLowHeteroplasmy': True,
                    'haplogroupDefining': False,
                    'mitotip': 'likely_pathogenic',
                    'sortedTranscriptConsequences': [
                        {
                            'aminoAcids': None,
                            'biotype': 'Mt_tRNA',
                            'canonical': 1,
                            'codons': None,
                            'consequenceTerms': ['non_coding_transcript_exon_variant'],
                            'geneId': 'ENSG00000210049',
                            'hgvsc': 'ENST00000387314.1:n.2T>C',
                            'hgvsp': None,
                            'loftee': {'isLofNagnag': None, 'lofFilters': None},
                            'majorConsequence': 'non_coding_transcript_exon_variant',
                            'transcriptId': 'ENST00000387314',
                            'transcriptRank': 0,
                        },
                    ],
                },
            ],
        )

    @mock.patch(
        'loading_pipeline.lib.tasks.exports.write_new_variants_parquet.WriteNewVariantsTableTask',
    )
    def test_sv_write_new_variants_parquet_test(
        self,
        write_new_variants_table_task: Mock,
    ) -> None:
        write_new_variants_table_task.return_value = MockCompleteTask()
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SV,
            sample_type=SampleType.WGS,
            callset_path='fake_callset',
            project_guids=[
                'fake_project',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SV,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        export_json[0]['sortedGeneConsequences'] = [
            export_json[0]['sortedGeneConsequences'][0],
        ]
        self.assertEqual(
            export_json,
            [
                {
                    'key': 727,
                    'xpos': 1001025886,
                    'chrom': '1',
                    'pos': 1025886,
                    'end': 1028192,
                    'rg37LocusEnd': {'contig': '1', 'position': 963572},
                    'variantId': 'BND_chr1_6',
                    'liftedOverChrom': '1',
                    'liftedOverPos': 961266,
                    'algorithms': 'manta',
                    'bothsidesSupport': None,
                    'cpxIntervals': [
                        {'chrom': '1', 'start': 1025886, 'end': 1025986, 'type': 'DUP'},
                        {'chrom': '1', 'start': 1025886, 'end': 1028192, 'type': 'INV'},
                    ],
                    'endChrom': '2',
                    'svSourceDetail': None,
                    'svType': 'CPX',
                    'svTypeDetail': 'dupINV',
                    'predictions': {'strvctvre': None},
                    'populations': {'gnomad_svs': None},
                    'sortedGeneConsequences': [
                        {'geneId': 'ENSG00000188157', 'majorConsequence': 'INTRONIC'},
                    ],
                },
            ],
        )

    @mock.patch(
        'loading_pipeline.lib.tasks.exports.write_new_variants_parquet.UpdateVariantAnnotationsTableWithNewVariantsTask',
    )
    @mock.patch(
        'loading_pipeline.lib.tasks.exports.write_new_variants_parquet.get_callset_ht',
    )
    def test_gcnv_write_new_variants_parquet_test(
        self,
        get_callset_ht: Mock,
        update_variant_annotations_task: Mock,
    ) -> None:
        get_callset_ht.return_value = hl.read_table(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
            ),
        )
        update_variant_annotations_task.return_value = MockCompleteTask()
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.GCNV,
            sample_type=SampleType.WES,
            callset_path='fake_callset',
            project_guids=[
                'fake_project',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        self.assertEqual(
            export_json,
            [
                {
                    'key': 0,
                    'xpos': 1000939203,
                    'chrom': '1',
                    'pos': 939203,
                    'end': 939558,
                    'rg37LocusEnd': {'contig': '1', 'position': 874938},
                    'variantId': 'suffix_16456_DEL',
                    'liftedOverChrom': '1',
                    'liftedOverPos': 874583,
                    'numExon': 1,
                    'svType': 'DUP',
                    'predictions': {'strvctvre': 0.4490000009536743},
                    'populations': {
                        'sv_callset': {
                            'ac': 1,
                            'af': 4.3387713958509266e-05,
                            'an': 23048,
                            'het': None,
                            'hom': None,
                        },
                    },
                    'sortedGeneConsequences': [
                        {'geneId': 'ENSG00000187634', 'majorConsequence': 'LOF'},
                    ],
                },
            ],
        )
