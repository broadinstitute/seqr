import unittest

import hail as hl

from loading_pipeline.lib.core import Sex
from loading_pipeline.lib.misc.family_loading_failures import (
    all_relatedness_checks,
    build_relatedness_check_lookup,
    build_sex_check_lookup,
    get_families_failed_imputed_sex_ploidy,
    get_families_failed_sex_check,
)
from loading_pipeline.lib.misc.io import import_pedigree
from loading_pipeline.lib.misc.pedigree import (
    Family,
    Sample,
    parse_pedigree_ht_to_families,
)

TEST_SEX_CHECK_1 = 'loading_pipeline/var/test/sex_check/test_sex_check_1.ht'
TEST_PEDIGREE_6 = 'loading_pipeline/var/test/pedigrees/test_pedigree_6.tsv'


class FamilyLoadingFailuresTest(unittest.TestCase):
    def test_build_relatedness_check_lookup(self):
        ht = hl.Table.parallelize(
            [
                {
                    'i': 'ROS_006_18Y03226_D1',
                    'j': 'ROS_007_19Y05939_D1',
                    'ibd0': 0.0,
                    'ibd1': 1.0,
                    'ibd2': 0.0,
                    'pi_hat': 0.5,
                },
            ],
            hl.tstruct(
                i=hl.tstr,
                j=hl.tstr,
                ibd0=hl.tfloat,
                ibd1=hl.tfloat,
                ibd2=hl.tfloat,
                pi_hat=hl.tfloat,
            ),
            key=['i', 'j'],
        )
        self.assertEqual(
            build_relatedness_check_lookup(
                ht,
                hl.dict({'ROS_006_18Y03226_D1': 'remapped_id'}),
            ),
            {
                ('ROS_007_19Y05939_D1', 'remapped_id'): [
                    0.0,
                    1.0,
                    0.0,
                    0.5,
                ],
            },
        )

    def test_build_sex_check_lookup(self):
        ht = hl.Table.parallelize(
            [
                {'s': 'ROS_006_18Y03226_D1', 'predicted_sex': 'F'},
                {'s': 'ROS_006_18Y03227_D1', 'predicted_sex': 'F'},
                {'s': 'ROS_006_18Y03228_D1', 'predicted_sex': 'F'},
                {'s': 'ROS_007_19Y05919_D1', 'predicted_sex': 'F'},
                {'s': 'ROS_007_19Y05939_D1', 'predicted_sex': 'M'},
                {'s': 'ROS_007_19Y05987_D1', 'predicted_sex': 'U'},
                {'s': 'ROS_007_19Y05989_D1', 'predicted_sex': 'X0'},
            ],
            hl.tstruct(
                s=hl.tstr,
                predicted_sex=hl.tstr,
            ),
            key='s',
        )
        self.assertEqual(
            build_sex_check_lookup(ht, hl.dict({'ROS_006_18Y03226_D1': 'remapped_id'})),
            {
                'remapped_id': Sex.FEMALE,
                'ROS_006_18Y03227_D1': Sex.FEMALE,
                'ROS_006_18Y03228_D1': Sex.FEMALE,
                'ROS_007_19Y05919_D1': Sex.FEMALE,
                'ROS_007_19Y05939_D1': Sex.MALE,
                'ROS_007_19Y05987_D1': Sex.UNKNOWN,
                'ROS_007_19Y05989_D1': Sex.X0,
            },
        )

    def test_all_relatedness_checks(self):
        relatedness_check_lookup = {
            # Parent
            ('sample_1', 'sample_2'): [
                0.0,
                0.98,
                0.0,
                0.52,
            ],
            # GrandParent
            ('sample_1', 'sample_3'): [0.48, 0.52, 0, 0.24],
            # Half Sibling (but actually a hidden Sibling)
            ('sample_1', 'sample_4'): [0.25, 0.5, 0.25, 0.5],
        }
        sample = Sample(
            sex=Sex.FEMALE,
            sample_id='sample_1',
            mother='sample_2',
            paternal_grandfather='sample_3',
            half_siblings=['sample_4'],
        )
        family = Family(
            family_guid='family_1a',
            samples={
                'sample_1': sample,
                'sample_2': Sample(sex=Sex.MALE, sample_id='sample_2'),
                'sample_3': Sample(sex=Sex.MALE, sample_id='sample_3'),
                'sample_4': Sample(sex=Sex.MALE, sample_id='sample_4'),
                'sample_5': Sample(sex=Sex.MALE, sample_id='sample_5'),
            },
        )
        failure_reasons = all_relatedness_checks(
            relatedness_check_lookup,
            family,
            sample,
        )
        self.assertListEqual(failure_reasons, [])

        # Defined grandparent missing in relatedness table
        sample = Sample(
            sex=Sex.FEMALE,
            sample_id='sample_1',
            mother='sample_2',
            paternal_grandfather='sample_3',
            paternal_grandmother='sample_5',
        )
        failure_reasons = all_relatedness_checks(
            relatedness_check_lookup,
            family,
            sample,
        )
        self.assertListEqual(
            failure_reasons,
            [
                'Sample sample_1 has expected relation "grandparent_grandchild" to sample_5 but has coefficients []',
            ],
        )

        # Sibling is actually a half sibling.
        relatedness_check_lookup = {
            **relatedness_check_lookup,
            ('sample_1', 'sample_4'): [0.5, 0.5, 0, 0.25],
        }
        sample = Sample(
            sex=Sex.FEMALE,
            sample_id='sample_1',
            mother='sample_2',
            paternal_grandfather='sample_3',
            siblings=['sample_4'],
        )
        failure_reasons = all_relatedness_checks(
            relatedness_check_lookup,
            family,
            sample,
        )
        self.assertListEqual(
            failure_reasons,
            [
                'Sample sample_1 has expected relation "sibling" to sample_4 but has coefficients [0.5, 0.5, 0, 0.25]',
            ],
        )

        relatedness_check_lookup = {
            **relatedness_check_lookup,
            ('sample_1', 'sample_2'): [
                0.5,
                0.5,
                0.5,
                0.5,
            ],
        }
        sample = Sample(
            sex=Sex.FEMALE,
            sample_id='sample_1',
            mother='sample_2',
            paternal_grandfather='sample_3',
            siblings=['sample_4'],
        )
        failure_reasons = all_relatedness_checks(
            relatedness_check_lookup,
            family,
            sample,
        )
        self.assertListEqual(
            failure_reasons,
            [
                'Sample sample_1 has expected relation "parent_child" to sample_2 but has coefficients [0.5, 0.5, 0.5, 0.5]',
                'Sample sample_1 has expected relation "sibling" to sample_4 but has coefficients [0.5, 0.5, 0, 0.25]',
            ],
        )

        # Some samples will include relationships with
        # samples that are not expected to be included
        # in the callset.  These should not trigger relatedness
        # failures.
        sample = Sample(
            sex=Sex.FEMALE,
            sample_id='sample_1',
            mother='sample_2',
        )
        family = Family(
            family_guid='family_1a',
            samples={
                'sample_1': sample,
            },
        )
        failure_reasons = all_relatedness_checks(
            {},
            family,
            sample,
        )
        self.assertListEqual(
            failure_reasons,
            [],
        )

    def test_get_families_failed_sex_check(self):
        sex_check_ht = hl.Table.parallelize(
            [
                {'s': 'ROS_006_18Y03226_D1', 'predicted_sex': 'F'},
                {'s': 'ROS_006_18Y03227_D1', 'predicted_sex': 'F'},  # Pedigree Sex U
                {'s': 'ROS_006_18Y03228_D1', 'predicted_sex': 'F'},
                {'s': 'ROS_007_19Y05939_D1', 'predicted_sex': 'M'},
                {'s': 'ROS_007_19Y05987_D1', 'predicted_sex': 'U'},  # Pedigree Sex F
                {'s': 'ROS_007_19Y05989_D1', 'predicted_sex': 'XXX'},
            ],
            hl.tstruct(
                s=hl.tstr,
                predicted_sex=hl.tstr,
            ),
            key='s',
        )
        pedigree_ht = import_pedigree(TEST_PEDIGREE_6)
        failed_families = get_families_failed_sex_check(
            parse_pedigree_ht_to_families(pedigree_ht),
            sex_check_ht,
            {},
        )
        self.assertCountEqual(
            failed_families.values(),
            [
                [
                    'Sample ROS_007_19Y05919_D1 has pedigree sex F but is missing from the sex check source',
                    'Sample ROS_007_19Y05939_D1 has pedigree sex F but imputed sex M',
                ],
            ],
        )

    def test_get_families_failed_imputed_sex_ploidy(self) -> None:
        female_sample = 'HG00731_1'
        male_sample_1 = 'HG00732_1'
        male_sample_2 = 'HG00732_1'
        x0_sample = 'NA20899_1'
        xxy_sample = 'NA20889_1'
        xyy_sample = 'NA20891_1'
        xxx_sample = 'NA20892_1'

        sex_check_ht = hl.read_table(TEST_SEX_CHECK_1)
        families = {
            Family(
                family_guid='',
                samples={
                    female_sample: Sample(female_sample, Sex.FEMALE),
                    male_sample_1: Sample(male_sample_1, Sex.MALE),
                    male_sample_2: Sample(male_sample_2, Sex.MALE),
                    x0_sample: Sample(x0_sample, Sex.X0),
                    xxy_sample: Sample(xxy_sample, Sex.XXY),
                    xyy_sample: Sample(xyy_sample, Sex.XYY),
                    xxx_sample: Sample(xxx_sample, Sex.XXX),
                },
            ),
        }

        # All calls on X chromosome are valid
        mt = (
            hl.MatrixTable.from_parts(
                rows={
                    'locus': [
                        hl.Locus(
                            contig='chrX',
                            position=1,
                            reference_genome='GRCh38',
                        ),
                    ],
                },
                cols={
                    's': [
                        female_sample,
                        male_sample_1,
                        x0_sample,
                        xxy_sample,
                        xyy_sample,
                        xxx_sample,
                    ],
                },
                entries={
                    'GT': [
                        [
                            hl.Call(alleles=[0, 0], phased=False),
                            hl.Call(alleles=[0], phased=False),
                            hl.Call(alleles=[0, 0], phased=False),  # X0
                            hl.Call(alleles=[0, 0], phased=False),  # XXY
                            hl.Call(alleles=[0, 0], phased=False),  # XYY
                            hl.Call(alleles=[0, 0], phased=False),  # XXX
                        ],
                    ],
                },
            )
            .key_rows_by('locus')
            .key_cols_by('s')
        )
        failed_families = get_families_failed_imputed_sex_ploidy(
            families,
            mt,
            sex_check_ht,
        )
        self.assertDictEqual(failed_families, {})

        # All calls on Y chromosome are valid
        mt = (
            hl.MatrixTable.from_parts(
                rows={
                    'locus': [
                        hl.Locus(
                            contig='chrY',
                            position=1,
                            reference_genome='GRCh38',
                        ),
                    ],
                },
                cols={
                    's': [
                        female_sample,
                        male_sample_1,
                        x0_sample,
                        xxy_sample,
                        xyy_sample,
                        xxx_sample,
                    ],
                },
                entries={
                    'GT': [
                        [
                            hl.missing(hl.tcall),
                            hl.Call(alleles=[0], phased=False),
                            hl.missing(hl.tcall),  # X0
                            hl.Call(alleles=[0, 0], phased=False),  # XXY
                            hl.Call(alleles=[0, 0], phased=False),  # XYY
                            hl.missing(hl.tcall),  # XXX
                        ],
                    ],
                },
            )
            .key_rows_by('locus')
            .key_cols_by('s')
        )
        failed_families = get_families_failed_imputed_sex_ploidy(
            families,
            mt,
            sex_check_ht,
        )
        self.assertDictEqual(failed_families, {})

        # Invalid X chromosome case
        mt = (
            hl.MatrixTable.from_parts(
                rows={
                    'locus': [
                        hl.Locus(
                            contig='chrX',
                            position=1,
                            reference_genome='GRCh38',
                        ),
                    ],
                },
                cols={
                    's': [
                        female_sample,
                        male_sample_1,
                        male_sample_2,
                        x0_sample,
                        xxy_sample,
                        xyy_sample,
                        xxx_sample,
                    ],
                },
                entries={
                    'GT': [
                        [
                            hl.Call(alleles=[0], phased=False),  # invalid Female call
                            hl.Call(alleles=[0], phased=False),  # valid Male call
                            hl.missing(hl.tcall),  # invalid Male call
                            hl.Call(alleles=[0], phased=False),  # invalid X0 call
                            hl.Call(alleles=[0], phased=False),  # invalid XXY call
                            hl.missing(hl.tcall),  # valid XYY call
                            hl.Call(alleles=[0, 0], phased=False),  # valid XXX call
                        ],
                    ],
                },
            )
            .key_rows_by('locus')
            .key_cols_by('s')
        )
        failed_families = get_families_failed_imputed_sex_ploidy(
            families,
            mt,
            sex_check_ht,
        )
        self.assertCountEqual(
            failed_families.values(),
            [
                [
                    "Found samples with misaligned ploidy with their provided imputed sex: ['HG00731_1', 'HG00732_1', 'NA20889_1', 'NA20899_1']",
                ],
            ],
        )

        # Invalid X chromosome case, but only discrepant family samples are reported
        families = {
            Family(
                family_guid='',
                samples={female_sample: Sample(female_sample, Sex.FEMALE)},
            ),
        }
        failed_families = get_families_failed_imputed_sex_ploidy(
            families,
            mt,
            sex_check_ht,
        )
        self.assertCountEqual(
            failed_families.values(),
            [
                [
                    "Found samples with misaligned ploidy with their provided imputed sex: ['HG00731_1']",
                ],
            ],
        )
