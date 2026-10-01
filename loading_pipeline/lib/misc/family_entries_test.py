import unittest

import hail as hl

from loading_pipeline.lib.core import DatasetType, SampleType
from loading_pipeline.lib.misc.family_entries import (
    compute_callset_family_entries_ht,
    deduplicate_by_most_non_ref_calls,
)


class FamilyEntriesTest(unittest.TestCase):
    def test_compute_callset_family_entries_ht(self) -> None:
        mt = hl.MatrixTable.from_parts(
            rows={
                'variants': [1, 2, 3],
                'filters': [
                    hl.empty_set(hl.tstr),
                    {'HIGH_SR_BACKGROUND'},
                    hl.empty_set(hl.tstr),
                ],
                'locus': [
                    hl.Struct(contig='1', position=123),
                    hl.Struct(contig='1', position=456),
                    hl.Struct(contig='1', position=789),
                ],
                'alleles': [
                    ['A', 'C'],
                    ['A', 'AGT'],
                    ['G', 'T'],
                ],
            },
            cols={'s': ['a', 'b', 'd', 'c']},
            entries={
                'GT': [
                    [
                        hl.Call([0, 0]),
                        hl.missing(hl.tcall),
                        hl.Call([0, 0]),
                        hl.Call([0, 0]),
                    ],
                    [
                        hl.Call([0, 0]),
                        hl.Call([0, 0]),
                        hl.Call([1, 1]),
                        hl.Call([0, 0]),
                    ],
                    [
                        hl.Call([0, 1]),
                        hl.Call([0, 0]),
                        hl.Call([1, 1]),
                        hl.Call([0, 0]),
                    ],
                ],
            },
            globals={
                'family_samples': {'2': ['a'], '1': ['b', 'c', 'd']},
                'project_families': {'p1': ['1'], 'p2': ['2', '3']},
            },
        ).key_rows_by('locus', 'alleles')
        ht = compute_callset_family_entries_ht(
            DatasetType.SNV_INDEL,
            mt,
            {'gt': mt.GT.n_alt_alleles()},
            SampleType.WGS,
        )
        self.maxDiff = None
        self.assertCountEqual(
            ht.filters.collect(),
            [{'HIGH_SR_BACKGROUND'}, set()],
        )
        self.assertCountEqual(
            ht.family_entries.collect(),
            [
                [
                    [
                        hl.Struct(GT=hl.Call(alleles=[0, 0], phased=False)),
                        hl.Struct(GT=hl.Call(alleles=[0, 0], phased=False)),
                        hl.Struct(GT=hl.Call(alleles=[1, 1], phased=False)),
                    ],
                    None,
                ],
                [
                    [
                        hl.Struct(GT=hl.Call(alleles=[0, 0], phased=False)),
                        hl.Struct(GT=hl.Call(alleles=[0, 0], phased=False)),
                        hl.Struct(GT=hl.Call(alleles=[1, 1], phased=False)),
                    ],
                    [hl.Struct(GT=hl.Call(alleles=[0, 1], phased=False))],
                ],
            ],
        )

    def test_deduplicate_by_most_non_ref_calls(self) -> None:
        project_ht = hl.Table.parallelize(
            [
                {
                    'id': 0,
                    'filters': {'PASS', 'HIGH_SR_BACKGROUND'},
                    'family_entries': [
                        [
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_a',
                                s='sample_1',
                            ),
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 0], phased=False),
                                family_guid='family_a',
                                s='sample_2',
                            ),
                        ],
                        [
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_b',
                                s='sample_3',
                            ),
                            None,
                        ],
                        None,
                    ],
                },
                {
                    'id': 0,
                    'filters': {'PASS'},
                    'family_entries': [
                        [
                            None,
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 0], phased=False),
                                family_guid='family_a',
                                s='sample_2',
                            ),
                        ],
                        [
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_b',
                                s='sample_3',
                            ),
                            None,
                        ],
                        None,
                    ],
                },
                {
                    'id': 2,
                    'filters': {'HIGH_SR_BACKGROUND'},
                    'family_entries': [
                        None,
                        None,
                    ],
                },
                {
                    'id': 3,
                    'filters': {'PASS'},
                    'family_entries': [
                        [
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_a',
                                s='sample_1',
                            ),
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_a',
                                s='sample_2',
                            ),
                        ],
                        None,
                    ],
                },
            ],
            hl.tstruct(
                id=hl.tint32,
                filters=hl.tset(hl.tstr),
                family_entries=hl.tarray(
                    hl.tarray(
                        hl.tstruct(
                            GT=hl.tcall,
                            family_guid=hl.tstr,
                            s=hl.tstr,
                        ),
                    ),
                ),
            ),
            key='id',
        )
        ht = deduplicate_by_most_non_ref_calls(project_ht)
        self.assertEqual(
            ht.collect(),
            [
                hl.Struct(
                    id=0,
                    filters={'PASS', 'HIGH_SR_BACKGROUND'},
                    family_entries=[
                        [
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_a',
                                s='sample_1',
                            ),
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 0], phased=False),
                                family_guid='family_a',
                                s='sample_2',
                            ),
                        ],
                        [
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_b',
                                s='sample_3',
                            ),
                            None,
                        ],
                        None,
                    ],
                ),
                hl.Struct(
                    id=2,
                    filters={'HIGH_SR_BACKGROUND'},
                    family_entries=[None, None],
                ),
                hl.Struct(
                    id=3,
                    filters={'PASS'},
                    family_entries=[
                        [
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_a',
                                s='sample_1',
                            ),
                            hl.Struct(
                                GT=hl.Call(alleles=[0, 1], phased=False),
                                family_guid='family_a',
                                s='sample_2',
                            ),
                        ],
                        None,
                    ],
                ),
            ],
        )
