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
    'guardian',
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
    #   django-debug-toolbar
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
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

HIJACK_DISPLAY_WARNING = True
HIJACK_LOGIN_REDIRECT_URL = '/dashboard'

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


PRODUCTION = False

DEBUG = not PRODUCTION


# set the secret key
SECRET_KEY = "~~~ FOR DEVELOPMENT USE ONLY ~~~"

if PRODUCTION:
    with open("/etc/django_secret_key") as f:
        SECRET_KEY = f.read().strip()

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)


PHENOTIPS_HOST = os.environ.get('PHENOTIPS_HOST', 'localhost')
PHENOTIPS_PORT = os.environ.get('PHENOTIPS_PORT', 8080)
PHENOTIPS_SERVER = "%s:%s" % (PHENOTIPS_HOST, PHENOTIPS_PORT)


# =========================================
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

MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
LOGGING_DB = MongoClient(MONGO_HOST, 27017)['logging']
COVERAGE_DB = MongoClient(MONGO_HOST, 27017)['xbrowse_reference']
EVENTS_COLLECTION = LOGGING_DB.events

UTILS_DB = MongoClient(MONGO_HOST, 27017)['xbrowse_server_utils']

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
CLINVAR_TSV = None


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


'''
   Application constants. The password/unames here need to be extracted to a non-checkin file
'''


PHENOPTIPS_HOST_NAME='http://%s:8080' % os.environ.get('PHENOTIPS_HOST', 'localhost')
#PHENOPTIPS_HOST_NAME='http://localhost:9010'
PHENOPTIPS_ALERT_CONTACT='harindra@broadinstitute.org'
_client = MongoClient(MONGO_HOST, 27017)
_db = _client['phenotips_edit_audit']
PHENOTIPS_EDIT_AUDIT = _db['phenotips_audit_record']
PHENOTIPS_ADMIN_UNAME='Admin'
PHENOTIPS_ADMIN_PWD='admin'

# when set to None, this *disables* the PhenoTips interface for all projects. If set to a list of project ids, it will
# enable the PhenoTips interface for *all* projects except those in the list.
PROJECTS_WITHOUT_PHENOTIPS = []




#-----------------Matchmaker constants-----------------

#REQUIRED
#########################################################
# The following setting ONLY controls the matchmaker links
# showing up in the family home page. The API links will 
# work always.
#
# - WHEN set to None, this DISABLES the MME interface for 
#   all projects. 
# - IF set to a list of project ids, it will
#   ENABLE the MME interface for THOSE PROJECTS ONLY
# - IF set to ['ALL'], ENABLES ALL PROJECTS
#########################################################
PROJECTS_WITH_MATCHMAKER = ['1kg']
#REQUIRED
#########################################################
# These names get included with contact person (MME_CONTACT_NAME)
#########################################################
MME_PATIENT_PRIMARY_DATA_OWNER = {
                           "1kg":"PI"
                           }
#########################################################
#NOTE:The name of the PI from MME_PATIENT_PRIMARY_DATA_OWNER 
#will be appended here
MME_CONTACT_NAME = 'Samantha Baxter'
MME_CONTACT_INSTITUTION = "Broad Center for Mendelian Genomics"
MME_CONTACT_HREF = "mailto:matchmaker@broadinstitute.org"
#########################################################
# Activates searching in external MME nodes
#########################################################
SEARCH_IN_EXTERNAL_MME_NODES=True


mme_db = _client['mme_primary']
SEQR_ID_TO_MME_ID_MAP = mme_db['seqr_id_to_mme_id_map']
MME_EXTERNAL_MATCH_REQUEST_LOG = mme_db['match_request_log']
MME_SEARCH_RESULT_ANALYSIS_STATE = mme_db['match_result_analysis_state']
GENOME_ASSEMBLY_NAME = 'GRCh37'
MME_NODE_ADMIN_TOKEN='abcd'
MME_NODE_ACCEPT_HEADER='application/vnd.ga4gh.matchmaker.v1.0+json'
MME_CONTENT_TYPE_HEADER='application/vnd.ga4gh.matchmaker.v1.0+json'
MME_HOST = os.environ.get('MME_HOST', 'seqr-aux')
MME_SERVER_HOST='http://%s:9020' % MME_HOST
#MME_SERVER_HOST='http://localhost:8080'
MME_ADD_INDIVIDUAL_URL = MME_SERVER_HOST + '/patient/add'
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

from local_settings import *
#
# These are all settings that require the stuff in local_settings.py
#

STATICFILES_DIRS = (
    os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/staticfiles/',
    os.path.join(BASE_DIR, 'ui/dist/'),    # this is so django's collectstatic copies ui dist files to STATIC_ROOT
)


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

CLINVAR_VARIANTS = {} # maps (xpos, ref, alt) to a 2-tuple containing (measureset_id, clinical_significance)
try:
    if CLINVAR_TSV and os.path.isfile(CLINVAR_TSV):
        from xbrowse.core.genomeloc import get_xpos
        header = None
        pathogenicity_values_counter = defaultdict(int)
        #print("Reading Clinvar data into memory: " + CLINVAR_TSV)
        for line in open(CLINVAR_TSV):
            line = line.strip()
            if line.startswith("#"):
                continue
            fields = line.split("\t")
            if header is None:
                header = fields
                sys.stderr.write('Clinvar header: %s\n' % ", ".join(fields))
            else:
                line_dict = dict(zip(header, fields))
                chrom = line_dict["chrom"]
                pos = int(line_dict["pos"])
                ref = line_dict["ref"]
                alt = line_dict["alt"]
                if "M" in chrom:
                    continue   # because get_xpos doesn't support chrMT.
                clinical_significance = line_dict["clinical_significance"].lower()
                if clinical_significance in ["not provided", "other", "association"]:
                    continue
                else:
                    for c in clinical_significance.split(";"):
                        pathogenicity_values_counter[c] += 1
                    xpos = get_xpos(chrom, pos)
                    CLINVAR_VARIANTS[(xpos, ref, alt)] = (line_dict["measureset_id"], clinical_significance)
        #for k in sorted(pathogenicity_values_counter.keys(), key=lambda k: -pathogenicity_values_counter[k]):
        #    sys.stderr.write(("     %5d  %s\n"  % (pathogenicity_values_counter[k], k)))
        #sys.stderr.write("%d clinvar variants loaded \n" % len(CLINVAR_VARIANTS))
except Exception as e:
    sys.stderr.write("Error while parsing clinvar: %s\n" % str(e))

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
logger.info("MONGO_HOST: " + MONGO_HOST)
logger.info("PHENOTIPS_HOST: " + PHENOTIPS_HOST)
logger.info("MME_HOST: " + MME_HOST)
