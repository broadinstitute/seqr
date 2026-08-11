import unittest

import hail as hl

from loading_pipeline.lib.misc.nested_field import parse_nested_field


class TestConstrainFunction(unittest.TestCase):
    def test_parse_nested_field(self):
        ht = hl.Table.parallelize(
            [
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    'alleles': ['A', 'C'],
                    'a': hl.Struct(d=1),
                    'b': hl.Struct(e=[2, 9]),
                    'h': hl.Struct(**{'i.j': 1}),
                    'a_index': 1,
                },
                {
                    'locus': hl.Locus(
                        contig='chr1',
                        position=2,
                        reference_genome='GRCh38',
                    ),
                    'alleles': ['A', 'C'],
                    'a': hl.Struct(d=3),
                    'b': hl.Struct(e=[4, 5]),
                    'h': hl.Struct(**{'i.j': 2}),
                    'a_index': 1,
                },
            ],
            hl.tstruct(
                locus=hl.tlocus('GRCh38'),
                alleles=hl.tarray(hl.tstr),
                a=hl.tstruct(d=hl.tint32),
                b=hl.tstruct(e=hl.tarray(hl.tint32)),
                h=hl.tstruct(**{'i.j': hl.tint32}),
                a_index=hl.tint32,
            ),
            key=['locus', 'alleles'],
        )
        ht = ht.select(
            d=parse_nested_field(ht, 'a.d'),
            e=parse_nested_field(ht, 'b.e#'),
            f=parse_nested_field(ht, 'a'),
            g=parse_nested_field(ht, 'h.i.j'),
        )
        self.assertListEqual(
            ht.collect(),
            [
                hl.Struct(
                    locus=hl.Locus(
                        contig='chr1',
                        position=1,
                        reference_genome='GRCh38',
                    ),
                    alleles=['A', 'C'],
                    d=1,
                    e=2,
                    f=hl.Struct(d=1),
                    g=1,
                ),
                hl.Struct(
                    locus=hl.Locus(
                        contig='chr1',
                        position=2,
                        reference_genome='GRCh38',
                    ),
                    alleles=['A', 'C'],
                    d=3,
                    e=4,
                    f=hl.Struct(d=3),
                    g=2,
                ),
            ],
        )
