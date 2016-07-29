import csv
import gzip
import pymongo
import os
from collections import defaultdict
from pymongo import MongoClient


ADMINS = (
    ('Ben Weisburd', 'weisburd@broadinstitute.org'),
    ('Harindra Arachchi', 'harindra@broadinstitute.org'),
)

MANAGERS = ADMINS

TIME_ZONE = 'America/New_York'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True

USE_L10N = True

USE_TZ = True

#STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'
#STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
#STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

STATICFILES_DIRS = (
            os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/staticfiles/',
)

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



MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'xbrowse_server.urls'

WSGI_APPLICATION = 'wsgi.application'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.admin',
    'django.contrib.admindocs',

    'django_extensions',
    'compressor',
    'crispy_forms',

    'xbrowse_server.base.apps.XBrowseBaseConfig',
    'xbrowse_server.api',
    'xbrowse_server.staff',
    'xbrowse_server.gene_lists',
    'xbrowse_server.search_cache',
    'xbrowse_server.phenotips',
    'xbrowse_server.matchmaker',
    
    )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
            'filename': 'django.output.log',
         },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {

         'xbrowse_server': {
             'handlers': ['file'],
             'level': 'INFO',
             'propagate': True,
         },
         'django': {
             'handlers': ['file', 'console'],
             'level': 'INFO',
             'propagate': True,
         },
        'django.request': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

SESSION_COOKIE_NAME = "xsessionid"

AUTH_PROFILE_MODULE = 'base.UserProfile'

LOGGING_DB = MongoClient('localhost', 27017)['logging']
COVERAGE_DB = MongoClient('localhost', 27017)['xbrowse_reference']
EVENTS_COLLECTION = LOGGING_DB.events

UTILS_DB = MongoClient('localhost', 27017)['xbrowse_server_utils']

FROM_EMAIL = "\"xBrowse\" <xbrowse@broadinstitute.org>"

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

PHENOPTIPS_HOST_NAME='http://localhost:9010'
PHENOPTIPS_ALERT_CONTACT='harindra@broadinstitute.org'
_client = MongoClient('localhost', 27017)
_db = _client['phenotips_edit_audit']
PHENOTIPS_EDIT_AUDIT = _db['phenotips_audit_record']
PHENOTIPS_ADMIN_UNAME='Admin'
PHENOTIPS_ADMIN_PWD='admin'

# when set to None, this *disables* the PhenoTips interface for all projects. If set to a list of project ids, it will
# enable the PhenoTips interface for *all* projects except those in the list.
PROJECTS_WITHOUT_PHENOTIPS = None

#-----------------Matchmaker constants-----------------
#####################################
#
#NOTE: MME FEATURES ARE DISABLED
#
#####################################
# when set to None, this *enables* the MME interface for all projects. If set to a list of project ids, it will
# enable the MME interface for *all* projects except those in the list.
PROJECTS_WITHOUT_MATCHMAKER = None
_db = _client['mme_primary']
SEQR_ID_TO_MME_ID_MAP = _db['seqr_id_to_mme_id_map']
GENOME_ASSEMBLY_NAME = 'GRCh37'
#------
#for testing only,fake token, in prod a new token will be put into non-checked-in ini file
MME_NODE_ADMIN_TOKEN=''
#------
MME_NODE_ACCEPT_HEADER='application/vnd.ga4gh.matchmaker.v0.1+json'
MME_CONTENT_TYPE_HEADER='application/x-www-form-urlencoded'
MME_CONTACT_NAME = 'Samantha Baxter'
MME_CONTACT_INSTITUTION = "Joint Center for Mendelian Disease at the Broad Institute"
MME_CONTACT_HREF = "mailto:harindra@broadinstitute.org"
MME_SERVER_HOST='http://localhost:8080'
#MME_SERVER_HOST='http://seqr-aux:8080'
MME_ADD_INDIVIDUAL_URL = MME_SERVER_HOST + '/individual/add'
#matches in local MME database ONLY, won't search in other MME nodes
MME_LOCAL_MATCH_URL = MME_SERVER_HOST + '/match'      
#matches in EXTERNAL MME nodes ONLY, won't search in LOCAL MME database/node
MME_EXTERNAL_MATCH_URL = MME_SERVER_HOST + '/individual/match'

from local_settings import *
#
# These are all settings that require the stuff in local_settings.py
#

ANNOTATOR_REFERENCE_POPULATIONS = ANNOTATOR_SETTINGS.reference_populations
ANNOTATOR_REFERENCE_POPULATION_SLUGS = [pop['slug'] for pop in ANNOTATOR_SETTINGS.reference_populations]

MEDIA_URL = URL_PREFIX + 'media/'

STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')
STATIC_URL = URL_PREFIX + 'static/'

LOGIN_URL = BASE_URL + 'login'

LOGOUT_URL = BASE_URL + 'logout'

CSRF_COOKIE_PATH = URL_PREFIX.rstrip('/')
SESSION_COOKIE_PATH = URL_PREFIX.rstrip('/')

# If supported by the browser, using the HttpOnly flag
# when generating a cookie helps mitigate the risk of client side script accessing the protected cookie. If a browser that supports HttpOnly
# detects a cookie containing the HttpOnly flag, and client side script code attempts to read the cookie, the browser returns an empty
# string as the result. This causes the attack to fail by preventing the malicious (usually XSS) code from sending the data to an attacker's website.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
# SESSION_EXPIRE_AT_BROWSER_CLOSE=True

CLINVAR_VARIANTS = {} # maps (xpos, ref, alt) to a 2-tuple containing (measureset_id, clinical_significance)
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
    #    print("     %5d  %s"  % (pathogenicity_values_counter[k], k))
    # print("%d variants loaded" % len(CLINVAR_VARIANTS))


# set the secret key
if os.access("/etc/xbrowse_django_secret_key", os.R_OK):
    with open("/etc/xbrowse_django_secret_key") as f:
        SECRET_KEY = f.read().strip()

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

else:
    print("Warning: could not access /etc/xbrowse_django_secret_key. Falling back on insecure hard-coded SECRET_KEY")
    SECRET_KEY = "~~~ this key string is FOR DEVELOPMENT USE ONLY ~~~"



