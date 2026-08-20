from unittest import mock
from unittest.mock import Mock

import hail as hl
import luigi.worker
import pandas as pd

from loading_pipeline.lib.annotations.expression_helpers import (
    get_expr_for_variant_id,
)
from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.misc.validation import ALL_VALIDATIONS
from loading_pipeline.lib.paths import (
    new_variants_parquet_path,
    remapped_and_subsetted_callset_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.exports.write_new_variants_parquet import (
    WriteNewVariantsParquetTask,
)
from loading_pipeline.lib.tasks.write_remapped_and_subsetted_callset import (
    WriteRemappedAndSubsettedCallsetTask,
)
from loading_pipeline.lib.test.misc import (
    convert_ndarray_to_list,
    copy_project_pedigree_to_mocked_dir,
)
from loading_pipeline.lib.test.mock_complete_task import MockCompleteTask
from loading_pipeline.lib.test.mocked_reference_datasets_testcase import (
    MockedReferenceDatasetsTestCase,
)
from loading_pipeline.var.test.vep.mock_vep_data import (
    MOCK_37_VEP_DATA,
    MOCK_38_VEP_DATA,
)

TEST_SNV_INDEL_VCF = 'loading_pipeline/var/test/callsets/1kg_30variants.vcf'
TEST_PEDIGREE_3_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_3_remap.tsv'
TEST_MITO_CALLSET = 'loading_pipeline/var/test/callsets/mito_1.mt'
TEST_MITO_EXPORT_PEDIGREE = (
    'loading_pipeline/var/test/pedigrees/test_mito_export_pedigree.tsv'
)
TEST_SV_VCF_2 = 'loading_pipeline/var/test/callsets/sv_2.vcf'
TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'
TEST_GCNV_ANNOTATIONS = 'loading_pipeline/var/test/exports/GRCh38/GCNV/annotations.ht'

TEST_RUN_ID = 'manual__2024-04-03'


def _write_prior_annotations_table(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    sample_type: SampleType,
    pedigree_path: str,
    callset_path: str,
    project_guid: str,
    exclude_variant_id: str,
    max_key_: int,
    keyed_by_variant_id: bool,
) -> None:
    # Runs the real WriteRemappedAndSubsettedCallsetTask (no VEP/DB involved)
    # to get a real callset, then snapshots everything except
    # `exclude_variant_id` as a "prior" annotations table so that
    # WriteNewVariantsTableTask's anti-join deterministically leaves
    # exactly one new variant to annotate.
    copy_project_pedigree_to_mocked_dir(
        pedigree_path,
        reference_genome,
        dataset_type,
        sample_type,
        project_guid,
    )
    worker = luigi.worker.Worker()
    wrsc_task = WriteRemappedAndSubsettedCallsetTask(
        reference_genome=reference_genome,
        dataset_type=dataset_type,
        run_id=TEST_RUN_ID,
        sample_type=sample_type,
        callset_path=callset_path,
        project_guids=[project_guid],
        project_i=0,
        validations_to_skip=[ALL_VALIDATIONS],
        skip_expect_tdr_metrics=True,
    )
    worker.add(wrsc_task)
    worker.run()
    callset_ht = hl.read_matrix_table(wrsc_task.output().path).rows()
    variant_id_expr = (
        callset_ht.variant_id
        if keyed_by_variant_id
        else get_expr_for_variant_id(callset_ht)
    )
    prior_ht = callset_ht.filter(variant_id_expr != exclude_variant_id)
    prior_ht = prior_ht.select()
    prior_ht = prior_ht.add_index(name='key_')
    prior_ht = prior_ht.annotate_globals(max_key_=max_key_)
    prior_ht.write(variant_annotations_table_path(reference_genome, dataset_type))


class WriteNewVariantsParquetTest(MockedReferenceDatasetsTestCase):
    def setUp(self) -> None:
        super().setUp()
        _write_prior_annotations_table(
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            TEST_PEDIGREE_3_REMAP,
            TEST_SNV_INDEL_VCF,
            'R0113_test_project',
            exclude_variant_id='1-876499-A-G',
            max_key_=-1,
            keyed_by_variant_id=False,
        )
        _write_prior_annotations_table(
            ReferenceGenome.GRCh37,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            TEST_PEDIGREE_3_REMAP,
            TEST_SNV_INDEL_VCF,
            'R0113_test_project',
            exclude_variant_id='1-69134-A-G',
            max_key_=1423,
            keyed_by_variant_id=False,
        )
        _write_prior_annotations_table(
            ReferenceGenome.GRCh38,
            DatasetType.MITO,
            SampleType.WGS,
            TEST_MITO_EXPORT_PEDIGREE,
            TEST_MITO_CALLSET,
            'R0116_test_project3',
            exclude_variant_id='M-8-G-T',
            max_key_=997,
            keyed_by_variant_id=False,
        )
        _write_prior_annotations_table(
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            TEST_PEDIGREE_5,
            TEST_SV_VCF_2,
            'R0115_test_project2',
            exclude_variant_id='BND_chr1_6',
            max_key_=726,
            keyed_by_variant_id=True,
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
        'loading_pipeline.lib.tasks.write_new_variants_table.load_gencode_ensembl_to_refseq_id',
    )
    @mock.patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_write_new_variants_parquet_test(
        self,
        mock_vep: Mock,
        mock_load_gencode_ensembl_to_refseq_id: Mock,
    ) -> None:
        mock_load_gencode_ensembl_to_refseq_id.return_value = hl.dict({})
        mock_vep.side_effect = lambda ht, **_: ht.annotate(vep=MOCK_38_VEP_DATA)
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_SNV_INDEL_VCF,
            project_guids=[
                'R0113_test_project',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
            skip_expect_tdr_metrics=True,
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

    @mock.patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_grch37_write_new_variants_parquet_test(
        self,
        mock_vep: Mock,
    ) -> None:
        mock_vep.side_effect = lambda ht, **_: ht.annotate(vep=MOCK_37_VEP_DATA)
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh37,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_SNV_INDEL_VCF,
            project_guids=[
                'R0113_test_project',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
            skip_expect_tdr_metrics=True,
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

    def test_mito_write_new_variants_parquet_test(
        self,
    ) -> None:
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.MITO,
            sample_type=SampleType.WGS,
            callset_path=TEST_MITO_CALLSET,
            project_guids=[
                'R0116_test_project3',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
            skip_expect_tdr_metrics=True,
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
        'loading_pipeline.lib.tasks.write_new_variants_table.load_gencode_gene_symbol_to_gene_id',
    )
    def test_sv_write_new_variants_parquet_test(
        self,
        mock_load_gencode_gene_symbol_to_gene_id: Mock,
    ) -> None:
        mock_load_gencode_gene_symbol_to_gene_id.return_value = hl.dict({})
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SV,
            sample_type=SampleType.WGS,
            callset_path=TEST_SV_VCF_2,
            project_guids=[
                'R0115_test_project2',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
            skip_expect_tdr_metrics=True,
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
