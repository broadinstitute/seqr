import os
import pymongo
import imp

#from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator

# django stuff

DEBUG = True
#COMPRESS_ENABLED = False
BASE_URL = '/'
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
    '<%= xbrowse_repo_dir =>/xbrowse_server/staticfiles/',
)


#
# xbrowse stuff
#

REFERENCE_SETTINGS = imp.load_source(
    'reference_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/reference_settings.py'
)

CUSTOM_ANNOTATOR_SETTINGS = imp.load_source(
    'custom_annotation_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/custom_annotator_settings.py'
)

ANNOTATOR_SETTINGS = imp.load_source(
    'annotator_settings',
    os.path.dirname(os.path.realpath(__file__)) + '/annotator_settings.py'
)

_conn = pymongo.MongoClient()
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



