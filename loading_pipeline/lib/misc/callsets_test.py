import unittest

import hail as hl

from loading_pipeline.lib.misc.callsets import union_callset_mts


class CallsetsTest(unittest.TestCase):
    def test_union_callset_mts(self) -> None:
        mt1 = (
            hl.MatrixTable.from_parts(
                rows={
                    'id': [
                        0,
                        1,
                    ],
                    'row_field': [
                        1,
                        2,
                    ],
                },
                cols={'s': ['sample_1']},
                entries={
                    'GT': [[hl.Call([0, 0])], [hl.Call([0, 0])]],
                },
            )
            .key_rows_by('id')
            .key_cols_by('s')
            .drop('row_idx', 'col_idx')
        )
        mt2 = (
            hl.MatrixTable.from_parts(
                rows={
                    'id': [
                        0,
                        2,
                    ],
                    'row_field': [
                        2,
                        3,
                    ],
                    'second_row_field': [
                        4,
                        5,
                    ],
                },
                cols={'s': ['sample_2']},
                entries={
                    'GT': [[hl.Call([0, 0])], [hl.Call([0, 1])]],
                },
            )
            .key_rows_by('id')
            .key_cols_by('s')
            .drop('row_idx', 'col_idx')
        )
        mt = union_callset_mts([mt1, mt2])
        self.assertEqual(
            mt.entries().collect(),
            [
                hl.Struct(
                    id=0,
                    row_field=1,
                    s='sample_1',
                    GT=hl.Call(alleles=[0, 0], phased=False),
                ),
                hl.Struct(
                    id=0,
                    row_field=1,
                    s='sample_2',
                    GT=hl.Call(alleles=[0, 0], phased=False),
                ),
                hl.Struct(
                    id=1,
                    row_field=2,
                    s='sample_1',
                    GT=hl.Call(alleles=[0, 0], phased=False),
                ),
                hl.Struct(id=1, row_field=2, s='sample_2', GT=None),
                hl.Struct(id=2, row_field=None, s='sample_1', GT=None),
                hl.Struct(
                    id=2,
                    row_field=None,
                    s='sample_2',
                    GT=hl.Call(alleles=[0, 1], phased=False),
                ),
            ],
        )
