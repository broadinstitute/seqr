import unittest

import pymongo
from django.conf import settings

from xbrowse.reference import Reference
from xbrowse.annotation import VariantAnnotator


class AnnotatorTests(unittest.TestCase):

    def setUp(self):
        reference_db = settings.XBROWSE_REFERENCE_DB
        self.reference = Reference(reference_db, ensembl_db_port=3001, ensembl_db_user="mysqldba")

        annotator_db = settings.XBROWSE_ANNOTATOR_DB
        self.annotator = VariantAnnotator(annotator_db, self.reference)

        self.populations = ['g1k_all', 'esp_ea', 'esp_aa', 'atgu_controls']

    def test_actn3(self):
        annotation = self.annotator.get_annotation_for_variant(11e9+66328095, 'T', 'C', self.populations)
        print annotation

    def test_103807450(self):
        annotation = self.annotator.get_annotation_for_variant(1e9+3807450, 'C', 'A', self.populations)
        print annotation

if __name__ == '__main__':
    unittest.main()