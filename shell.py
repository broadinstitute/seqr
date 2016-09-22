#!/usr/bin/env python

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import django
django.setup()

import pymongo
from xbrowse.reference import Reference
from xbrowse.annotation import VariantAnnotator
from xbrowse.coverage import CoverageDatastore
from xbrowse.datastore import MongoDatastore
import reference_settings
import annotator_settings

reference_db = pymongo.MongoClient('xbrowse_reference')
reference = Reference(reference_settings) 

annotator_db = pymongo.MongoClient('xbrowse_annotator')
annotator = VariantAnnotator(annotator_settings, reference)
annotator._ensure_indices()

datastore_db = pymongo.MongoClient('xbrowse_datastore')
datastore = MongoDatastore(datastore_db, annotator)

user_ns = {
    'annotator': annotator, 
    'datastore': datastore,
}

import IPython
IPython.embed(user_ns=user_ns)
