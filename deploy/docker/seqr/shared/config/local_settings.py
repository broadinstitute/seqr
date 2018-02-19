import os
import pymongo
import imp


# django stuff
reference_data_dir = '../data/reference_data'

#DEBUG = True
#COMPRESS_ENABLED = False
BASE_URL = '/'
URL_PREFIX = '/'

GENERATED_FILES_DIR = os.path.join(os.path.dirname(__file__), 'generated_files')
MEDIA_ROOT = os.path.join(GENERATED_FILES_DIR , 'media/')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'localhost'),
        'PORT': int(os.environ.get('POSTGRES_SERVICE_PORT', '5432')),
        'NAME': 'seqrdb',
        'USER': os.environ.get('POSTGRES_USERNAME', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
    }
}

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
DEFAULT_FROM_EMAIL = "seqr@broadinstitute.org"

ANYMAIL = {
    #"SENDGRID_API_KEY": os.environ.get('SENDGRID_API_KEY', 'sendgrid-api-key-placeholder'),
    "POSTMARK_SERVER_TOKEN": os.environ.get('POSTMARK_SERVER_TOKEN', 'postmark-server-token-placeholder'),
}

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

_conn = pymongo.MongoClient(host=os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost'))
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

COVERAGE_DB = _conn['coverage']

READ_VIZ_BAM_PATH = 'https://broad-seqr'
READ_VIZ_CRAM_PATH = 'broad-seqr:5000'

READ_VIZ_USERNAME = "xbrowse-bams"
READ_VIZ_PASSWD = "xbrowse-bams"

CLINVAR_TSV  = os.path.join(reference_data_dir, "clinvar.tsv")


