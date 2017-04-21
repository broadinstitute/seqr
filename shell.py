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
from seqr.models import Project as SeqrProject, Family as SeqrFamily, Individual as SeqrIndividual, VariantTagType, VariantTag
from django.contrib.auth.models import User, UserProfile
from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual

annotator = datastore = None
try:
    reference_db = pymongo.MongoClient('xbrowse_reference')
    reference = Reference(reference_settings) 

    annotator_db = pymongo.MongoClient('xbrowse_annotator')
    annotator = VariantAnnotator(annotator_settings, reference)
    annotator._ensure_indices()

    datastore_db = pymongo.MongoClient('xbrowse_datastore')
    datastore = MongoDatastore(datastore_db, annotator)
except Exception as e:
    print("Error while connecting to mongo: " + str(e))

user_ns = {
    'annotator': annotator, 
    'datastore': datastore,
    'BaseProject': BaseProject,
    'BaseFamily': BaseFamily,
    'BaseIndividual': BaseIndividual,
    'SeqrProject': SeqrProject,
    'SeqrFamily': SeqrFamily,
    'SeqrIndividual': SeqrIndividual,
    'VariantTag': VariantTag,
    'VariantTagType': VariantTagType,
    'User': User,
    'UserProfile': UserProfile,
}

import IPython
IPython.embed(user_ns=user_ns)
