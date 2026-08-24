import os
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
    existing_variants_parquet_path,
    new_variant_details_parquet_path,
)
from loading_pipeline.lib.tasks.exports.write_new_variant_details_parquet import (
    WriteNewVariantDetailsParquetTask,
)
from loading_pipeline.lib.test.misc import (
    convert_ndarray_to_list,
    copy_project_pedigree_to_mocked_dir,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase
from loading_pipeline.var.test.vep.mock_vep_data import (
    MOCK_37_VEP_DATA,
    MOCK_38_VEP_DATA,
)

TEST_SNV_INDEL_VCF = 'loading_pipeline/var/test/callsets/1kg_30variants.vcf'
TEST_PEDIGREE_3_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_3_remap.tsv'

TEST_RUN_ID = 'manual__2024-04-03'

EXISTING_SNV_INDEL_VARIANT_IDS = [
    '1-871269-A-C',
    '1-874734-C-T',
    '1-878314-G-C',
    '1-878809-C-T',
    '1-879576-C-T',
    '1-881070-G-A',
    '1-881627-G-A',
    '1-881918-G-A',
    '1-883485-C-T',
    '1-883625-A-G',
    '1-883918-G-A',
    '1-887560-A-C',
    '1-887801-A-G',
    '1-888529-G-A',
    '1-888659-T-C',
    '1-889158-G-C',
    '1-889159-A-C',
    '1-889238-G-A',
    '1-894573-G-A',
    '1-896922-C-T',
    '1-897325-G-C',
    '1-898313-C-T',
    '1-898323-T-C',
    '1-898467-C-T',
    '1-899959-G-GC',
    '1-900505-G-C',
    '1-902024-G-A',
    '1-902069-T-C',
    '1-902088-G-A',
    '1-902088-G-ACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACTACT',
]


def _write_existing_variants_parquet_fixture(
    variant_ids: list[str],
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    max_key_: int,
) -> None:
    n = len(variant_ids)
    path = existing_variants_parquet_path(reference_genome, dataset_type, TEST_RUN_ID)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame(
        {
            'variant_id': variant_ids,
            'key_': range(max_key_ - n + 1, max_key_ + 1),
        },
    ).to_parquet(path)


SNV_INDEL_GRCH38_MOCK_VEP_DATA = MOCK_38_VEP_DATA.annotate(
    transcript_consequences=hl.array(
        [
            MOCK_38_VEP_DATA.transcript_consequences[0].annotate(
                am_pathogenicity=hl.missing(hl.tfloat32),
                exon='6/14',
                gene_id='ENSG00000187634',
                hgvsc='ENST00000616016.5:c.1049C>T',
                hgvsp='ENSP00000478421.2:p.Ser350Leu',
                lof=hl.missing(hl.tstr),
                lof_filter=hl.missing(hl.tstr),
                mane_select='NM_001385641.1',
                transcript_id='ENST00000616016',
                fiveutr_annotation=hl.dict(
                    {
                        '1': hl.struct(
                            type='OutOfFrame_oORF',
                            KozakContext='CGCATGC',
                            KozakStrength='Weak',
                            DistanceToCDS='41',
                            CapDistanceToStart=hl.missing(hl.tstr),
                            DistanceToStop=hl.missing(hl.tstr),
                            Evidence=hl.missing(hl.tstr),
                            AltStop=hl.missing(hl.tstr),
                            AltStopDistanceToCDS=hl.missing(hl.tstr),
                            FrameWithCDS=hl.missing(hl.tstr),
                            StartDistanceToCDS=hl.missing(hl.tstr),
                            newSTOPDistanceToCDS=hl.missing(hl.tstr),
                            alt_type=hl.missing(hl.tstr),
                            alt_type_length=hl.missing(hl.tstr),
                            ref_StartDistanceToCDS=hl.missing(hl.tstr),
                            ref_type=hl.missing(hl.tstr),
                            ref_type_length=hl.missing(hl.tstr),
                        ),
                    },
                ),
            ),
        ],
    ),
)

SNV_INDEL_GRCH37_MOCK_VEP_DATA = MOCK_37_VEP_DATA.annotate(
    transcript_consequences=hl.array(
        [
            MOCK_37_VEP_DATA.transcript_consequences[0].annotate(
                amino_acids='E/G',
                codons='gAa/gGa',
                gene_id='ENSG00000186092',
                hgvsc='ENST00000335137.3:c.44A>G',
                hgvsp='ENSP00000334393.3:p.Glu15Gly',
                transcript_id='ENST00000335137',
                lof=hl.missing(hl.tstr),
                lof_filter=hl.missing(hl.tstr),
            ),
        ],
    ),
)


class WriteNewVariantDetailsParquetTest(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()
        _write_existing_variants_parquet_fixture(
            EXISTING_SNV_INDEL_VARIANT_IDS,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            max_key_=-1,
        )
        _write_existing_variants_parquet_fixture(
            EXISTING_SNV_INDEL_VARIANT_IDS,
            ReferenceGenome.GRCh37,
            DatasetType.SNV_INDEL,
            max_key_=1423,
        )

        # Make an incomplete parquet to validate overwrite-ing.
        os.makedirs(
            new_variant_details_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
            exist_ok=True,
        )
        with open(
            os.path.join(
                new_variant_details_parquet_path(
                    ReferenceGenome.GRCh38,
                    DatasetType.SNV_INDEL,
                    TEST_RUN_ID,
                ),
                'incomplete_file.parquet',
            ),
            'w',
        ) as f:
            f.write('')

    @mock.patch(
        'loading_pipeline.lib.tasks.write_new_variants_table.load_gencode_ensembl_to_refseq_id',
    )
    @mock.patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_write_new_variant_details_parquet_test(
        self,
        mock_vep: Mock,
        mock_load_gencode_ensembl_to_refseq_id: Mock,
    ) -> None:
        mock_load_gencode_ensembl_to_refseq_id.return_value = hl.dict(
            {'ENST00000616016': 'NM_001385641.1'},
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
        task = WriteNewVariantDetailsParquetTask(
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
            new_variant_details_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SNV_INDEL,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        self.assertListEqual(
            list(export_json[0].keys()),
            [
                'key',
                'variantId',
                'rsid',
                'CAID',
                'liftedOverChrom',
                'liftedOverPos',
                'sortedMotifFeatureConsequences',
                'sortedRegulatoryFeatureConsequences',
                'transcripts',
            ],
        )
        self.assertEqual(
            export_json[0]['key'],
            0,
        )
        self.assertEqual(
            export_json[0]['transcripts'][0],
            {
                'alphamissense': {'pathogenicity': None},
                'aminoAcids': 'S/L',
                'biotype': 'protein_coding',
                'canonical': 1,
                'codons': 'tCg/tTg',
                'consequenceTerms': ['missense_variant'],
                'exon': {'index': 6, 'total': 14},
                'geneId': 'ENSG00000187634',
                'hgvsc': 'ENST00000616016.5:c.1049C>T',
                'hgvsp': 'ENSP00000478421.2:p.Ser350Leu',
                'intron': None,
                'transcriptId': 'ENST00000616016',
                'transcriptRank': 0,
                'majorConsequence': 'missense_variant',
                'maneSelect': 'NM_001385641.1',
                'manePlusClinical': None,
                'refseqTranscriptId': 'NM_001385641.1',
                'loftee': {'isLofNagnag': None, 'lofFilters': None},
                'spliceregion': {
                    'extended_intronic_splice_region_variant': False,
                },
                'utrannotator': {
                    'existingInframeOorfs': None,
                    'existingOutofframeOorfs': None,
                    'existingUorfs': None,
                    'fiveutrAnnotation': {
                        'AltStop': None,
                        'AltStopDistanceToCDS': None,
                        'CapDistanceToStart': None,
                        'DistanceToCDS': 41,
                        'DistanceToStop': None,
                        'Evidence': None,
                        'FrameWithCDS': None,
                        'KozakContext': 'CGCATGC',
                        'KozakStrength': 'Weak',
                        'StartDistanceToCDS': None,
                        'alt_type': None,
                        'alt_type_length': None,
                        'newSTOPDistanceToCDS': None,
                        'ref_StartDistanceToCDS': None,
                        'ref_type': None,
                        'ref_type_length': None,
                        'type': 'OutOfFrame_oORF',
                    },
                    'fiveutrConsequence': None,
                },
            },
        )
        self.assertEqual(
            list(export_json[0]['transcripts'][0].keys()),
            sorted(export_json[0]['transcripts'][0].keys()),
        )
        self.assertEqual(
            list(
                export_json[0]['transcripts'][0]['utrannotator'][
                    'fiveutrAnnotation'
                ].keys(),
            ),
            sorted(
                export_json[0]['transcripts'][0]['utrannotator'][
                    'fiveutrAnnotation'
                ].keys(),
            ),
        )

    @mock.patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_grch37_write_new_variant_details_parquet_test(
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
        task = WriteNewVariantDetailsParquetTask(
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
            os.path.join(
                new_variant_details_parquet_path(
                    ReferenceGenome.GRCh37,
                    DatasetType.SNV_INDEL,
                    TEST_RUN_ID,
                ),
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        self.assertListEqual(
            list(export_json[0].keys()),
            [
                'key',
                'variantId',
                'rsid',
                'CAID',
                'liftedOverChrom',
                'liftedOverPos',
                'transcripts',
            ],
        )
        self.assertEqual(
            export_json[0]['key'],
            1424,
        )
        self.assertEqual(export_json[0]['CAID'], None)
        self.assertEqual(
            export_json[0]['transcripts'][0],
            {
                'aminoAcids': 'E/G',
                'biotype': 'protein_coding',
                'canonical': 1,
                'codons': 'gAa/gGa',
                'consequenceTerms': ['missense_variant'],
                'geneId': 'ENSG00000186092',
                'hgvsc': 'ENST00000335137.3:c.44A>G',
                'hgvsp': 'ENSP00000334393.3:p.Glu15Gly',
                'loftee': {'isLofNagnag': None, 'lofFilters': None},
                'majorConsequence': 'missense_variant',
                'transcriptId': 'ENST00000335137',
                'transcriptRank': 0,
            },
        )
        self.assertEqual(
            list(export_json[0]['transcripts'][0].keys()),
            sorted(export_json[0]['transcripts'][0].keys()),
        )
