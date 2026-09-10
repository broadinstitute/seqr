import unittest

import hail as hl

from loading_pipeline.lib.misc.gcnv import parse_gcnv_genes


class GCNVGeneParsingTest(unittest.TestCase):
    def test_parse_gcnv_genes(self):
        t1 = hl.Table.parallelize(
            [
                {'genes': 'AC118553.2,SLC35A3'},
                {'genes': 'AC118553.1,None'},
                {'genes': 'None'},
                {'genes': 'SLC35A3.43'},
                {'genes': ''},
                {'genes': 'SLC35A4.43'},
            ],
            hl.tstruct(genes=hl.dtype('str')),
            key='genes',
        )
        t1 = t1.annotate(gene_set=parse_gcnv_genes(t1.genes))
        self.assertCountEqual(
            t1.collect(),
            [
                hl.Struct(
                    genes='AC118553.2,SLC35A3',
                    gene_set={'AC118553', 'SLC35A3'},
                ),
                hl.Struct(genes='AC118553.1,None', gene_set={'AC118553'}),
                hl.Struct(genes='None', gene_set=set()),
                hl.Struct(genes='SLC35A3.43', gene_set={'SLC35A3'}),
                hl.Struct(genes='', gene_set=set()),
                hl.Struct(genes='SLC35A4.43', gene_set={'SLC35A4'}),
            ],
        )

    def test_aggregate_parsed_genes(self):
        t1 = hl.Table.parallelize(
            [
                {'genes': 'AC118553.2,SLC35A3'},
                {'genes': 'AC118553.1,None'},
                {'genes': 'None'},
                {'genes': 'SLC35A3.43'},
                {'genes': ''},
                {'genes': 'SLC35A4.43'},
            ],
            hl.tstruct(genes=hl.dtype('str')),
            key='genes',
        )
        aggregated_gene_set = t1.aggregate(
            hl.flatten(hl.agg.collect_as_set(parse_gcnv_genes(t1.genes))),
        )
        self.assertEqual(aggregated_gene_set, {'SLC35A4', 'SLC35A3', 'AC118553'})
