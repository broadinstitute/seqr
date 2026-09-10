from unittest.mock import Mock, patch

import hail as hl

from loading_pipeline.lib.annotations.fields import get_fields
from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
)
from loading_pipeline.lib.misc.vep import run_vep
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase
from loading_pipeline.var.test.vep.mock_vep_data import (
    MOCK_37_VEP_DATA,
    MOCK_38_VEP_DATA,
)


class FieldsTest(MockedDatarootTestCase):
    def setUp(self) -> None:
        super().setUp()

    @patch('loading_pipeline.lib.misc.vep.hl.vep')
    def test_get_formatting_fields(self, mock_vep: Mock) -> None:
        for reference_genome, ht, expected_fields in [
            (
                ReferenceGenome.GRCh38,
                hl.Table.parallelize(
                    [
                        {
                            'locus': hl.Locus(
                                contig='chr1',
                                position=1,
                                reference_genome='GRCh38',
                            ),
                            'alleles': ['A', 'C'],
                            'rsid': 'abcd',
                        },
                    ],
                    hl.tstruct(
                        locus=hl.tlocus('GRCh38'),
                        alleles=hl.tarray(hl.tstr),
                        rsid=hl.tstr,
                    ),
                    key=['locus', 'alleles'],
                ),
                [
                    'check_ref',
                    'rg37_locus',
                    'rsid',
                    'sorted_motif_feature_consequences',
                    'sorted_regulatory_feature_consequences',
                    'sorted_transcript_consequences',
                    'variant_id',
                    'xpos',
                ],
            ),
            (
                ReferenceGenome.GRCh37,
                hl.Table.parallelize(
                    [
                        {
                            'locus': hl.Locus(
                                contig='1',
                                position=1,
                                reference_genome='GRCh37',
                            ),
                            'alleles': ['A', 'C'],
                            'rsid': 'abcd',
                        },
                    ],
                    hl.tstruct(
                        locus=hl.tlocus('GRCh37'),
                        alleles=hl.tarray(hl.tstr),
                        rsid=hl.tstr,
                    ),
                    key=['locus', 'alleles'],
                ),
                [
                    'rg38_locus',
                    'rsid',
                    'sorted_transcript_consequences',
                    'variant_id',
                    'xpos',
                ],
            ),
        ]:
            mock_vep.return_value = ht.annotate(
                vep=MOCK_37_VEP_DATA
                if reference_genome == ReferenceGenome.GRCh37
                else MOCK_38_VEP_DATA,
            )
            ht = run_vep(  # noqa: PLW2901
                ht,
                DatasetType.SNV_INDEL,
                reference_genome,
            )
            self.assertCountEqual(
                list(
                    get_fields(
                        ht,
                        DatasetType.SNV_INDEL.formatting_annotation_fns(
                            reference_genome,
                        ),
                        **(
                            {
                                'gencode_ensembl_to_refseq_id_mapping': hl.dict(
                                    {'a': 'b'},
                                ),
                            }
                            if reference_genome == ReferenceGenome.GRCh38
                            else {}
                        ),
                        dataset_type=DatasetType.SNV_INDEL,
                        reference_genome=reference_genome,
                    ).keys(),
                ),
                expected_fields,
            )
