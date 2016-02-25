"""
This just runs a bunch of quick tests against a fully loaded xbrowse reference
Used in initial development when I didn't have time to write unit tests - not sure where it should lead
"""

import unittest

import pymongo

from xbrowse.reference import Reference


class InternalLookupsTests(unittest.TestCase):
    """
    Test the different internal methods that query ensembl db and rest api
    """
    def setUp(self):
        reference_db = pymongo.MongoClient()['xbrowse_reference']
        self.reference = Reference(reference_db, ensembl_db_port=3001, ensembl_db_user="mysqldba")

    def test_phenotype_info(self):
        p = self.reference._get_ensembl_phenotype_info('ENSG00000196218')
        self.assertEqual(p['mim_id'], '180901')
        self.assertEqual(len(p['mim_phenotypes']), 4)
        self.assertEqual(len(p['orphanet_phenotypes']), 7)


class ReferenceTests(unittest.TestCase):

    def setUp(self):
        reference_db = pymongo.MongoClient()['xbrowse_reference']
        self.reference = Reference(reference_db, ensembl_db_port=3001, ensembl_db_user="mysqldba")

    def test_num_genes(self):
        self.assertEqual(len(self.reference._get_all_gene_ids()), 30585)

    def test_symbol_lookup(self):
        self.assertEqual(self.reference.get_gene_id_from_symbol('RYR1'), 'ENSG00000196218')

    def test_symbol_lookup_lower(self):
        self.assertEqual(self.reference.get_gene_id_from_symbol('ryr1'), 'ENSG00000196218')

    def test_id_lookup(self):
        self.assertEqual(self.reference.get_gene_symbol('ENSG00000196218'), 'RYR1')


class RYR1Tests(unittest.TestCase):

    def setUp(self):
        reference_db = pymongo.MongoClient()['xbrowse_reference']
        self.reference = Reference(reference_db, ensembl_db_port=3001, ensembl_db_user="mysqldba")
        gene_id = self.reference.get_gene_id_from_symbol('RYR1')
        self.gene = self.reference.get_gene(gene_id)

    def test_biotype(self):
        self.assertEqual(self.gene['biotype'], 'protein_coding')

    def test_description(self):
        self.assertEqual(self.gene['description'], 'ryanodine receptor 1 (skeletal) [Source:HGNC Symbol;Acc:10483]')

    def test_symbol(self):
        self.assertEqual(self.gene['symbol'], 'RYR1')

    def test_num_transcripts(self):
        self.assertEqual(len(self.gene['transcripts']), 13)

    def test_num_exons(self):
        self.assertEqual(len(self.gene['exons']), 158)


if __name__ == '__main__':
    unittest.main()