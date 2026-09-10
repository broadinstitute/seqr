import unittest

import hail as hl

from loading_pipeline.lib.core import Sex
from loading_pipeline.lib.misc.io import import_pedigree
from loading_pipeline.lib.misc.pedigree import (
    Family,
    Sample,
    parse_pedigree_ht_to_families,
)

TEST_PEDIGREE_1 = 'loading_pipeline/var/test/pedigrees/test_pedigree_1.tsv'
TEST_PEDIGREE_2 = 'loading_pipeline/var/test/pedigrees/test_pedigree_2.tsv'
TEST_PEDIGREE_9 = 'loading_pipeline/var/test/pedigrees/test_pedigree_9.tsv'


class PedigreesTest(unittest.TestCase):
    def test_empty_pedigree(self) -> None:
        with self.assertRaises(Exception):  # noqa: B017
            _ = import_pedigree(TEST_PEDIGREE_1)

    def test_parse_lineage(self) -> None:
        #
        #
        #       sample_9   sample_10        sample_7
        #           \        /                  \                       |
        # sample_6 -> sample_8      ---------     sample_3 ----- ?      |
        #                \                       /    \        /        |
        #                   sample_4, sample_5          sample_2        |    sample_1
        #
        #
        samples = Family.parse_direct_lineage(
            [
                hl.Struct(s='sample_1', maternal_s=None, paternal_s=None, sex='F'),
                hl.Struct(
                    s='sample_2',
                    maternal_s='sample_3',
                    paternal_s=None,
                    sex='M',
                ),
                hl.Struct(
                    s='sample_3',
                    maternal_s=None,
                    paternal_s='sample_7',
                    sex='F',
                ),
                hl.Struct(
                    s='sample_4',
                    maternal_s='sample_3',
                    paternal_s='sample_8',
                    sex='M',
                ),
                hl.Struct(
                    s='sample_5',
                    maternal_s='sample_3',
                    paternal_s='sample_8',
                    sex='M',
                ),
                hl.Struct(
                    s='sample_6',
                    maternal_s='sample_9',
                    paternal_s='sample_10',
                    sex='M',
                ),
                hl.Struct(s='sample_7', maternal_s=None, paternal_s=None, sex='M'),
                hl.Struct(
                    s='sample_8',
                    maternal_s='sample_9',
                    paternal_s='sample_10',
                    sex='F',
                ),
                hl.Struct(s='sample_9', maternal_s=None, paternal_s=None, sex='F'),
                hl.Struct(s='sample_10', maternal_s=None, paternal_s=None, sex='M'),
            ],
        )
        self.assertEqual(
            Family.parse_collateral_lineage(samples),
            {
                'sample_1': Sample(
                    sample_id='sample_1',
                    sex=Sex.FEMALE,
                    mother=None,
                    father=None,
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_2': Sample(
                    sample_id='sample_2',
                    sex=Sex.MALE,
                    mother='sample_3',
                    father=None,
                    maternal_grandmother=None,
                    maternal_grandfather='sample_7',
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=['sample_4', 'sample_5'],
                    aunt_nephews=[],
                ),
                'sample_3': Sample(
                    sample_id='sample_3',
                    sex=Sex.FEMALE,
                    mother=None,
                    father='sample_7',
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_4': Sample(
                    sample_id='sample_4',
                    sex=Sex.MALE,
                    mother='sample_3',
                    father='sample_8',
                    maternal_grandmother=None,
                    maternal_grandfather='sample_7',
                    paternal_grandmother='sample_9',
                    paternal_grandfather='sample_10',
                    siblings=['sample_5'],
                    half_siblings=[],
                    aunt_nephews=['sample_6'],
                ),
                'sample_5': Sample(
                    sample_id='sample_5',
                    sex=Sex.MALE,
                    mother='sample_3',
                    father='sample_8',
                    maternal_grandmother=None,
                    maternal_grandfather='sample_7',
                    paternal_grandmother='sample_9',
                    paternal_grandfather='sample_10',
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=['sample_6'],
                ),
                'sample_6': Sample(
                    sample_id='sample_6',
                    sex=Sex.MALE,
                    mother='sample_9',
                    father='sample_10',
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=['sample_8'],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_7': Sample(
                    sample_id='sample_7',
                    sex=Sex.MALE,
                    mother=None,
                    father=None,
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_8': Sample(
                    sample_id='sample_8',
                    sex=Sex.FEMALE,
                    mother='sample_9',
                    father='sample_10',
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_9': Sample(
                    sample_id='sample_9',
                    sex=Sex.FEMALE,
                    mother=None,
                    father=None,
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_10': Sample(
                    sample_id='sample_10',
                    sex=Sex.MALE,
                    mother=None,
                    father=None,
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
            },
        )

    def test_parse_parent_not_aunt_uncle(self) -> None:
        samples = Family.parse_direct_lineage(
            [
                hl.Struct(s='sample_1', maternal_s=None, paternal_s=None, sex='F'),
                hl.Struct(
                    s='sample_2',
                    maternal_s=None,
                    paternal_s=None,
                    sex='M',
                ),
                hl.Struct(
                    s='sample_3',
                    maternal_s='sample_1',
                    paternal_s='sample_2',
                    sex='F',
                ),
                hl.Struct(
                    s='sample_4',
                    maternal_s='sample_3',
                    paternal_s=None,
                    sex='F',
                ),
                hl.Struct(
                    s='sample_5',
                    maternal_s='sample_3',
                    paternal_s=None,
                    sex='F',
                ),
            ],
        )
        self.assertEqual(
            Family.parse_collateral_lineage(samples),
            {
                'sample_1': Sample(
                    sample_id='sample_1',
                    sex=Sex.FEMALE,
                    mother=None,
                    father=None,
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_2': Sample(
                    sample_id='sample_2',
                    sex=Sex.MALE,
                    mother=None,
                    father=None,
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_3': Sample(
                    sample_id='sample_3',
                    sex=Sex.FEMALE,
                    mother='sample_1',
                    father='sample_2',
                    maternal_grandmother=None,
                    maternal_grandfather=None,
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
                'sample_4': Sample(
                    sample_id='sample_4',
                    sex=Sex.FEMALE,
                    mother='sample_3',
                    father=None,
                    maternal_grandmother='sample_1',
                    maternal_grandfather='sample_2',
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=['sample_5'],
                    aunt_nephews=[],
                ),
                'sample_5': Sample(
                    sample_id='sample_5',
                    sex=Sex.FEMALE,
                    mother='sample_3',
                    father=None,
                    maternal_grandmother='sample_1',
                    maternal_grandfather='sample_2',
                    paternal_grandmother=None,
                    paternal_grandfather=None,
                    siblings=[],
                    half_siblings=[],
                    aunt_nephews=[],
                ),
            },
        )

    def test_parse_project(self) -> None:
        pedigree_ht = import_pedigree(TEST_PEDIGREE_2)
        self.assertCountEqual(
            list(parse_pedigree_ht_to_families(pedigree_ht)),
            [
                Family(
                    family_guid='BBL_BC1-000345_1',
                    samples={
                        'BBL_BC1-000345_01_D1': Sample(
                            sample_id='BBL_BC1-000345_01_D1',
                            sex=Sex.UNKNOWN,
                            mother='BBL_BC1-000345_03_D1',
                            father='BBL_BC1-000345_02_D1',
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                        'BBL_BC1-000345_02_D1': Sample(
                            sample_id='BBL_BC1-000345_02_D1',
                            sex=Sex.MALE,
                            mother=None,
                            father=None,
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                        'BBL_BC1-000345_03_D1': Sample(
                            sample_id='BBL_BC1-000345_03_D1',
                            sex=Sex.FEMALE,
                            mother=None,
                            father=None,
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                    },
                ),
                Family(
                    family_guid='BBL_HT-007-5195_1',
                    samples={
                        'BBL_HT-007-5195_01_D1': Sample(
                            sample_id='BBL_HT-007-5195_01_D1',
                            sex=Sex.FEMALE,
                            mother='BBL_HT-007-5195_03_D1',
                            father='BBL_HT-007-5195_02_D1',
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[
                                'BBL_HT-007-5195_04_D1',
                                'BBL_HT-007-5195_05_D1',
                                'BBL_HT-007-5195_06_D1',
                            ],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                        'BBL_HT-007-5195_02_D1': Sample(
                            sample_id='BBL_HT-007-5195_02_D1',
                            sex=Sex.MALE,
                            mother=None,
                            father=None,
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                        'BBL_HT-007-5195_03_D1': Sample(
                            sample_id='BBL_HT-007-5195_03_D1',
                            sex=Sex.FEMALE,
                            mother=None,
                            father=None,
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                        'BBL_HT-007-5195_04_D1': Sample(
                            sample_id='BBL_HT-007-5195_04_D1',
                            sex=Sex.MALE,
                            mother='BBL_HT-007-5195_03_D1',
                            father='BBL_HT-007-5195_02_D1',
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=['BBL_HT-007-5195_05_D1', 'BBL_HT-007-5195_06_D1'],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                        'BBL_HT-007-5195_05_D1': Sample(
                            sample_id='BBL_HT-007-5195_05_D1',
                            sex=Sex.FEMALE,
                            mother='BBL_HT-007-5195_03_D1',
                            father='BBL_HT-007-5195_02_D1',
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=['BBL_HT-007-5195_06_D1'],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                        'BBL_HT-007-5195_06_D1': Sample(
                            sample_id='BBL_HT-007-5195_06_D1',
                            sex=Sex.MALE,
                            mother='BBL_HT-007-5195_03_D1',
                            father='BBL_HT-007-5195_02_D1',
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                    },
                ),
                Family(
                    family_guid='BBL_SDS1-000178_1',
                    samples={
                        'BBL_SDS1-000178_01_D1': Sample(
                            sample_id='BBL_SDS1-000178_01_D1',
                            sex=Sex.FEMALE,
                            mother=None,
                            father=None,
                            maternal_grandmother=None,
                            maternal_grandfather=None,
                            paternal_grandmother=None,
                            paternal_grandfather=None,
                            siblings=[],
                            half_siblings=[],
                            aunt_nephews=[],
                        ),
                    },
                ),
            ],
        )

    def test_subsetted_pedigree_with_removed_parent(self) -> None:
        pedigree_ht = import_pedigree(TEST_PEDIGREE_2)
        pedigree_ht = pedigree_ht.filter(
            pedigree_ht.s != 'BBL_BC1-000345_02_D1',
        )
        parsed_pedigree = parse_pedigree_ht_to_families(pedigree_ht)
        family = next(
            iter(
                [
                    family
                    for family in parsed_pedigree
                    if family.family_guid == 'BBL_BC1-000345_1'
                ],
            ),
        )
        self.assertEqual(len(family.samples), 2)
        self.assertFalse(
            'BBL_BC1-000345_02_D1' in family.samples,
        )
        self.assertEqual(
            family.samples['BBL_BC1-000345_01_D1'].father,
            'BBL_BC1-000345_02_D1',
        )
        self.assertEqual(
            family.samples['BBL_BC1-000345_01_D1'].mother,
            'BBL_BC1-000345_03_D1',
        )

    def test_pedigree_ungrouped_families(self) -> None:
        pedigree_ht = import_pedigree(TEST_PEDIGREE_9)
        parsed_pedigree = parse_pedigree_ht_to_families(pedigree_ht)
        self.assertEqual(len(parsed_pedigree), 2)
        family = next(
            iter(
                [
                    family
                    for family in parsed_pedigree
                    if family.family_guid == 'family_2_1'
                ],
            ),
        )
        self.assertTrue(
            family.samples.keys() == {'RGP_164_1', 'RGP_164_2', 'RGP_164_4'},
        )
