import logging
import os
import sys

logger = logging.getLogger(__name__)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ADMINS = (
    ('Ben Weisburd', 'weisburd@broadinstitute.org'),
    ('Harindra Arachchi', 'harindra@broadinstitute.org'),
)

MANAGERS = ADMINS

# Password validation - https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Application definition

INSTALLED_APPS = [
    'hijack',
    'compat',
    'corsheaders',
    'guardian',
    'anymail',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'seqr',
    'reference_data',
    'breakpoint_search',
    #'structural_variants',
    'crispy_forms',
    # Other django plugins to try from https://djangopackages.org/
    #   django-extensions  (https://django-extensions.readthedocs.io/en/latest/installation_instructions.html)
    #   django-admin-tools
    #   django-model-utils
    #   django-autocomplete-lite     # add autocomplete to admin model
    #   django-admin-honeypot
    #   python-social-auth, or django-allauth
    #   django-registration
    #   django-mailer, django-post_office
    #   django-constance
    #   django-configurations
    #   django-threadedcomments, django-contrib-comments    # create Comment class based on this (https://django-contrib-comments.readthedocs.io/en/latest/quickstart.html)

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# django-hijack plugin
HIJACK_DISPLAY_WARNING = True
HIJACK_LOGIN_REDIRECT_URL = '/dashboard'

CORS_ORIGIN_WHITELIST = (
    'localhost:3000',
    'localhost:8000',
)
CORS_ALLOW_CREDENTIALS = True

# django-debug-toolbar settings
ENABLE_DJANGO_DEBUG_TOOLBAR = True
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INSTALLED_APPS = ['debug_toolbar'] + INSTALLED_APPS
    INTERNAL_IPS = ['127.0.0.1']
    SHOW_COLLAPSED = True
    DEBUG_TOOLBAR_PANELS = [
        'ddt_request_history.panels.request_history.RequestHistoryPanel',
        #'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        #'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        #'debug_toolbar.panels.cache.CachePanel',
        #'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ]
    DEBUG_TOOLBAR_CONFIG = {
        'RESULTS_CACHE_SIZE': 100,
    }


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s: %(message)s     (%(name)s.%(funcName)s:%(lineno)d)',
        },
        'simple': {
            'format': '%(asctime)s %(levelname)s:  %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'INFO',
            'filters': ['require_debug_false'],
            'class': 'logging.FileHandler',
            'filename': 'django.info.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'formatter': 'verbose',
            'propagate': True,
        },
    }
}

ELASTICSEARCH_SERVICE_HOSTNAME = os.environ.get('ELASTICSEARCH_SERVICE_HOSTNAME', 'localhost')
ELASTICSEARCH_PORT = os.environ.get('ELASTICSEARCH_SERVICE_PORT', "9200")
ELASTICSEARCH_SERVER = "%s:%s" % (ELASTICSEARCH_SERVICE_HOSTNAME, ELASTICSEARCH_PORT)

CLOUD_PROVIDER_LOCAL = "local"
CLOUD_PROVIDER_GOOGLE = "google"
CLOUD_PROVIDERS = set([CLOUD_PROVIDER_LOCAL, CLOUD_PROVIDER_GOOGLE])
CLOUD_PROVIDER = os.environ.get('CLOUD_PROVIDER', CLOUD_PROVIDER_LOCAL)
assert CLOUD_PROVIDER in CLOUD_PROVIDERS, "Invalid cloud provider name: %(CLOUD_PROVIDER)s" % locals()

DEPLOYMENT_TYPE_DEV = "dev"
DEPLOYMENT_TYPE_PROD = "prod"
DEPLOYMENT_TYPES = set([DEPLOYMENT_TYPE_DEV, DEPLOYMENT_TYPE_PROD])
DEPLOYMENT_TYPE = os.environ.get("DEPLOYMENT_TYPE", DEPLOYMENT_TYPE_DEV)
assert DEPLOYMENT_TYPE in DEPLOYMENT_TYPES, "Invalid deployment type: %(DEPLOYMENT_TYPE)s" % locals()

USE_GCLOUD_DATAPROC = (CLOUD_PROVIDER == CLOUD_PROVIDER_GOOGLE) and os.environ.get('USE_GCLOUD_DATAPROC', False)
if CLOUD_PROVIDER == CLOUD_PROVIDER_GOOGLE:
    PROJECT_DATA_DIR = "gs://seqr-datasets/"
    REFERENCE_DATA_DIR = "gs://seqr-reference-data/"
else:
    PROJECT_DATA_DIR = "/data/projects/"
    REFERENCE_DATA_DIR = "/data/reference-data/"

GCLOUD_PROJECT = os.environ.get("GCLOUD_PROJECT") or "seqr-project"
GCLOUD_ZONE = os.environ.get("GCLOUD_ZONE") or "us-central1-b"


# set the secret key
if os.path.isfile("/etc/django_secret_key"):
    with open("/etc/django_secret_key") as f:
        SECRET_KEY = f.read().strip()
else:
    SECRET_KEY = os.environ.get("DJANGO_KEY", "-placeholder-key-")

if DEPLOYMENT_TYPE == DEPLOYMENT_TYPE_PROD:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    DEBUG = True

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)


# ===========================================================
# ===========================================================
# legacy settings that need to be reviewed

import csv
import gzip
from collections import defaultdict
from pymongo import MongoClient
import pymongo

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)


#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#    }
#}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.dirname(os.path.realpath(__file__)) + '/ui/dist/',
            os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/templates/',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "xbrowse_server.base.context_processors.custom_processor",
            ],
        },
    },
]




ROOT_URLCONF = 'xbrowse_server.urls'

WSGI_APPLICATION = 'wsgi.application'

INSTALLED_APPS += [
    'compressor',

    'xbrowse_server.base.apps.XBrowseBaseConfig',
    'xbrowse_server.api',
    'xbrowse_server.staff',
    'xbrowse_server.gene_lists',
    'xbrowse_server.search_cache',
    'xbrowse_server.phenotips',
    'xbrowse_server.matchmaker',
]


TEST_RUNNER = 'django.test.runner.DiscoverRunner'

AUTH_PROFILE_MODULE = 'base.UserProfile'

MONGO_SERVICE_HOSTNAME = os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost')
LOGGING_DB = MongoClient(MONGO_SERVICE_HOSTNAME, 27017)['logging']
COVERAGE_DB = MongoClient(MONGO_SERVICE_HOSTNAME, 27017)['xbrowse_reference']
EVENTS_COLLECTION = LOGGING_DB.events

UTILS_DB = MongoClient(MONGO_SERVICE_HOSTNAME, 27017)['xbrowse_server_utils']

FROM_EMAIL = "\"seqr\" <seqr@broadinstitute.org>"

XBROWSE_VERSION = 0.1

DOCS_DIR = os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/user_docs/'

SHELL_PLUS_POST_IMPORTS = (
    ('xbrowse_server.shell_helpers', 'getproj'),
    ('xbrowse_server', 'mall'),
)

FAMILY_LOAD_BATCH_SIZE = 25000

ANNOTATION_BATCH_SIZE = 25000

# defaults for optional local settings
CONSTRUCTION_TEMPLATE = None
CLINVAR_TSV = "/dev/null"

VARIANT_QUERY_RESULTS_LIMIT = 5000

UPLOADED_PEDIGREE_FILE_RECIPIENTS = []
# READ_VIZ

# The base directory where subdirectories contain bams to be shown
# within Variant Search results in an IGV.js view.
# This path can be a local directory or a url to which Django will
# forward the IGV.js http requests.
# The subdirectories under this path should be organized like:
# <project_id1>/<project1_sample_id1>.bam
#               <project1_sample_id1>.bam.bai
#               <project1_sample_id2>.bam
#               <project1_sample_id2>.bam.bai
#               ..
# <project_id2>/<project2_sample_id1>.bam
#               <project2_sample_id1>.bam.bai
#               <project2_sample_id2>.bam
#               <project2_sample_id2>.bam.bai
#               ..
# to xbrowse project ids, and contain
# .bam and .bai files for samples
READ_VIZ_BAM_PATH = ""

READ_VIZ_USERNAME=None   # used to authenticate to remote HTTP bam server
READ_VIZ_PASSWD=None


PHENOTIPS_PORT=os.environ.get('PHENOTIPS_SERVICE_PORT', 8080)
PHENOTIPS_SERVICE_HOSTNAME = os.environ.get('PHENOTIPS_SERVICE_HOSTNAME', 'localhost')
PHENOTIPS_SERVER = "%s:%s" % (PHENOTIPS_SERVICE_HOSTNAME, PHENOTIPS_PORT)
PHENOPTIPS_BASE_URL='http://%s:%s' % (os.environ.get('PHENOTIPS_SERVICE_HOSTNAME', 'localhost'), PHENOTIPS_PORT)
PHENOPTIPS_ALERT_CONTACT='harindra@broadinstitute.org'
_client = MongoClient(MONGO_SERVICE_HOSTNAME, 27017)
_db = _client['phenotips_edit_audit']
PHENOTIPS_EDIT_AUDIT = _db['phenotips_audit_record']
PHENOTIPS_ADMIN_UNAME='Admin'
PHENOTIPS_ADMIN_PWD='admin'
PHENOTIPS_UPLOAD_EXTERNAL_PHENOTYPE_URL="http://"+PHENOTIPS_SERVICE_HOSTNAME+":"+str(PHENOTIPS_PORT)+"/rest/patients/eid"

# when set to None, this *disables* the PhenoTips interface for all projects. If set to a list of project ids, it will
# enable the PhenoTips interface for *all* projects except those in the list.
PROJECTS_WITHOUT_PHENOTIPS = []


REDIS_SERVICE_HOSTNAME = os.environ.get('REDIS_SERVICE_HOST')


#-----------------Matchmaker constants-----------------

#########################################################
MME_DEFAULT_CONTACT_NAME = 'Samantha Baxter'
MME_DEFAULT_CONTACT_INSTITUTION = "Broad Center for Mendelian Genomics"
MME_DEFAULT_CONTACT_HREF = "mailto:matchmaker@broadinstitute.org"

#########################################################
# Activates searching in external MME nodes
#########################################################
SEARCH_IN_EXTERNAL_MME_NODES=True


mme_db = _client['mme_primary']
SEQR_ID_TO_MME_ID_MAP = mme_db['seqr_id_to_mme_id_map']
MME_EXTERNAL_MATCH_REQUEST_LOG = mme_db['match_request_log']
MME_SEARCH_RESULT_ANALYSIS_STATE = mme_db['match_result_analysis_state']
MME_NODE_ADMIN_TOKEN=os.environ.get("MME_NODE_ADMIN_TOKEN", "abcd")
MME_NODE_ACCEPT_HEADER='application/vnd.ga4gh.matchmaker.v1.0+json'
MME_CONTENT_TYPE_HEADER='application/vnd.ga4gh.matchmaker.v1.0+json'
MATCHBOX_SERVICE_HOSTNAME = os.environ.get('MATCHBOX_SERVICE_HOSTNAME', 'localhost')
MME_SERVER_HOST='http://%s:9020' % MATCHBOX_SERVICE_HOSTNAME
#adds a patient to MME
MME_ADD_INDIVIDUAL_URL = MME_SERVER_HOST + '/patient/add'
#deletes a patient from MME
MME_DELETE_INDIVIDUAL_URL = MME_SERVER_HOST + '/patient/delete'
#matches in local MME database ONLY, won't search in other MME nodes
MME_LOCAL_MATCH_URL = MME_SERVER_HOST + '/match'      
#matches in EXTERNAL MME nodes ONLY, won't search in LOCAL MME database/node
MME_EXTERNAL_MATCH_URL = MME_SERVER_HOST + '/match/external'
#privileged/internal metrics URL
MME_MATCHBOX_METRICS_URL= MME_SERVER_HOST + '/metrics'
#Public metrics URL
MME_MATCHBOX_PUBLIC_METRICS_URL= MME_SERVER_HOST + '/metrics/public'
#set this to None if you don't have Slack
MME_SLACK_EVENT_NOTIFICATION_CHANNEL='matchmaker_alerts'
MME_SLACK_MATCH_NOTIFICATION_CHANNEL='matchmaker_matches'
#This is used in slack post to add a link back to project
SEQR_HOSTNAME_FOR_SLACK_POST='https://seqr.broadinstitute.org/project'
#####SLACK integration, assign "None" to this if you do not use slack, otherwise add token here
SLACK_TOKEN=None


PROJECT_IDS_TO_EXCLUDE_FROM_DISCOVERY_SHEET_DOWNLOAD = []


from local_settings import *
#
# These are all settings that require the stuff in local_settings.py
#

STATICFILES_DIRS = (
    os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/staticfiles/',
    os.path.join(BASE_DIR, 'ui/dist/'),    # this is so django's collectstatic copies ui dist files to STATIC_ROOT
)


ANNOTATOR_REFERENCE_POPULATIONS_IN_ELASTICSEARCH = [
    {"slug": "1kg_wgs_phase3", "name": "1000G v3", "has_hom_hemi": False, "full_name": "1000 Genomes Samples", "description": "Filter out variants that have a higher allele count (AC) in the 1000 Genomes Phase 3 release (5/2/2013), or a higher allele frequency (popmax AF) in any one of these five subpopulations defined for 1000 Genomes Phase 3: AFR, AMR, EAS, EUR, SAS"},
    {"slug": "exac_v3", "name": "ExAC v0.3", "has_hom_hemi": True, "full_name": "ExAC", "description": "Filter out variants that have a higher allele count (AC) or homozygous/hemizygous count (H/H) in ExAC, or a higher allele frequency (popmax AF) in any one of these six subpopulations defined for ExAC: AFR, AMR, EAS, FIN, NFE, SAS"},
    {"slug": "gnomad-genomes2", "name": "gnomAD 15k genomes", "has_hom_hemi": True, "description": "Filter out variants that have a higher allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD genomes, or a higher allele frequency (popmax AF) in any one of these six subpopulations defined for gnomAD genomes: AFR, AMR, EAS, FIN, NFE, ASJ"},
    {"slug": "gnomad-exomes2", "name": "gnomAD 123k exomes", "has_hom_hemi": True, "description": "Filter out variants that have a higher allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD genomes, or a higher allele frequency (popmax AF) in any one of these seven subpopulations defined for gnomAD genomes: AFR, AMR, EAS, FIN, NFE, ASJ, SAS"},
    {"slug": "topmed", "name": "TOPMed", "has_hom_hemi": False, "description": "Filter out variants that have a higher allele count (AC), or a higher allele frequency (AF) in TOPMed"},
    {"slug": "AF", "name": "This Callset", "has_hom_hemi": False, "description": ""},
]

ANNOTATOR_REFERENCE_POPULATIONS = ANNOTATOR_SETTINGS.reference_populations
ANNOTATOR_REFERENCE_POPULATION_SLUGS = [pop['slug'] for pop in ANNOTATOR_SETTINGS.reference_populations]

MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')

LOGIN_URL = '/login'

LOGOUT_URL = '/logout'

# If supported by the browser, using the HttpOnly flag
# when generating a cookie helps mitigate the risk of client side script accessing the protected cookie. If a browser that supports HttpOnly
# detects a cookie containing the HttpOnly flag, and client side script code attempts to read the cookie, the browser returns an empty
# string as the result. This causes the attack to fail by preventing the malicious (usually XSS) code from sending the data to an attacker's website.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
# SESSION_EXPIRE_AT_BROWSER_CLOSE=True


if len(sys.argv) >= 2 and sys.argv[1] == 'test':
    # use in-memory sqlite database for running tests
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'seqr_test_db.sqlite',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }


logger.info("Starting seqr...")
logger.info("MONGO_SERVICE_HOSTNAME: " + MONGO_SERVICE_HOSTNAME)
logger.info("PHENOTIPS_SERVICE_HOSTNAME: " + PHENOTIPS_SERVICE_HOSTNAME)
logger.info("MATCHBOX_SERVICE_HOSTNAME: " + MATCHBOX_SERVICE_HOSTNAME)
