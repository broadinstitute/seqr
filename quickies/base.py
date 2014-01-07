from xbrowse.reference import Reference
from xbrowse.annotation import VariantAnnotator
from xbrowse.coverage import CoverageDatastore
from xbrowse.datastore import MongoDatastore

import pymongo

reference_db = pymongo.Connection()['xbrowse_reference']
reference = Reference(reference_db, ensembl_db_host='useastdb.ensembl.org', ensembl_db_user="anonymous")

annotator_db = pymongo.Connection()['xbrowse_annotator']
annotator = VariantAnnotator(annotator_db, reference)
annotator.ensure_indices()

coverage_db = pymongo.Connection()['xbrowse_coverage']
coverage_store = CoverageDatastore(coverage_db, reference)

datastore_db = pymongo.Connection()['xbrowse_datastore']
datastore = MongoDatastore(datastore_db, annotator)