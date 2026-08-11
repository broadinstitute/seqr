import unittest

import hail as hl

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
)
from loading_pipeline.lib.tasks.exports.misc import (
    camelcase_array_structexpression_fields,
    sorted_hl_struct,
    unmap_formatting_annotation_enums,
)

TEST_SNV_INDEL_ANNOTATIONS = (
    'loading_pipeline/var/test/exports/GRCh38/SNV_INDEL/annotations.ht'
)
TEST_GRCH37_SNV_INDEL_ANNOTATIONS = (
    'loading_pipeline/var/test/exports/GRCh37/SNV_INDEL/annotations.ht'
)


class MiscTest(unittest.TestCase):
    def test_unmap_formatting_annotation_enums(self) -> None:
        ht = hl.read_table(TEST_SNV_INDEL_ANNOTATIONS)
        ht = unmap_formatting_annotation_enums(
            ht,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
        )
        self.assertCountEqual(
            list(ht.globals.enums.collect()[0].keys()),
            [
                'clinvar',
                'hgmd',
                'screen',
                'dbnsfp',
                'gnomad_exomes',
                'gnomad_non_coding_constraint',
                'splice_ai',
                'exac',
                'topmed',
                'gnomad_genomes',
                'eigen',
            ],
        )
        ht = ht.annotate(
            sorted_transcript_consequences=[ht.sorted_transcript_consequences[0]],
        )
        self.assertEqual(
            ht.collect()[0],
            hl.Struct(
                key_=0,
                locus=hl.Locus(
                    contig='chr1',
                    position=876499,
                    reference_genome='GRCh38',
                ),
                alleles=['A', 'G'],
                clinvar=hl.Struct(
                    alleleId=929885,
                    conflictingPathogenicities=None,
                    goldStars=1,
                    submitters=['Labcorp Genetics (formerly Invitae), Labcorp'],
                    conditions=['not provided'],
                    assertion_ids=[],
                    pathogenicity_id=12,
                ),
                rg37_locus=hl.Locus(
                    contig=1,
                    position=874501,
                    reference_genome='GRCh37',
                ),
                rsid=None,
                sorted_transcript_consequences=[
                    hl.Struct(
                        amino_acids='S/L',
                        canonical=1,
                        codons='tCg/tTg',
                        gene_id='ENSG00000187634',
                        hgvsc='ENST00000616016.5:c.1049C>T',
                        hgvsp='ENSP00000478421.2:p.Ser350Leu',
                        transcript_id='ENST00000616016',
                        mane_select='NM_001385641.1',
                        mane_plus_clinical=None,
                        exon=hl.Struct(index=6, total=14),
                        intron=None,
                        refseq_transcript_id='NM_001385641.1',
                        alphamissense=hl.Struct(pathogenicity=None),
                        loftee=hl.Struct(is_lof_nagnag=None, lof_filters=None),
                        spliceregion=hl.Struct(
                            extended_intronic_splice_region_variant=False,
                        ),
                        utrannotator=hl.Struct(
                            existing_inframe_oorfs=None,
                            existing_outofframe_oorfs=None,
                            existing_uorfs=None,
                            fiveutr_annotation=hl.Struct(
                                type='OutOfFrame_oORF',
                                KozakContext='CGCATGC',
                                KozakStrength='Weak',
                                DistanceToCDS=41,
                                CapDistanceToStart=None,
                                DistanceToStop=None,
                                Evidence=None,
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
                            fiveutr_consequence=None,
                        ),
                        biotype='protein_coding',
                        consequence_terms=['missense_variant'],
                    ),
                ],
                variant_id='1-876499-A-G',
                xpos=1000876499,
                gt_stats=hl.Struct(AC=47, AN=81784, AF=0.0005746845272369683, hom=1),
                CAID='CA502654',
                check_ref=False,
                sorted_regulatory_feature_consequences=[
                    hl.Struct(
                        regulatory_feature_id='ENSR00000344437',
                        biotype='CTCF_binding_site',
                        consequence_terms=['regulatory_region_variant'],
                    ),
                ],
                sorted_motif_feature_consequences=[
                    hl.Struct(
                        motif_feature_id='ENSM00493959715',
                        consequence_terms=['TF_binding_site_variant'],
                    ),
                ],
                gnomad_non_coding_constraint=hl.Struct(z_score=None),
                hgmd=hl.Struct(accession='abcdefg', class_id=3),
                gnomad_exomes=hl.Struct(
                    AF=0.0006690866430290043,
                    AN=1440770,
                    AC=964,
                    Hom=0,
                    AF_POPMAX_OR_GLOBAL=0.0008023773552849889,
                    FAF_AF=0.000633420015219599,
                    Hemi=0,
                ),
                gnomad_genomes=hl.Struct(
                    AF=0.0002759889466688037,
                    AN=152180,
                    AC=42,
                    Hom=0,
                    AF_POPMAX_OR_GLOBAL=0.10000000149011612,
                    FAF_AF=0.0002092500071739778,
                    Hemi=0,
                ),
                screen=hl.Struct(region_type_ids=[]),
                dbnsfp=hl.Struct(
                    PrimateAI_score=0.5918066501617432,
                    fathmm_MKL_coding_score=0.7174800038337708,
                    CADD_phred=23.5,
                    SIFT_score=0.0010000000474974513,
                    REVEL_score=0.3109999895095825,
                    Polyphen2_HVAR_score=0.164000004529953,
                    VEST4_score=0.39500001072883606,
                    MPC_score=0.01291007362306118,
                    MutPred_score=None,
                    MutationTaster_pred_id=0,
                ),
                topmed=hl.Struct(
                    AC=41,
                    AF=0.00032651599030941725,
                    AN=125568,
                    Hom=0,
                    Het=41,
                ),
                exac=hl.Struct(
                    AF_POPMAX=0.0007150234305299819,
                    AF=0.00019039999460801482,
                    AC_Adj=20,
                    AC_Het=20,
                    AC_Hom=0,
                    AC_Hemi=None,
                    AN_Adj=47974,
                ),
                splice_ai=hl.Struct(delta_score=0.0, splice_consequence_id=4),
                eigen=hl.Struct(Eigen_phred=2.628000020980835),
            ),
        )
        ht = hl.read_table(TEST_GRCH37_SNV_INDEL_ANNOTATIONS)
        ht = unmap_formatting_annotation_enums(
            ht,
            ReferenceGenome.GRCh37,
            DatasetType.SNV_INDEL,
        )
        self.assertCountEqual(
            list(ht.globals.enums.collect()[0].keys()),
            [
                'clinvar',
                'hgmd',
                'dbnsfp',
                'gnomad_exomes',
                'splice_ai',
                'exac',
                'topmed',
                'gnomad_genomes',
                'eigen',
            ],
        )
        ht = ht.annotate(
            sorted_transcript_consequences=[ht.sorted_transcript_consequences[0]],
        )
        self.assertEqual(
            ht.collect()[0],
            hl.Struct(
                locus=hl.Locus(contig=1, position=69134, reference_genome='GRCh37'),
                alleles=['A', 'G'],
                clinvar=hl.Struct(
                    alleleId=2193183,
                    conflictingPathogenicities=None,
                    goldStars=1,
                    submitters=['Ambry Genetics'],
                    conditions=['not specified'],
                    assertion_ids=[],
                    pathogenicity_id=14,
                ),
                rsid=None,
                sorted_transcript_consequences=[
                    hl.Struct(
                        amino_acids='E/G',
                        canonical=1,
                        codons='gAa/gGa',
                        gene_id='ENSG00000186092',
                        hgvsc='ENST00000335137.3:c.44A>G',
                        hgvsp='ENSP00000334393.3:p.Glu15Gly',
                        transcript_id='ENST00000335137',
                        is_lof_nagnag=None,
                        biotype='protein_coding',
                        consequence_terms=['missense_variant'],
                        lof_filters=None,
                    ),
                ],
                variant_id='1-69134-A-G',
                xpos=1000069134,
                gt_stats=hl.Struct(AC=25, AN=1246, AF=0.020064204931259155, hom=10),
                CAID='CA502008',
                rg38_locus=hl.Locus(
                    contig='chr1',
                    position=69134,
                    reference_genome='GRCh38',
                ),
                hgmd=None,
                gnomad_exomes=hl.Struct(
                    AF=0.026665963232517242,
                    AN=18938,
                    AC=505,
                    Hom=127,
                    AF_POPMAX_OR_GLOBAL=0.08191808313131332,
                    FAF_AF=0.02474386990070343,
                    Hemi=0,
                ),
                gnomad_genomes=hl.Struct(
                    AF=0.0001722949673421681,
                    AN=5804,
                    AC=1,
                    Hom=0,
                    AF_POPMAX_OR_GLOBAL=0.0005662514013238251,
                    FAF_AF=0.0,
                    Hemi=0,
                ),
                dbnsfp=hl.Struct(
                    PrimateAI_score=0.37232041358947754,
                    fathmm_MKL_coding_score=0.056940000504255295,
                    CADD_phred=15.880000114440918,
                    SIFT_score=0.1289999932050705,
                    REVEL_score=0.07500000298023224,
                    Polyphen2_HVAR_score=0.0010000000474974513,
                    VEST4_score=0.10700000077486038,
                    MPC_score=1.8921889066696167,
                    MutPred_score=0.3779999911785126,
                    MutationTaster_pred_id=2,
                ),
                topmed=hl.Struct(
                    AC=95,
                    AF=0.0007565619889646769,
                    AN=125568,
                    Hom=0,
                    Het=95,
                ),
                exac=hl.Struct(
                    AF_POPMAX=None,
                    AF=0.0016550000291317701,
                    AC_Adj=0,
                    AC_Het=0,
                    AC_Hom=0,
                    AC_Hemi=None,
                    AN_Adj=66,
                ),
                eigen=hl.Struct(Eigen_phred=1.0019999742507935),
                splice_ai=hl.Struct(
                    delta_score=0.019999999552965164,
                    splice_consequence_id=2,
                ),
                key_=1424,
            ),
        )

    def test_camelcase_array_structexpression_fields(self) -> None:
        ht = hl.read_table(TEST_SNV_INDEL_ANNOTATIONS)
        ht = unmap_formatting_annotation_enums(
            ht,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
        )
        ht = camelcase_array_structexpression_fields(
            ht,
            ReferenceGenome.GRCh38,
            DatasetType.SNV_INDEL,
        )
        ht = ht.annotate(
            sortedTranscriptConsequences=[ht.sortedTranscriptConsequences[0]],
        )
        self.assertEqual(
            ht.collect()[0],
            hl.Struct(
                key_=0,
                locus=hl.Locus(
                    contig='chr1',
                    position=876499,
                    reference_genome='GRCh38',
                ),
                alleles=['A', 'G'],
                clinvar=hl.Struct(
                    alleleId=929885,
                    conflictingPathogenicities=None,
                    goldStars=1,
                    submitters=['Labcorp Genetics (formerly Invitae), Labcorp'],
                    conditions=['not provided'],
                    assertion_ids=[],
                    pathogenicity_id=12,
                ),
                rg37_locus=hl.Locus(
                    contig=1,
                    position=874501,
                    reference_genome='GRCh37',
                ),
                rsid=None,
                variant_id='1-876499-A-G',
                xpos=1000876499,
                gt_stats=hl.Struct(AC=47, AN=81784, AF=0.0005746845272369683, hom=1),
                CAID='CA502654',
                check_ref=False,
                gnomad_non_coding_constraint=hl.Struct(z_score=None),
                hgmd=hl.Struct(accession='abcdefg', class_id=3),
                gnomad_exomes=hl.Struct(
                    AF=0.0006690866430290043,
                    AN=1440770,
                    AC=964,
                    Hom=0,
                    AF_POPMAX_OR_GLOBAL=0.0008023773552849889,
                    FAF_AF=0.000633420015219599,
                    Hemi=0,
                ),
                gnomad_genomes=hl.Struct(
                    AF=0.0002759889466688037,
                    AN=152180,
                    AC=42,
                    Hom=0,
                    AF_POPMAX_OR_GLOBAL=0.10000000149011612,
                    FAF_AF=0.0002092500071739778,
                    Hemi=0,
                ),
                screen=hl.Struct(region_type_ids=[]),
                dbnsfp=hl.Struct(
                    PrimateAI_score=0.5918066501617432,
                    fathmm_MKL_coding_score=0.7174800038337708,
                    CADD_phred=23.5,
                    SIFT_score=0.0010000000474974513,
                    REVEL_score=0.3109999895095825,
                    Polyphen2_HVAR_score=0.164000004529953,
                    VEST4_score=0.39500001072883606,
                    MPC_score=0.01291007362306118,
                    MutPred_score=None,
                    MutationTaster_pred_id=0,
                ),
                topmed=hl.Struct(
                    AC=41,
                    AF=0.00032651599030941725,
                    AN=125568,
                    Hom=0,
                    Het=41,
                ),
                exac=hl.Struct(
                    AF_POPMAX=0.0007150234305299819,
                    AF=0.00019039999460801482,
                    AC_Adj=20,
                    AC_Het=20,
                    AC_Hom=0,
                    AC_Hemi=None,
                    AN_Adj=47974,
                ),
                splice_ai=hl.Struct(
                    delta_score=0.0,
                    splice_consequence_id=4,
                ),
                eigen=hl.Struct(Eigen_phred=2.628000020980835),
                sortedTranscriptConsequences=[
                    hl.Struct(
                        aminoAcids='S/L',
                        canonical=1,
                        codons='tCg/tTg',
                        geneId='ENSG00000187634',
                        hgvsc='ENST00000616016.5:c.1049C>T',
                        hgvsp='ENSP00000478421.2:p.Ser350Leu',
                        transcriptId='ENST00000616016',
                        maneSelect='NM_001385641.1',
                        manePlusClinical=None,
                        exon=hl.Struct(index=6, total=14),
                        intron=None,
                        refseqTranscriptId='NM_001385641.1',
                        alphamissense=hl.Struct(pathogenicity=None),
                        loftee=hl.Struct(isLofNagnag=None, lofFilters=None),
                        spliceregion=hl.Struct(
                            extended_intronic_splice_region_variant=False,
                        ),
                        utrannotator=hl.Struct(
                            existingInframeOorfs=None,
                            existingOutofframeOorfs=None,
                            existingUorfs=None,
                            fiveutrAnnotation=hl.Struct(
                                type='OutOfFrame_oORF',
                                KozakContext='CGCATGC',
                                KozakStrength='Weak',
                                DistanceToCDS=41,
                                CapDistanceToStart=None,
                                DistanceToStop=None,
                                Evidence=None,
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
                            fiveutrConsequence=None,
                        ),
                        biotype='protein_coding',
                        consequenceTerms=['missense_variant'],
                    ),
                ],
                sortedRegulatoryFeatureConsequences=[
                    hl.Struct(
                        regulatoryFeatureId='ENSR00000344437',
                        biotype='CTCF_binding_site',
                        consequenceTerms=['regulatory_region_variant'],
                    ),
                ],
                sortedMotifFeatureConsequences=[
                    hl.Struct(
                        motifFeatureId='ENSM00493959715',
                        consequenceTerms=['TF_binding_site_variant'],
                    ),
                ],
            ),
        )

    def test_sorted_hl_struct(self) -> None:
        struct = hl.Struct(
            z=5,
            y=hl.Struct(b=2, a=hl.Struct(d=4, c=3)),
            x=hl.Struct(k=9),
        )
        self.assertEqual(
            sorted_hl_struct(struct),
            hl.Struct(x=hl.Struct(k=9), y=hl.Struct(a=hl.Struct(c=3, d=4), b=2), z=5),
        )
