import os
import pymongo
import imp


# django stuff
reference_data_dir = '../data/reference_data'

DEBUG = True
#COMPRESS_ENABLED = False
BASE_URL = '/'
URL_PREFIX = '/'

GENERATED_FILES_DIR = './generated_files'

MEDIA_ROOT = GENERATED_FILES_DIR + '/media/'

"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
"""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seqrdb',
        'USER': 'seqr',
        'PASSWORD': 'seqr',
        'HOST': 'localhost',
        'PORT': '',
    }
}


ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


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
DATASTORE_DB = _conn['datastore']
POPULATION_DATASTORE_DB = _conn['pop_datastore']

DEFAULT_CONTROL_COHORT = 'controls'
CONTROL_COHORTS = [
    {
        'slug': 'controls',
        'vcf': '',
    },
]

COVERAGE_DB = _conn['coverage']

PROJECT_DATASTORE_DB = _conn['proj_store']

CNV_STORE_DB_NAME = 'cnvs'

CUSTOM_POPULATIONS_DB = _conn['xcustom_refpops']

READ_VIZ_BAM_PATH = os.path.join(reference_data_dir, "bams")

CLINVAR_TSV  = os.path.join(reference_data_dir, "clinvar.tsv")

# Email settings
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
