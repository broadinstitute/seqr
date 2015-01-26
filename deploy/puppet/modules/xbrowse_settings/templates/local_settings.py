from xbrowse.reference import Reference
from xbrowse.annotation import VariantAnnotator
from xbrowse.datastore.population_datastore import PopulationDatastore
from xbrowse.coverage import CoverageDatastore
from xbrowse.datastore import MongoDatastore
from xbrowse.cnv import CNVStore

import os
import pymongo
import imp

#from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator

# django stuff

DEBUG = True
#COMPRESS_ENABLED = False
BASE_URL = '<%= base_url %>'
URL_PREFIX = '/'

GENERATED_FILES_DIR = os.path.join(os.path.dirname(__file__), 'generated_files')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'xbrowsedb',
        'USER': 'xbrowseuser',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '',
    }
}

ALLOWED_HOSTS = ['*']

MEDIA_ROOT = GENERATED_FILES_DIR + '/media/'
STATIC_ROOT = GENERATED_FILES_DIR + '/static_root/'

STATICFILES_DIRS = (
    os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/staticfiles/',
)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


#
# xbrowse stuff
#
COMMON_SNP_FILE = "/vagrant/xbrowse-laptop-downloads/markers.txt"

HGMD_OMIM_FILE = '/vagrant/xbrowse-laptop-downloads/hgmd_omim_genes.txt'

REFERENCE_SETTINGS = imp.load_source(
    'reference_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/reference_settings.py'
)
CUSTOM_ANNOTATOR_SETTINGS = None

ANNOTATOR_SETTINGS = imp.load_source(
    'annotator_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/annotator_settings.py'
)

_conn = pymongo.Connection()
DATASTORE_DB = _conn['xbrowse_datastore']
POPULATION_DATASTORE_DB = _conn['xbrowse_pop_datastore']

DEFAULT_CONTROL_COHORT = 'controls'
CONTROL_COHORTS = [
    {
        'slug': 'controls',
        'vcf': '',
    },
]

COVERAGE_DB = _conn['xbrowse_coverage']

PROJECT_DATASTORE_DB = _conn['xbrowse_proj_store']

CNV_STORE_DB_NAME = 'xbrowse_cnvs'

CUSTOM_POPULATIONS_DB = _conn['xcustom_refpops']

if os.access("/etc/xbrowse_django_secret_key", os.R_OK):
    with open("/etc/xbrowse_django_secret_key") as f:
        SECRET_KEY = f.read().strip()
else:
    raise Exception("Can't access SECRET_KEY file /etc/xbrowse_django_secret_key. This text file needs to exist and "
        "be readable by the web server process. It should contain a string to use for the SECRET_KEY.")
