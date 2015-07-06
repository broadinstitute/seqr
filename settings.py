import csv
import gzip
import pymongo
import os
from collections import defaultdict

ADMINS = (
    ('Brett Thomas', 'brettpthomas@gmail.com'),
    ('Ben Weisburd', 'weisburd@broadinstitute.org'),
)

MANAGERS = ADMINS

TIME_ZONE = 'America/New_York'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)


TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'xbrowse_server.urls'

WSGI_APPLICATION = 'wsgi.application'

TEMPLATE_DIRS = (
    os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/templates/',
)

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

    'datasets',

    'xbrowse_server.base.apps.XBrowseBaseConfig',
    'xbrowse_server.api', 
    'xbrowse_server.staff',
    'xbrowse_server.gene_lists',
    'xbrowse_server.search_cache',

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
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'xbrowse_server': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages", 

    "xbrowse_server.base.context_processors.custom_processor",
)

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

SESSION_COOKIE_NAME = "xsessionid"

AUTH_PROFILE_MODULE = 'base.UserProfile'

LOGGING_DB = pymongo.Connection().logging

UTILS_DB = pymongo.Connection().xbrowse_server_utils

FROM_EMAIL = "\"xBrowse\" <xbrowse@broadinstitute.org>"

XBROWSE_VERSION = 0.1

DOCS_DIR = os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/user_docs/'

SHELL_PLUS_POST_IMPORTS = (
    ('xbrowse_server.shell_helpers', 'getproj'),
    ('xbrowse_server', 'mall'),
)

FAMILY_LOAD_BATCH_SIZE = 100000

ANNOTATION_BATCH_SIZE = 25000

# defaults for optional local settings
CONSTRUCTION_TEMPLATE = None
CLINVAR_TSV = None

from local_settings import *
#
# These are all settings that require the stuff in local_settings.py
#

ANNOTATOR_REFERENCE_POPULATIONS = ANNOTATOR_SETTINGS.reference_populations
ANNOTATOR_REFERENCE_POPULATION_SLUGS = [pop['slug'] for pop in ANNOTATOR_SETTINGS.reference_populations]

TEMPLATE_DEBUG = DEBUG

MEDIA_URL = URL_PREFIX + 'media/'

STATIC_URL = URL_PREFIX + 'static/'

LOGIN_URL = BASE_URL + 'login'

LOGOUT_URL = BASE_URL + 'logout'

CSRF_COOKIE_PATH = URL_PREFIX.rstrip('/')

SESSION_COOKIE_PATH = URL_PREFIX.rstrip('/')

CLINVAR_VARIANTS = {} # maps (xpos, ref, alt) to a 2-tuple containing (measureset_id, clinical_significance)
if CLINVAR_TSV and os.path.isfile(CLINVAR_TSV):
    from xbrowse.core.genomeloc import get_xpos
    header = None
    pathogenicity_values_counter = defaultdict(int)
    print("Reading Clinvar data into memory: " + CLINVAR_TSV)
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
    for k in sorted(pathogenicity_values_counter.keys(), key=lambda k: -pathogenicity_values_counter[k]):
        print("     %5d  %s"  % (pathogenicity_values_counter[k], k))

# set the secret key
if os.access("/etc/xbrowse_django_secret_key", os.R_OK):
    with open("/etc/xbrowse_django_secret_key") as f:
        SECRET_KEY = f.read().strip()
else:
    print("Warning: could not access /etc/xbrowse_django_secret_key. Falling back on insecure hard-coded SECRET_KEY")
    SECRET_KEY = "~~~ this key string is FOR DEVELOPMENT USE ONLY ~~~"




