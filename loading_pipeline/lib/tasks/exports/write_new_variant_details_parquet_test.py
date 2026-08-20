import os
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
    new_variant_details_parquet_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.exports.write_new_variant_details_parquet import (
    WriteNewVariantDetailsParquetTask,
)
from loading_pipeline.lib.tasks.write_remapped_and_subsetted_callset import (
    WriteRemappedAndSubsettedCallsetTask,
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


def _write_prior_annotations_table(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    sample_type: SampleType,
    pedigree_path: str,
    callset_path: str,
    project_guid: str,
    exclude_variant_id: str,
    max_key_: int,
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
    variant_id_expr = get_expr_for_variant_id(callset_ht)
    prior_ht = callset_ht.filter(variant_id_expr != exclude_variant_id)
    prior_ht = prior_ht.select()
    prior_ht = prior_ht.add_index(name='key_')
    prior_ht = prior_ht.annotate_globals(max_key_=max_key_)
    prior_ht.write(variant_annotations_table_path(reference_genome, dataset_type))


class WriteNewVariantDetailsParquetTest(MockedDatarootTestCase):
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
        mock_load_gencode_ensembl_to_refseq_id.return_value = hl.dict({})
        mock_vep.side_effect = lambda ht, **_: ht.annotate(vep=MOCK_38_VEP_DATA)
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
        mock_vep.side_effect = lambda ht, **_: ht.annotate(vep=MOCK_37_VEP_DATA)
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
