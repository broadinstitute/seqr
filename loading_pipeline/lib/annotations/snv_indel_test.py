import unittest
from unittest.mock import Mock, patch

import hail as hl

from loading_pipeline.lib.annotations import shared, snv_indel
from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.misc.vep import run_vep
from loading_pipeline.var.test.vep.mock_vep_data import (
    MOCK_37_VEP_DATA,
    MOCK_38_VEP_DATA,
)


class SNVTest(unittest.TestCase):
    @patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_sorted_transcript_consequences_37(
        self,
        mock_vep: Mock,
    ) -> None:
        ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='1',
                        position=871269,
                        reference_genome=ReferenceGenome.GRCh37.value,
                    ),
                    'alleles': ['A', 'C'],
                },
            ],
            hl.tstruct(
                locus=hl.tlocus(ReferenceGenome.GRCh37.value),
                alleles=hl.tarray(hl.tstr),
            ),
            key=['locus', 'alleles'],
        )
        mock_vep.return_value = ht.annotate(vep=MOCK_37_VEP_DATA)
        ht = run_vep(
            ht,
            DatasetType.SNV_INDEL,
            ReferenceGenome.GRCh37,
        )
        ht = ht.select(
            sorted_transcript_consequences=shared.sorted_transcript_consequences(
                ht,
            ),
        )
        self.assertCountEqual(
            ht.sorted_transcript_consequences.collect(),
            [
                [
                    hl.Struct(
                        amino_acids='S/L',
                        canonical=1,
                        codons='tCg/tTg',
                        gene_id='ENSG00000188976',
                        hgvsc='ENST00000327044.6:c.1667C>T',
                        hgvsp='ENSP00000317992.6:p.Ser556Leu',
                        transcript_id='ENST00000327044',
                        biotype='protein_coding',
                        consequence_terms=['missense_variant'],
                        is_lof_nagnag=None,
                        lof_filters=['END_TRUNC', 'INCOMPLETE_CDS'],
                    ),
                    hl.Struct(
                        amino_acids=None,
                        canonical=None,
                        codons=None,
                        gene_id='ENSG00000188976',
                        hgvsc='ENST00000477976.1:n.3114C>T',
                        hgvsp=None,
                        transcript_id='ENST00000477976',
                        biotype='lncRNA',
                        consequence_terms=[
                            'non_coding_transcript_exon_variant',
                            'non_coding_transcript_variant',
                        ],
                        is_lof_nagnag=None,
                        lof_filters=None,
                    ),
                    hl.Struct(
                        amino_acids=None,
                        canonical=None,
                        codons=None,
                        gene_id='ENSG00000188976',
                        hgvsc='ENST00000483767.1:n.523C>T',
                        hgvsp=None,
                        transcript_id='ENST00000483767',
                        biotype='retained_intron',
                        consequence_terms=[
                            'non_coding_transcript_exon_variant',
                            'non_coding_transcript_variant',
                        ],
                        is_lof_nagnag=None,
                        lof_filters=None,
                    ),
                ],
            ],
        )

    @patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_sorted_transcript_consequences_38(
        self,
        mock_vep: Mock,
    ) -> None:
        ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=871269,
                        reference_genome=ReferenceGenome.GRCh38.value,
                    ),
                    'alleles': ['A', 'C'],
                },
            ],
            hl.tstruct(
                locus=hl.tlocus(ReferenceGenome.GRCh38.value),
                alleles=hl.tarray(hl.tstr),
            ),
            key=['locus', 'alleles'],
        )
        mock_vep.return_value = ht.annotate(vep=MOCK_38_VEP_DATA)
        ht = run_vep(
            ht,
            DatasetType.SNV_INDEL,
            ReferenceGenome.GRCh38,
        )
        ht = ht.select(
            sorted_transcript_consequences=snv_indel.sorted_transcript_consequences(
                ht,
                hl.dict(
                    {'ENST00000327044': 'NM_015658.4', 'ENST00000477976': 'refseq1'},
                ),
            ),
        )
        self.assertCountEqual(
            ht.sorted_transcript_consequences.collect()[0],
            [
                hl.Struct(
                    amino_acids='S/L',
                    canonical=1,
                    codons='tCg/tTg',
                    gene_id='ENSG00000188976',
                    hgvsc='ENST00000327044.6:c.1667C>T',
                    hgvsp='ENSP00000317992.6:p.Ser556Leu',
                    transcript_id='ENST00000327044',
                    refseq_transcript_id='NM_015658.4',
                    mane_select='NM_015658.4',
                    mane_plus_clinical=None,
                    biotype='protein_coding',
                    consequence_terms=['missense_variant'],
                    exon=hl.Struct(index=15, total=19),
                    intron=None,
                    alphamissense=hl.Struct(pathogenicity=0.10000000149011612),
                    loftee=hl.Struct(
                        is_lof_nagnag=None,
                        lof_filters=['END_TRUNC', 'INCOMPLETE_CDS'],
                    ),
                    spliceregion=hl.Struct(
                        extended_intronic_splice_region_variant=False,
                    ),
                    utrannotator=hl.Struct(
                        existing_inframe_oorfs=None,
                        existing_outofframe_oorfs=None,
                        existing_uorfs=None,
                        fiveutr_consequence=None,
                        fiveutr_annotation=None,
                    ),
                ),
                hl.Struct(
                    amino_acids=None,
                    canonical=None,
                    codons=None,
                    gene_id='ENSG00000188976',
                    hgvsc='ENST00000477976.1:n.3114C>T',
                    hgvsp=None,
                    transcript_id='ENST00000477976',
                    refseq_transcript_id='refseq1',
                    mane_select=None,
                    mane_plus_clinical=None,
                    biotype='retained_intron',
                    consequence_terms=[
                        'non_coding_transcript_exon_variant',
                        'non_coding_transcript_variant',
                    ],
                    exon=hl.Struct(index=13, total=17),
                    intron=None,
                    alphamissense=hl.Struct(pathogenicity=0.9700000286102295),
                    loftee=hl.Struct(
                        is_lof_nagnag=None,
                        lof_filters=None,
                    ),
                    spliceregion=hl.Struct(
                        extended_intronic_splice_region_variant=False,
                    ),
                    utrannotator=hl.Struct(
                        existing_inframe_oorfs=None,
                        existing_outofframe_oorfs=None,
                        existing_uorfs=None,
                        fiveutr_consequence=None,
                        fiveutr_annotation=None,
                    ),
                ),
                hl.Struct(
                    amino_acids=None,
                    canonical=None,
                    codons=None,
                    gene_id='ENSG00000188976',
                    hgvsc='ENST00000483767.1:n.523C>T',
                    hgvsp=None,
                    transcript_id='ENST00000483767',
                    refseq_transcript_id=None,
                    mane_select=None,
                    mane_plus_clinical=None,
                    biotype='retained_intron',
                    consequence_terms=[
                        'non_coding_transcript_exon_variant',
                        'splice_donor_region_variant',
                        'non_coding_transcript_variant',
                    ],
                    exon=hl.Struct(index=1, total=5),
                    intron=None,
                    alphamissense=hl.Struct(pathogenicity=None),
                    loftee=hl.Struct(
                        is_lof_nagnag=None,
                        lof_filters=None,
                    ),
                    spliceregion=hl.Struct(
                        extended_intronic_splice_region_variant=True,
                    ),
                    utrannotator=hl.Struct(
                        existing_inframe_oorfs=0,
                        existing_outofframe_oorfs=1,
                        existing_uorfs=0,
                        fiveutr_consequence='5_prime_UTR_premature_start_codon_loss_variant',
                        fiveutr_annotation=hl.Struct(
                            type='OutOfFrame_oORF',
                            KozakContext='TTTATGC',
                            KozakStrength='Weak',
                            DistanceToCDS=40,
                            CapDistanceToStart=20,
                            DistanceToStop=75,
                            Evidence=False,
                            AltStop=None,
                            AltStopDistanceToCDS=None,
                            FrameWithCDS=None,
                            StartDistanceToCDS=None,
                            newSTOPDistanceToCDS=None,
                            alt_type=None,
                            alt_type_length=None,
                            ref_StartDistanceToCDS=None,
                            ref_type=None,
                            ref_type_length=None,
                        ),
                    ),
                ),
            ],
        )

    @patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_sorted_other_feature_consequences(
        self,
        mock_vep: Mock,
    ) -> None:
        ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=871269,
                        reference_genome=ReferenceGenome.GRCh38.value,
                    ),
                    'alleles': ['A', 'C'],
                },
            ],
            hl.tstruct(
                locus=hl.tlocus(ReferenceGenome.GRCh38.value),
                alleles=hl.tarray(hl.tstr),
            ),
            key=['locus', 'alleles'],
        )
        mock_vep.return_value = ht.annotate(vep=MOCK_38_VEP_DATA)
        ht = run_vep(
            ht,
            DatasetType.SNV_INDEL,
            ReferenceGenome.GRCh38,
        )
        ht = ht.select(
            sorted_motif_feature_consequences=snv_indel.sorted_motif_feature_consequences(
                ht,
            ),
            sorted_regulatory_feature_consequences=snv_indel.sorted_regulatory_feature_consequences(
                ht,
            ),
        )
        self.assertCountEqual(
            ht.sorted_motif_feature_consequences.collect(),
            [None],
        )
        self.assertCountEqual(
            ht.sorted_regulatory_feature_consequences.collect()[0],
            [
                hl.Struct(
                    biotype='enhancer',
                    consequence_terms=['regulatory_region_ablation'],
                    regulatory_feature_id='regulatory_2',
                ),
                hl.Struct(
                    biotype='enhancer',
                    consequence_terms=['regulatory_region_variant'],
                    regulatory_feature_id='regulatory_1',
                ),
            ],
        )
