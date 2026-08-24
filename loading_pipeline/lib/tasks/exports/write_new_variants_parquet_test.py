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
    remapped_and_subsetted_callset_path,
)
from loading_pipeline.lib.tasks.exports.write_new_variants_parquet import (
    WriteNewVariantsParquetTask,
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
TEST_SV_VCF = 'loading_pipeline/var/test/callsets/sv_1.vcf'
TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'

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

SNV_INDEL_GRCH38_MOCK_VEP_DATA = MOCK_38_VEP_DATA.annotate(
    motif_feature_consequences=hl.array(
        [
            hl.struct(
                consequence_terms=hl.array(['TF_binding_site_variant']),
                motif_feature_id='motif_1',
            ),
        ],
    ),
    regulatory_feature_consequences=hl.array(
        [MOCK_38_VEP_DATA.regulatory_feature_consequences[0]],
    ),
    transcript_consequences=hl.array(
        [
            MOCK_38_VEP_DATA.transcript_consequences[0].annotate(
                am_pathogenicity=hl.missing(hl.tfloat32),
                gene_id='ENSG00000187634',
            ),
        ],
    ),
)

SNV_INDEL_GRCH37_MOCK_VEP_DATA = MOCK_37_VEP_DATA.annotate(
    transcript_consequences=hl.array(
        [
            MOCK_37_VEP_DATA.transcript_consequences[0].annotate(
                gene_id='ENSG00000186092',
            ),
        ],
    ),
)


class WriteNewVariantsParquetTest(MockedReferenceDatasetsTestCase):
    def setUp(self) -> None:
        super().setUp()
        ht = hl.read_table(TEST_SNV_INDEL_ANNOTATIONS)
        ht = ht.filter(ht.variant_id != '1-876499-A-G')
        ht = ht.annotate_globals(max_key_=-1)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
            ),
        )
        ht = hl.read_table(TEST_GRCH37_SNV_INDEL_ANNOTATIONS)
        ht = ht.filter(ht.variant_id != '1-69134-A-G')
        ht = ht.annotate_globals(max_key_=1423)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh37,
                DatasetType.SNV_INDEL,
            ),
        )
        ht = hl.read_table(TEST_MITO_ANNOTATIONS)
        ht = ht.filter(ht.variant_id != 'M-8-G-T')
        ht = ht.join(
            hl.Table.parallelize(
                [
                    {'locus': hl.Locus('chrM', 3, 'GRCh38'), 'alleles': ['T', 'C']},
                    {'locus': hl.Locus('chrM', 12, 'GRCh38'), 'alleles': ['T', 'C']},
                ],
                hl.tstruct(locus=hl.tlocus('GRCh38'), alleles=hl.tarray(hl.tstr)),
                key=['locus', 'alleles'],
            ),
            how='outer',
        )
        ht = ht.annotate_globals(max_key_=997)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.MITO,
            ),
        )
        ht = hl.read_table(TEST_SV_ANNOTATIONS)
        ht = ht.filter(ht.variant_id != 'CPX_chr1_22')
        ht = ht.join(
            hl.Table.parallelize(
                [
                    {'variant_id': variant_id}
                    for variant_id in [
                        'DUP_chr1_5',
                        'DEL_chr1_12',
                        'BND_chr1_9',
                        'INS_chr1_65',
                        'CPX_chr1_41',
                        'INS_chr1_268',
                        'CPX_chr1_54',
                        'INS_chr1_688',
                        'CPX_chr1_251',
                        'CPX_chrX_251',
                        'CPX_chrX_252',
                    ]
                ],
                hl.tstruct(variant_id=hl.tstr),
                key='variant_id',
            ),
            how='outer',
        )
        ht = ht.annotate_globals(max_key_=726)
        ht.write(
            variant_annotations_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.SV,
            ),
        )
        ht = hl.read_table(TEST_GCNV_ANNOTATIONS)
        ht.write(
            new_variants_table_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                TEST_RUN_ID,
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
        mock_load_gencode_ensembl_to_refseq_id.return_value = hl.dict(
            {'ENST00000327044': 'NM_015658.4'},
        )
        mock_vep.side_effect = lambda ht, **_: ht.annotate(
            vep=SNV_INDEL_GRCH38_MOCK_VEP_DATA,
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0113_test_project',
        )
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
        mock_vep.side_effect = lambda ht, **_: ht.annotate(
            vep=SNV_INDEL_GRCH37_MOCK_VEP_DATA,
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh37,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0113_test_project',
        )
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
        copy_project_pedigree_to_mocked_dir(
            TEST_MITO_EXPORT_PEDIGREE,
            ReferenceGenome.GRCh38,
            DatasetType.MITO,
            SampleType.WGS,
            'R0116_test_project3',
        )
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
        self.assertEqual(
            export_json,
            [
                {
                    'key': 998,
                    'variantId': 'M-8-G-T',
                    'rsid': 'rs1603218446',
                    'liftedOverPos': 8,
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
        mock_load_gencode_gene_symbol_to_gene_id.return_value = hl.dict(
            {'TAS1R1': 'ENSG00000173662'},
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        task = WriteNewVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SV,
            sample_type=SampleType.WGS,
            callset_path=TEST_SV_VCF,
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
                    'xpos': 1006558902,
                    'chrom': '1',
                    'pos': 6558902,
                    'end': 6559723,
                    'rg37LocusEnd': {'contig': '1', 'position': 6619783},
                    'variantId': 'CPX_chr1_22',
                    'liftedOverChrom': '1',
                    'liftedOverPos': 6618962,
                    'algorithms': 'manta',
                    'bothsidesSupport': True,
                    'cpxIntervals': [
                        {'chrom': '1', 'start': 6558902, 'end': 6559723, 'type': 'INV'},
                        {'chrom': '1', 'start': 6559655, 'end': 6559723, 'type': 'DUP'},
                    ],
                    'endChrom': None,
                    'svSourceDetail': None,
                    'svType': 'CPX',
                    'svTypeDetail': 'INVdup',
                    'predictions': {'strvctvre': None},
                    'populations': {'gnomad_svs': None},
                    'sortedGeneConsequences': [
                        {'geneId': 'ENSG00000173662', 'majorConsequence': 'INTRONIC'},
                    ],
                },
            ],
        )

    @mock.patch(
        'loading_pipeline.lib.tasks.exports.write_new_variants_parquet.WriteNewVariantsTableTask',
    )
    def test_gcnv_write_new_variants_parquet_test(
        self,
        write_new_variants_table_task: Mock,
    ) -> None:
        write_new_variants_table_task.return_value = MockCompleteTask()
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
