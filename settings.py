import csv
import gzip
import pymongo
import os
from collections import defaultdict
from pymongo import MongoClient

#global database settings
#Load ini files
import ConfigParser
config = ConfigParser.SafeConfigParser()
config.read(['config/seqr.ini.sample','config/phenotips.ini.sample','config/seqr.ini','config/phenotips.ini'])

#######################################################
##>>>>> General
#######################################################
SEQR_VERSION = 0.1


#######################################################
##>>>>> DB configuration
#######################################################

DB_HOST = config.get('database','host')
DB_PORT = config.get('database','port')
DB_REPLICA = config.get('database','replicaset')
DB_USER = config.get('database','user')
DB_PASS = config.get('database','password')
seqr_db_connect='mongodb://'
if DB_USER != '':
    seqr_db_connect+='%s:%s@%s:%s'%(DB_USER,DB_PASS,DB_HOST,DB_PORT)
else:
    seqr_db_connect+='%s:%s'%(DB_HOST,DB_PORT)
if DB_REPLICA != '':
    seqr_db_connect+='/?replicaSet=%s'%(DB_REPLICA)
SEQR_DBCONN = MongoClient(seqr_db_connect)

#######################################################
##>>>>> PhenoTips configuration
#######################################################

PHENOPTIPS_HOST_NAME=config.get('phenotips','phenotips_host_name')
PHENOTIPS_ADMIN_UNAME= config.get('phenotips','phenotips_host_name')
PHENOTIPS_ADMIN_PWD= config.get('phenotips','phenotips_host_name')
PHENOPTIPS_ALERT_CONTACT=config.get('phenotips','alert_contact')
PHENOTIPS_DB_HOST = config.get('database','host')
PHENOTIPS_DB_PORT = config.get('database','port')
PHENOTIPS_DB_REPLICA = config.get('database','replicaset')
PHENOTIPS_DB_USER = config.get('database','user')
PHENOTIPS_DB_PASS = config.get('database','password')
phenotips_db_connect='mongodb://'
if PHENOTIPS_DB_USER != "":
    phenotips_db_connect+='%s:%s@%s:%s'%(PHENOTIPS_DB_USER,PHENOTIPS_DB_PASS,PHENOTIPS_DB_HOST,PHENOTIPS_DB_PORT)
else:
    phenotips_db_connect+='%s:%s'%(PHENOTIPS_DB_HOST,PHENOTIPS_DB_PORT)
if DB_REPLICA != "":
    phenotips_db_connect+='/?replicaSet=%s'%(PHENOTIPS_DB_REPLICA)
PHENOTIPS_DBCONN = MongoClient(phenotips_db_connect)
PHENOTIPS_EDIT_AUDIT = PHENOTIPS_DBCONN['phenotips_audit_record']
    # when set to None, this *disables* the PhenoTips interface for all projects. If set to a list of project ids, it will
    # enable the PhenoTips interface for *all* projects except those in the list.
PROJECTS_WITHOUT_PHENOTIPS = None

#######################################################
##>>>>> DB connections
#######################################################
    #seqr db
COVERAGE_DB = SEQR_DBCONN['xbrowse_coverage']
CUSTOM_POPULATIONS_DB = SEQR_DBCONN['xcustom_refpops']
DATASTORE_DB = SEQR_DBCONN['xbrowse_datastore']
LOGGING_DB = SEQR_DBCONN['logging']
POPULATION_DATASTORE_DB = SEQR_DBCONN['xbrowse_pop_datastore']
PROJECT_DATASTORE_DB = SEQR_DBCONN['xbrowse_proj_store']
UTILS_DB = SEQR_DBCONN['xbrowse_server_utils']
XBROWSE_REFERENCE_DB = SEQR_DBCONN['xbrowse_reference']
XBROWSE_ANNOTATOR_DB = SEQR_DBCONN['xbrowse_annotator']
XBROWSE_CUSTOM_ANNOTATOR_DB = SEQR_DBCONN['x_custom_annots']
XBROWSE_CNV_DB = SEQR_DBCONN['xbrowse_cnvs']
XBROWSE_COVERAGE_STORE = SEQR_DBCONN['']

#######################################################
##>>>>> visualization
#######################################################

READ_VIZ_BAM_PATH = config.get('visualization','viz_bam_path')
READ_VIZ_USERNAME= config.get('visualization','viz_user')   # used to authenticate to remote HTTP bam server
READ_VIZ_PASSWD= config.get('visualization','viz_pass')

#######################################################
##>>>>> Users and notification
#######################################################

ADMINS = (
    ('Ben Weisburd', 'weisburd@broadinstitute.org'),
    ('Harindra Arachchi', 'harindra@broadinstitute.org'),
)
FROM_EMAIL = "\"xBrowse\" <xbrowse@broadinstitute.org>"

#######################################################
##>>>>> Django Settings
#######################################################

MANAGERS = ADMINS
TIME_ZONE = 'America/New_York'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True

#static
STATICFILES_DIRS = (
            os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/staticfiles/',
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
#templates
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
#middleware
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

    # URLs
ROOT_URLCONF = 'xbrowse_server.urls'
BASE_URL = '/'
URL_PREFIX = '/'
MEDIA_URL = URL_PREFIX + 'media/'
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')
STATIC_URL = URL_PREFIX + 'static/'
LOGIN_URL = BASE_URL + 'login'
LOGOUT_URL = BASE_URL + 'logout'


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

    )
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
SESSION_COOKIE_NAME = "xsessionid"
AUTH_PROFILE_MODULE = 'base.UserProfile'
DOCS_DIR = os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/user_docs/'
SHELL_PLUS_POST_IMPORTS = (
    ('xbrowse_server.shell_helpers', 'getproj'),
    ('xbrowse_server', 'mall'),
)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'xbrowse_db.sqlite'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
ALLOWED_HOSTS = ['*']
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#######################################################
##>>>>> seqr specifics
#######################################################
from local_settings import *

ANNOTATOR_REFERENCE_POPULATIONS = ANNOTATOR_SETTINGS.reference_populations
ANNOTATOR_REFERENCE_POPULATION_SLUGS = [pop['slug'] for pop in ANNOTATOR_SETTINGS.reference_populations]

FAMILY_LOAD_BATCH_SIZE = 25000
ANNOTATION_BATCH_SIZE = 25000
# defaults for optional local settings
CONSTRUCTION_TEMPLATE = None
CLINVAR_TSV = None

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

#######################################################
##>>>>> logging
#######################################################

DEBUG = True
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

#######################################################
##>>>>> Cookies and security
#######################################################

CSRF_COOKIE_PATH = URL_PREFIX.rstrip('/')
SESSION_COOKIE_PATH = URL_PREFIX.rstrip('/')

# If supported by the browser, using the HttpOnly flag
# when generating a cookie helps mitigate the risk of client side script accessing the protected cookie. If a browser that supports HttpOnly
# detects a cookie containing the HttpOnly flag, and client side script code attempts to read the cookie, the browser returns an empty
# string as the result. This causes the attack to fail by preventing the malicious (usually XSS) code from sending the data to an attacker's website.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
# SESSION_EXPIRE_AT_BROWSER_CLOSE=True

# set the secret key
if os.access("/etc/xbrowse_django_secret_key", os.R_OK):
    with open("/etc/xbrowse_django_secret_key") as f:
        SECRET_KEY = f.read().strip()

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

else:
    SECRET_KEY = "~~~ this key string is FOR DEVELOPMENT USE ONLY ~~~"



