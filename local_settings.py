import os
import pymongo
import imp


# django stuff
install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
reference_data_dir = os.path.join(install_dir, 'data/reference_data')

DEBUG = True
#COMPRESS_ENABLED = False
BASE_URL = '/'
URL_PREFIX = '/'

GENERATED_FILES_DIR = os.path.join(os.path.dirname(__file__), 'generated_files')


"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(install_dir, 'seqrdb.sqlite'),
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
        #'USER': 'postgres',
        #'PASSWORD': '',
        #'HOST': 'localhost',
        'PORT': '',
    }
}

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


SLACK_TOKEN = ''

PROJECTS_WITH_MATCHMAKER = []


MME_PATIENT_PRIMARY_DATA_OWNER = {}




PROJECTS_WITHOUT_PHENOTIPS = {}


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

READ_VIZ_BAM_PATH = os.path.join(reference_data_dir, "bams")

CLINVAR_TSV  = os.path.join(reference_data_dir, "clinvar.tsv")


MEDIA_ROOT = os.path.abspath(GENERATED_FILES_DIR + "/media/")


# Email settings
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
