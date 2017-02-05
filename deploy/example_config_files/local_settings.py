import os
import pymongo
import imp


# django stuff
xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
xbrowse_reference_data_dir = os.path.join(xbrowse_install_dir, 'data/reference_data')

DEBUG = True
#COMPRESS_ENABLED = False
BASE_URL = '/'
URL_PREFIX = '/'

GENERATED_FILES_DIR = os.path.join(xbrowse_install_dir, 'generated_files')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(xbrowse_install_dir, 'xbrowse_db.sqlite'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
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

READ_VIZ_BAM_PATH = os.path.join(xbrowse_reference_data_dir, "bams")

CLINVAR_TSV  = os.path.join(xbrowse_reference_data_dir, "clinvar.tsv")

# Email settings
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
