import functools
from unittest.mock import Mock, PropertyMock, patch

import hail as hl
import luigi.worker

from loading_pipeline.lib.annotations.enums import (
    BIOTYPES,
    FIVEUTR_CONSEQUENCES,
    LOF_FILTERS,
    MITOTIP_PATHOGENICITIES,
    MOTIF_CONSEQUENCE_TERMS,
    REGULATORY_BIOTYPES,
    REGULATORY_CONSEQUENCE_TERMS,
    SV_CONSEQUENCE_RANKS,
    SV_TYPE_DETAILS,
    SV_TYPES,
    TRANSCRIPT_CONSEQUENCE_TERMS,
)
from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.misc.io import remap_pedigree_hash
from loading_pipeline.lib.misc.validation import (
    ALL_VALIDATIONS,
    SKIPPABLE_VALIDATIONS,
    validate_expected_contig_frequency,
)
from loading_pipeline.lib.paths import (
    valid_reference_dataset_path,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget
from loading_pipeline.lib.tasks.update_variant_annotations_table_with_new_variants import (
    UpdateVariantAnnotationsTableWithNewVariantsTask,
)
from loading_pipeline.lib.test.misc import copy_project_pedigree_to_mocked_dir
from loading_pipeline.lib.test.mocked_reference_datasets_testcase import (
    MockedReferenceDatasetsTestCase,
)
from loading_pipeline.var.test.vep.mock_vep_data import (
    MOCK_37_VEP_DATA,
    MOCK_38_VEP_DATA,
)

TEST_MITO_MT = 'loading_pipeline/var/test/callsets/mito_1.mt'
TEST_SNV_INDEL_VCF = 'loading_pipeline/var/test/callsets/1kg_30variants.vcf'
TEST_SV_VCF = 'loading_pipeline/var/test/callsets/sv_1.vcf'
TEST_SV_VCF_2 = 'loading_pipeline/var/test/callsets/sv_2.vcf'
TEST_GCNV_BED_FILE = 'loading_pipeline/var/test/callsets/gcnv_1.tsv'
TEST_GCNV_BED_FILE_2 = 'loading_pipeline/var/test/callsets/gcnv_2.tsv'
TEST_PEDIGREE_3_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_3_remap.tsv'
TEST_PEDIGREE_4_REMAP = 'loading_pipeline/var/test/pedigrees/test_pedigree_4_remap.tsv'
TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'
TEST_PEDIGREE_8 = 'loading_pipeline/var/test/pedigrees/test_pedigree_8.tsv'
TEST_PEDIGREE_10 = 'loading_pipeline/var/test/pedigrees/test_pedigree_10.tsv'
TEST_PEDIGREE_11 = 'loading_pipeline/var/test/pedigrees/test_pedigree_11.tsv'

GENE_ID_MAPPING = {
    'OR4F5': 'ENSG00000186092',
    'PLEKHG4B': 'ENSG00000153404',
    'OR4F16': 'ENSG00000186192',
    'OR4F29': 'ENSG00000284733',
    'FBXO28': 'ENSG00000143756',
    'SAMD11': 'ENSG00000187634',
    'C1orf174': 'ENSG00000198912',
    'TAS1R1': 'ENSG00000173662',
    'FAM131C': 'ENSG00000185519',
    'RCC2': 'ENSG00000179051',
    'NBPF3': 'ENSG00000142794',
    'AGBL4': 'ENSG00000186094',
    'KIAA1614': 'ENSG00000135835',
    'MR1': 'ENSG00000153029',
    'STX6': 'ENSG00000135823',
    'XPR1': 'ENSG00000143324',
}

TEST_RUN_ID = 'manual__2024-04-03'


class UpdateVariantAnnotationsTableWithNewVariantsTaskTest(
    MockedReferenceDatasetsTestCase,
):
    def test_missing_pedigree(
        self,
    ) -> None:
        uvatwns_task = UpdateVariantAnnotationsTableWithNewVariantsTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_SNV_INDEL_VCF,
            project_guids=['R0113_test_project'],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker = luigi.worker.Worker()
        worker.add(uvatwns_task)
        worker.run()
        self.assertFalse(uvatwns_task.complete())

    @patch(
        'loading_pipeline.lib.tasks.validate_callset.SKIPPABLE_VALIDATIONS',
        [
            x
            for x in SKIPPABLE_VALIDATIONS
            if x.__name__ != 'validate_expected_contig_frequency'
        ]
        + [
            functools.update_wrapper(
                functools.partial(
                    validate_expected_contig_frequency,
                    min_rows_per_contig=25,
                ),
                validate_expected_contig_frequency,
            ),
        ],
    )
    @patch.object(ReferenceGenome, 'standard_contigs', new_callable=PropertyMock)
    @patch('loading_pipeline.lib.misc.vep.hl.vep')
    @patch(
        'loading_pipeline.lib.tasks.write_new_variants_table.load_gencode_ensembl_to_refseq_id',
    )
    def test_multiple_update_vat(
        self,
        mock_load_gencode_ensembl_to_refseq_id: Mock,
        mock_vep: Mock,
        mock_standard_contigs: Mock,
    ) -> None:
        mock_vep.side_effect = lambda ht, **_: ht.annotate(vep=MOCK_38_VEP_DATA)
        mock_load_gencode_ensembl_to_refseq_id.return_value = hl.dict(
            {'ENST00000327044': 'NM_015658.4'},
        )
        mock_standard_contigs.return_value = {'chr1'}
        # This creates a mock validation table with 1 coding and 1 non-coding variant
        # explicitly chosen from the VCF.
        # NB: This is the one and only place validation is enabled in the task tests!
        coding_and_noncoding_variants_ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=871269,
                        reference_genome='GRCh38',
                    ),
                    'coding': False,
                    'noncoding': True,
                },
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=876499,
                        reference_genome='GRCh38',
                    ),
                    'coding': True,
                    'noncoding': False,
                },
            ],
            hl.tstruct(
                locus=hl.tlocus('GRCh38'),
                coding=hl.tbool,
                noncoding=hl.tbool,
            ),
            key='locus',
            globals=hl.Struct(
                enums=hl.Struct(
                    gnomad_genomes=hl.Struct(),
                ),
            ),
        )
        coding_and_noncoding_variants_ht.write(
            valid_reference_dataset_path(
                ReferenceGenome.GRCh38,
                ReferenceDataset.gnomad_coding_and_noncoding,
            ),
            overwrite=True,
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0113_test_project',
        )
        worker = luigi.worker.Worker()
        uvatwns_task_3 = UpdateVariantAnnotationsTableWithNewVariantsTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_SNV_INDEL_VCF,
            project_guids=['R0113_test_project'],
            validations_to_skip=[],
            run_id=TEST_RUN_ID,
        )
        worker.add(uvatwns_task_3)
        worker.run()
        self.assertTrue(uvatwns_task_3.complete())
        ht = hl.read_table(uvatwns_task_3.output().path)
        self.assertEqual(ht.count(), 30)
        self.assertEqual(
            ht.globals.updates.collect(),
            [
                {
                    hl.Struct(
                        callset=TEST_SNV_INDEL_VCF,
                        project_guid='R0113_test_project',
                        remap_pedigree_hash=hl.eval(
                            remap_pedigree_hash(TEST_PEDIGREE_3_REMAP),
                        ),
                    ),
                },
            ],
        )
        self.assertEqual(
            hl.eval(ht.globals.max_key_),
            29,
        )

        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_4_REMAP,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0114_project4',
        )
        # Ensure that new variants are added correctly to the table.
        uvatwns_task_4 = UpdateVariantAnnotationsTableWithNewVariantsTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_SNV_INDEL_VCF,
            project_guids=['R0114_project4'],
            validations_to_skip=[],
            run_id=TEST_RUN_ID + '-another-run',
        )
        worker.add(uvatwns_task_4)
        worker.run()
        self.assertTrue(uvatwns_task_4.complete())
        ht = hl.read_table(uvatwns_task_4.output().path)
        self.assertCountEqual(
            [
                x
                for x in ht.select(
                    'variant_id',
                    'xpos',
                ).collect()
                if x.locus.position <= 878809  # noqa: PLR2004
            ],
            [
                hl.Struct(
                    locus=hl.Locus(
                        contig='chr1',
                        position=871269,
                        reference_genome='GRCh38',
                    ),
                    alleles=['A', 'C'],
                    variant_id='1-871269-A-C',
                    xpos=1000871269,
                ),
                hl.Struct(
                    locus=hl.Locus(
                        contig='chr1',
                        position=874734,
                        reference_genome='GRCh38',
                    ),
                    alleles=['C', 'T'],
                    variant_id='1-874734-C-T',
                    xpos=1000874734,
                ),
                hl.Struct(
                    locus=hl.Locus(
                        contig='chr1',
                        position=876499,
                        reference_genome='GRCh38',
                    ),
                    alleles=['A', 'G'],
                    variant_id='1-876499-A-G',
                    xpos=1000876499,
                ),
                hl.Struct(
                    locus=hl.Locus(
                        contig='chr1',
                        position=878314,
                        reference_genome='GRCh38',
                    ),
                    alleles=['G', 'C'],
                    variant_id='1-878314-G-C',
                    xpos=1000878314,
                ),
                hl.Struct(
                    locus=hl.Locus(
                        contig='chr1',
                        position=878809,
                        reference_genome='GRCh38',
                    ),
                    alleles=['C', 'T'],
                    variant_id='1-878809-C-T',
                    xpos=1000878809,
                ),
            ],
        )
        self.assertCountEqual(
            ht.filter(
                ht.locus.position <= 878809,  # noqa: PLR2004
            ).sorted_transcript_consequences.consequence_term_ids.collect(),
            [
                [[9], [23, 26], [23, 13, 26]],
                [[9], [23, 26], [23, 13, 26]],
                [[9], [23, 26], [23, 13, 26]],
                [[9], [23, 26], [23, 13, 26]],
                [[9], [23, 26], [23, 13, 26]],
            ],
        )
        self.assertCountEqual(
            ht.globals.collect(),
            [
                hl.Struct(
                    updates={
                        hl.Struct(
                            callset='loading_pipeline/var/test/callsets/1kg_30variants.vcf',
                            project_guid='R0113_test_project',
                            remap_pedigree_hash=hl.eval(
                                remap_pedigree_hash(
                                    TEST_PEDIGREE_3_REMAP,
                                ),
                            ),
                        ),
                        hl.Struct(
                            callset='loading_pipeline/var/test/callsets/1kg_30variants.vcf',
                            project_guid='R0114_project4',
                            remap_pedigree_hash=hl.eval(
                                remap_pedigree_hash(
                                    TEST_PEDIGREE_4_REMAP,
                                ),
                            ),
                        ),
                    },
                    max_key_=29,
                    enums=hl.Struct(
                        sorted_motif_feature_consequences=hl.Struct(
                            consequence_term=MOTIF_CONSEQUENCE_TERMS,
                        ),
                        sorted_regulatory_feature_consequences=hl.Struct(
                            biotype=REGULATORY_BIOTYPES,
                            consequence_term=REGULATORY_CONSEQUENCE_TERMS,
                        ),
                        sorted_transcript_consequences=hl.Struct(
                            biotype=BIOTYPES,
                            consequence_term=TRANSCRIPT_CONSEQUENCE_TERMS,
                            loftee=hl.Struct(
                                lof_filter=LOF_FILTERS,
                            ),
                            utrannotator=hl.Struct(
                                fiveutr_consequence=FIVEUTR_CONSEQUENCES,
                            ),
                        ),
                    ),
                ),
            ],
        )

    @patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_update_vat_grch37(
        self,
        mock_vep: Mock,
    ) -> None:
        mock_vep.side_effect = lambda ht, **_: ht.annotate(vep=MOCK_37_VEP_DATA)
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_3_REMAP,
            ReferenceGenome.GRCh37,
            DatasetType.SNV_INDEL,
            SampleType.WGS,
            'R0113_test_project',
        )
        worker = luigi.worker.Worker()
        uvatwns_task = UpdateVariantAnnotationsTableWithNewVariantsTask(
            reference_genome=ReferenceGenome.GRCh37,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path=TEST_SNV_INDEL_VCF,
            project_guids=['R0113_test_project'],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(uvatwns_task)
        worker.run()
        self.assertTrue(uvatwns_task.complete())
        ht = hl.read_table(uvatwns_task.output().path)
        self.assertEqual(ht.count(), 30)
        self.assertFalse(hasattr(ht, 'rg37_locus'))
        self.assertEqual(
            ht.collect()[0],
            hl.Struct(
                locus=hl.Locus(
                    contig=1,
                    position=871269,
                    reference_genome='GRCh37',
                ),
                alleles=['A', 'C'],
                rsid=None,
                variant_id='1-871269-A-C',
                xpos=1000871269,
                sorted_transcript_consequences=[
                    hl.Struct(
                        amino_acids='S/L',
                        canonical=1,
                        codons='tCg/tTg',
                        gene_id='ENSG00000188976',
                        hgvsc='ENST00000327044.6:c.1667C>T',
                        hgvsp='ENSP00000317992.6:p.Ser556Leu',
                        transcript_id='ENST00000327044',
                        biotype_id=39,
                        consequence_term_ids=[9],
                        is_lof_nagnag=None,
                        lof_filter_ids=[0, 1],
                    ),
                    hl.Struct(
                        amino_acids=None,
                        canonical=None,
                        codons=None,
                        gene_id='ENSG00000188976',
                        hgvsc='ENST00000477976.1:n.3114C>T',
                        hgvsp=None,
                        transcript_id='ENST00000477976',
                        biotype_id=38,
                        consequence_term_ids=[23, 26],
                        is_lof_nagnag=None,
                        lof_filter_ids=None,
                    ),
                    hl.Struct(
                        amino_acids=None,
                        canonical=None,
                        codons=None,
                        gene_id='ENSG00000188976',
                        hgvsc='ENST00000483767.1:n.523C>T',
                        hgvsp=None,
                        transcript_id='ENST00000483767',
                        biotype_id=38,
                        consequence_term_ids=[23, 26],
                        is_lof_nagnag=None,
                        lof_filter_ids=None,
                    ),
                ],
                rg38_locus=hl.Locus(
                    contig='chr1',
                    position=935889,
                    reference_genome='GRCh38',
                ),
                key_=0,
            ),
        )

    def test_mito_update_vat(
        self,
    ) -> None:
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.MITO,
            SampleType.WGS,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        update_variant_annotations_task = (
            UpdateVariantAnnotationsTableWithNewVariantsTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.MITO,
                sample_type=SampleType.WGS,
                callset_path=TEST_MITO_MT,
                project_guids=['R0115_test_project2'],
                validations_to_skip=[ALL_VALIDATIONS],
                run_id=TEST_RUN_ID,
            )
        )
        worker.add(update_variant_annotations_task)
        worker.run()
        self.assertTrue(update_variant_annotations_task.complete())
        ht = hl.read_table(update_variant_annotations_task.output().path)
        self.assertEqual(ht.count(), 5)
        self.assertCountEqual(
            ht.globals.collect(),
            [
                hl.Struct(
                    enums=hl.Struct(
                        sorted_transcript_consequences=hl.Struct(
                            biotype=BIOTYPES,
                            consequence_term=TRANSCRIPT_CONSEQUENCE_TERMS,
                            lof_filter=LOF_FILTERS,
                        ),
                        mitotip=hl.Struct(trna_prediction=MITOTIP_PATHOGENICITIES),
                    ),
                    max_key_=4,
                    updates={
                        hl.Struct(
                            callset='loading_pipeline/var/test/callsets/mito_1.mt',
                            project_guid='R0115_test_project2',
                            remap_pedigree_hash=hl.eval(
                                remap_pedigree_hash(
                                    TEST_PEDIGREE_5,
                                ),
                            ),
                        ),
                    },
                ),
            ],
        )
        self.assertCountEqual(
            ht.collect()[0],
            hl.Struct(
                locus=hl.Locus(
                    contig='chrM',
                    position=3,
                    reference_genome='GRCh38',
                ),
                alleles=['T', 'C'],
                common_low_heteroplasmy=False,
                haplogroup=hl.Struct(is_defining=False),
                mitotip=hl.Struct(trna_prediction_id=None),
                rg37_locus=hl.Locus(
                    contig='MT',
                    position=3,
                    reference_genome='GRCh37',
                ),
                rsid=None,
                sorted_transcript_consequences=None,
                variant_id='M-3-T-C',
                xpos=25000000003,
                key_=0,
            ),
        )

    @patch(
        'loading_pipeline.lib.tasks.write_new_variants_table.load_gencode_gene_symbol_to_gene_id',
    )
    def test_sv_multiple_vcf_update_vat(
        self,
        mock_load_gencode: Mock,
    ) -> None:
        mock_load_gencode.return_value = GENE_ID_MAPPING
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        update_variant_annotations_task = (
            UpdateVariantAnnotationsTableWithNewVariantsTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.SV,
                sample_type=SampleType.WGS,
                callset_path=TEST_SV_VCF,
                project_guids=['R0115_test_project2'],
                validations_to_skip=[ALL_VALIDATIONS],
                run_id=TEST_RUN_ID,
            )
        )
        worker.add(update_variant_annotations_task)
        worker.run()
        self.assertTrue(update_variant_annotations_task.complete())
        self.assertFalse(
            GCSorLocalFolderTarget(
                f'{self.mock_env.REFERENCE_DATASETS_DIR}/v03/GRCh38/SV/lookup.ht',
            ).exists(),
        )
        ht = hl.read_table(update_variant_annotations_task.output().path)
        self.assertEqual(ht.count(), 13)
        self.assertCountEqual(
            ht.globals.collect(),
            [
                hl.Struct(
                    enums=hl.Struct(
                        sv_type=SV_TYPES,
                        sv_type_detail=SV_TYPE_DETAILS,
                        sorted_gene_consequences=hl.Struct(
                            major_consequence=SV_CONSEQUENCE_RANKS,
                        ),
                    ),
                    max_key_=12,
                    updates={
                        hl.Struct(
                            callset=TEST_SV_VCF,
                            project_guid='R0115_test_project2',
                            remap_pedigree_hash=hl.eval(
                                remap_pedigree_hash(
                                    TEST_PEDIGREE_5,
                                ),
                            ),
                        ),
                    },
                ),
            ],
        )
        self.assertCountEqual(
            ht.collect()[:8],
            [
                hl.Struct(
                    variant_id='BND_chr1_6',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=None,
                    end_locus=hl.Locus(
                        contig='chr5',
                        position=20404,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=10367,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=5,
                        position=20404,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000186092', major_consequence_id=12),
                        hl.Struct(gene_id='ENSG00000153404', major_consequence_id=12),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=180928,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_len=-1,
                    sv_type_id=2,
                    sv_type_detail_id=None,
                    xpos=1000180928,
                    key_=0,
                ),
                hl.Struct(
                    variant_id='BND_chr1_9',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=None,
                    end_locus=hl.Locus(
                        contig='chr1',
                        position=789481,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=724861,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=1,
                        position=724861,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000143756', major_consequence_id=12),
                        hl.Struct(gene_id='ENSG00000186192', major_consequence_id=12),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=789481,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_len=223225007,
                    sv_type_id=2,
                    sv_type_detail_id=None,
                    xpos=1000789481,
                    key_=1,
                ),
                hl.Struct(
                    variant_id='CPX_chr1_22',
                    algorithms='manta',
                    bothsides_support=True,
                    cpx_intervals=[
                        hl.Struct(
                            type_id=8,
                            start=hl.Locus('chr1', 6558902, 'GRCh38'),
                            end=hl.Locus('chr1', 6559723, 'GRCh38'),
                        ),
                        hl.Struct(
                            type_id=6,
                            start=hl.Locus('chr1', 6559655, 'GRCh38'),
                            end=hl.Locus('chr1', 6559723, 'GRCh38'),
                        ),
                    ],
                    end_locus=hl.Locus(
                        contig='chr1',
                        position=6559723,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=6618962,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=1,
                        position=6619783,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000173662', major_consequence_id=11),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=6558902,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_len=821,
                    sv_type_id=3,
                    sv_type_detail_id=2,
                    xpos=1006558902,
                    key_=2,
                ),
                hl.Struct(
                    variant_id='CPX_chr1_251',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=[
                        hl.Struct(
                            type_id=5,
                            start=hl.Locus('chr1', 180540234, 'GRCh38'),
                            end=hl.Locus('chr1', 181074767, 'GRCh38'),
                        ),
                        hl.Struct(
                            type_id=8,
                            start=hl.Locus('chr1', 181074767, 'GRCh38'),
                            end=hl.Locus('chr1', 181074938, 'GRCh38'),
                        ),
                    ],
                    end_locus=hl.Locus(
                        contig='chr1',
                        position=181074952,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=180509370,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=1,
                        position=181044088,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000135835', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000153029', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000135823', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000143324', major_consequence_id=0),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=180540234,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_len=534718,
                    sv_type_id=3,
                    sv_type_detail_id=9,
                    xpos=1180540234,
                    key_=3,
                ),
                hl.Struct(
                    variant_id='CPX_chr1_41',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=[
                        hl.Struct(
                            type_id=6,
                            start=hl.Locus('chr1', 16088760, 'GRCh38'),
                            end=hl.Locus('chr1', 16088835, 'GRCh38'),
                        ),
                        hl.Struct(
                            type_id=8,
                            start=hl.Locus('chr1', 16088760, 'GRCh38'),
                            end=hl.Locus('chr1', 16089601, 'GRCh38'),
                        ),
                    ],
                    end_locus=hl.Locus(
                        contig='chr1',
                        position=16089601,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=16415255,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=1,
                        position=16416096,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000185519', major_consequence_id=12),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=16088760,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_len=841,
                    sv_type_id=3,
                    sv_type_detail_id=12,
                    xpos=1016088760,
                    key_=4,
                ),
                hl.Struct(
                    variant_id='CPX_chr1_54',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=[
                        hl.Struct(
                            type_id=6,
                            start=hl.Locus('chr1', 21427498, 'GRCh38'),
                            end=hl.Locus('chr1', 21427959, 'GRCh38'),
                        ),
                        hl.Struct(
                            type_id=8,
                            start=hl.Locus('chr1', 21427498, 'GRCh38'),
                            end=hl.Locus('chr1', 21480073, 'GRCh38'),
                        ),
                        hl.Struct(
                            type_id=5,
                            start=hl.Locus('chr1', 21480073, 'GRCh38'),
                            end=hl.Locus('chr1', 21480419, 'GRCh38'),
                        ),
                    ],
                    end_locus=hl.Locus(
                        contig='chr1',
                        position=21480419,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=21753991,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=1,
                        position=21806912,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000142794', major_consequence_id=0),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=21427498,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_len=52921,
                    sv_type_id=3,
                    sv_type_detail_id=13,
                    xpos=1021427498,
                    key_=5,
                ),
                hl.Struct(
                    variant_id='CPX_chrX_251',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=[
                        hl.Struct(
                            type_id=5,
                            start=hl.Locus(
                                contig='chr1',
                                position=180540234,
                                reference_genome='GRCh38',
                            ),
                            end=hl.Locus(
                                contig='chr1',
                                position=181074767,
                                reference_genome='GRCh38',
                            ),
                        ),
                        hl.Struct(
                            type_id=8,
                            start=hl.Locus(
                                contig='chr1',
                                position=181074767,
                                reference_genome='GRCh38',
                            ),
                            end=hl.Locus(
                                contig='chr1',
                                position=181074938,
                                reference_genome='GRCh38',
                            ),
                        ),
                    ],
                    end_locus=hl.Locus(
                        contig='chrX',
                        position=2781000,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000135835', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000153029', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000135823', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000143324', major_consequence_id=0),
                    ],
                    start_locus=hl.Locus(
                        contig='chrX',
                        position=3,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_type_id=3,
                    sv_type_detail_id=9,
                    sv_len=534718,
                    xpos=23000000003,
                    rg37_locus=None,
                    rg37_locus_end=hl.Locus(
                        contig='X',
                        position=2699041,
                        reference_genome='GRCh37',
                    ),
                    key_=6,
                ),
                hl.Struct(
                    variant_id='CPX_chrX_252',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=[
                        hl.Struct(
                            type_id=5,
                            start=hl.Locus(
                                contig='chr1',
                                position=180540234,
                                reference_genome='GRCh38',
                            ),
                            end=hl.Locus(
                                contig='chr1',
                                position=181074767,
                                reference_genome='GRCh38',
                            ),
                        ),
                        hl.Struct(
                            type_id=8,
                            start=hl.Locus(
                                contig='chr1',
                                position=181074767,
                                reference_genome='GRCh38',
                            ),
                            end=hl.Locus(
                                contig='chr1',
                                position=181074938,
                                reference_genome='GRCh38',
                            ),
                        ),
                    ],
                    end_locus=hl.Locus(
                        contig='chrX',
                        position=2781900,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000135835', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000153029', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000135823', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000143324', major_consequence_id=0),
                    ],
                    start_locus=hl.Locus(
                        contig='chrX',
                        position=2781700,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_type_id=3,
                    sv_type_detail_id=9,
                    sv_len=534718,
                    xpos=23002781700,
                    rg37_locus=hl.Locus(
                        contig='X',
                        position=2699741,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig='X',
                        position=2699941,
                        reference_genome='GRCh37',
                    ),
                    key_=7,
                ),
            ],
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0115_test_project2',
        )
        update_variant_annotations_task = (
            UpdateVariantAnnotationsTableWithNewVariantsTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.SV,
                sample_type=SampleType.WGS,
                callset_path=TEST_SV_VCF_2,
                project_guids=['R0115_test_project2'],
                validations_to_skip=[ALL_VALIDATIONS],
                run_id='second_run_id',
            )
        )
        worker.add(update_variant_annotations_task)
        worker.run()
        self.assertTrue(update_variant_annotations_task.complete())
        ht = hl.read_table(update_variant_annotations_task.output().path)
        self.assertEqual(ht.count(), 14)
        self.assertCountEqual(
            ht.globals.collect(),
            [
                hl.Struct(
                    enums=hl.Struct(
                        sv_type=SV_TYPES,
                        sv_type_detail=SV_TYPE_DETAILS,
                        sorted_gene_consequences=hl.Struct(
                            major_consequence=SV_CONSEQUENCE_RANKS,
                        ),
                    ),
                    max_key_=13,
                    updates={
                        hl.Struct(
                            callset=TEST_SV_VCF,
                            project_guid='R0115_test_project2',
                            remap_pedigree_hash=hl.eval(
                                remap_pedigree_hash(
                                    TEST_PEDIGREE_5,
                                ),
                            ),
                        ),
                        hl.Struct(
                            callset=TEST_SV_VCF_2,
                            project_guid='R0115_test_project2',
                            remap_pedigree_hash=hl.eval(
                                remap_pedigree_hash(
                                    TEST_PEDIGREE_5,
                                ),
                            ),
                        ),
                    },
                ),
            ],
        )
        self.assertCountEqual(
            ht.take(1),
            [
                hl.Struct(
                    variant_id='BND_chr1_6',
                    algorithms='manta',
                    bothsides_support=False,
                    cpx_intervals=None,
                    end_locus=hl.Locus(
                        contig='chr5',
                        position=20404,
                        reference_genome='GRCh38',
                    ),
                    gnomad_svs=None,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=10367,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=5,
                        position=20404,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000186092', major_consequence_id=12),
                        hl.Struct(gene_id='ENSG00000153404', major_consequence_id=12),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=180928,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=None),
                    sv_len=-1,
                    sv_type_id=2,
                    sv_type_detail_id=None,
                    xpos=1000180928,
                    key_=0,
                ),
            ],
        )

    @patch(
        'loading_pipeline.lib.tasks.write_new_variants_table.load_gencode_gene_symbol_to_gene_id',
    )
    def test_sv_multiple_project_single_vcf(
        self,
        mock_load_gencode: Mock,
    ) -> None:
        mock_load_gencode.return_value = GENE_ID_MAPPING
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_10,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0116_test_project3',
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_11,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0117_test_project4',
        )
        worker = luigi.worker.Worker()
        update_variant_annotations_task = (
            UpdateVariantAnnotationsTableWithNewVariantsTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.SV,
                sample_type=SampleType.WGS,
                callset_path=TEST_SV_VCF_2,
                project_guids=['R0116_test_project3', 'R0117_test_project4'],
                validations_to_skip=[ALL_VALIDATIONS],
                run_id='run_id',
            )
        )
        worker.add(update_variant_annotations_task)
        worker.run()
        self.assertTrue(update_variant_annotations_task.complete())
        ht = hl.read_table(update_variant_annotations_task.output().path)
        self.assertEqual(ht.count(), 2)
        self.assertEqual(
            len(ht.globals.updates.collect()[0]),
            2,
        )

    def test_gcnv_update_vat_multiple(
        self,
    ) -> None:
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.GCNV,
            SampleType.WES,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        update_variant_annotations_task = (
            UpdateVariantAnnotationsTableWithNewVariantsTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.GCNV,
                sample_type=SampleType.WES,
                callset_path=TEST_GCNV_BED_FILE,
                project_guids=['R0115_test_project2'],
                validations_to_skip=[ALL_VALIDATIONS],
                run_id=TEST_RUN_ID,
            )
        )
        worker.add(update_variant_annotations_task)
        worker.run()
        self.assertTrue(update_variant_annotations_task.complete())
        self.assertFalse(
            GCSorLocalFolderTarget(
                f'{self.mock_env.REFERENCE_DATASETS_DIR}/v03/GRCh38/GCNV/lookup.ht',
            ).exists(),
        )
        ht = hl.read_table(update_variant_annotations_task.output().path)
        self.assertEqual(ht.count(), 2)
        self.assertCountEqual(
            ht.globals.collect(),
            [
                hl.Struct(
                    enums=hl.Struct(
                        sv_type=SV_TYPES,
                        sorted_gene_consequences=hl.Struct(
                            major_consequence=SV_CONSEQUENCE_RANKS,
                        ),
                    ),
                    max_key_=1,
                    updates={
                        hl.Struct(
                            callset=TEST_GCNV_BED_FILE,
                            project_guid='R0115_test_project2',
                            remap_pedigree_hash=hl.eval(
                                remap_pedigree_hash(
                                    TEST_PEDIGREE_5,
                                ),
                            ),
                        ),
                    },
                ),
            ],
        )
        self.assertCountEqual(
            ht.collect(),
            [
                hl.Struct(
                    variant_id='suffix_16456_DEL',
                    end_locus=hl.Locus(
                        contig='chr1',
                        position=100023213,
                        reference_genome='GRCh38',
                    ),
                    gt_stats=hl.Struct(
                        AF=hl.eval(hl.float32(4.401408e-05)),
                        AC=1,
                        AN=22720,
                        Hom=None,
                        Het=None,
                    ),
                    num_exon=3,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=100472493,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=1,
                        position=100488769,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000117620', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG00000283761', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG22222222222', major_consequence_id=None),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=100006937,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=hl.eval(hl.float32(0.583))),
                    sv_type_id=5,
                    xpos=1100006937,
                    key_=0,
                ),
                hl.Struct(
                    variant_id='suffix_16457_DEL',
                    end_locus=hl.Locus(
                        contig='chr1',
                        position=100023212,
                        reference_genome='GRCh38',
                    ),
                    gt_stats=hl.Struct(
                        AF=8.802817319519818e-05,
                        AC=2,
                        AN=22719,
                        Hom=None,
                        Het=None,
                    ),
                    num_exon=2,
                    rg37_locus=hl.Locus(
                        contig=1,
                        position=100483142,
                        reference_genome='GRCh37',
                    ),
                    rg37_locus_end=hl.Locus(
                        contig=1,
                        position=100488768,
                        reference_genome='GRCh37',
                    ),
                    sorted_gene_consequences=[
                        hl.Struct(gene_id='ENSG00000283761', major_consequence_id=0),
                        hl.Struct(gene_id='ENSG22222222222', major_consequence_id=None),
                    ],
                    start_locus=hl.Locus(
                        contig='chr1',
                        position=100017586,
                        reference_genome='GRCh38',
                    ),
                    strvctvre=hl.Struct(score=0.5070000290870667),
                    sv_type_id=5,
                    xpos=1100017586,
                    key_=1,
                ),
            ],
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_8,
            ReferenceGenome.GRCh38,
            DatasetType.GCNV,
            SampleType.WES,
            'R0115_test_project2',
        )
        update_variant_annotations_task = (
            UpdateVariantAnnotationsTableWithNewVariantsTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.GCNV,
                sample_type=SampleType.WES,
                callset_path=TEST_GCNV_BED_FILE_2,
                project_guids=['R0115_test_project2'],
                validations_to_skip=[ALL_VALIDATIONS],
                run_id='second_run_id',
            )
        )
        worker.add(update_variant_annotations_task)
        worker.run()
        ht = hl.read_table(update_variant_annotations_task.output().path)
        self.assertEqual(ht.count(), 3)
        self.assertCountEqual(
            ht.select('gt_stats').collect(),
            [
                hl.Struct(
                    # Existing variant, gt_stats are preserved
                    variant_id='suffix_16456_DEL',
                    gt_stats=hl.Struct(
                        AF=hl.eval(hl.float32(4.401408e-05)),
                        AC=1,
                        AN=22720,
                        Hom=None,
                        Het=None,
                    ),
                ),
                hl.Struct(
                    # Exiting variant, gt_stats are updated
                    variant_id='suffix_16457_DEL',
                    gt_stats=hl.Struct(
                        AF=8.111110946629196e-05,
                        AC=3,
                        AN=36986,
                        Hom=None,
                        Het=None,
                    ),
                ),
                hl.Struct(
                    # New variant.
                    variant_id='suffix_99999_DEL',
                    gt_stats=hl.Struct(
                        AF=8.802817319519818e-05,
                        AC=2,
                        AN=22719,
                        Hom=None,
                        Het=None,
                    ),
                ),
            ],
        )
