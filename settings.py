
from local_settings import *

import sys
import os
import pymongo

from xbrowse import utils as xbrowse_utils

TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Brett Thomas', 'brettpthomas@gmail.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = URL_PREFIX + 'media/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = URL_PREFIX + 'static/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'd#!pbr7g&amp;q$2k&amp;*v1*o_hj)-ac1q&amp;g+wbt9i58)c1!)#aq6-*x'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'xbrowse_server.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'xbrowse_server.wsgi.application'

TEMPLATE_DIRS = (
    os.path.dirname(os.path.realpath(__file__)) + '/xbrowse_server/templates/'
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.admin',
    'django.contrib.admindocs',

    'south', 
    'django_extensions',
    'compressor',

    'datasets',

    'xbrowse_server.base', 
    'xbrowse_server.api', 
    'xbrowse_server.staff',
    'xbrowse_server.gene_lists',
    'xbrowse_server.search_cache',

    )

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
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

LOGIN_URL = BASE_URL + 'login'
LOGOUT_URL = BASE_URL + 'logout'

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

CSRF_COOKIE_PATH = URL_PREFIX.rstrip('/')
SESSION_COOKIE_PATH = URL_PREFIX.rstrip('/')
SESSION_COOKIE_NAME = "xsessionid"

TESTMEDIA = os.path.dirname(os.path.realpath(__file__)) + '/../testmedia/'

AUTH_PROFILE_MODULE = 'base.UserProfile'

LOGGING_DB = pymongo.Connection().logging
UTILS_DB = pymongo.Connection().xbrowse_server_utils

FROM_EMAIL = "\"xBrowse\" <xbrowse@atgu.mgh.harvard.edu>"

TEST_RUNNER = 'xbrowse_server.test_runner.XBrowseServerTestRunner'

TEST_DATA_DIR = os.path.dirname(os.path.realpath(__file__)) + '/../test_data_files/'

XBROWSE_VERSION = 0.1
XBROWSE_REFERENCE_POPULATIONS = ['esp_ea', 'esp_aa', 'atgu_controls', 'g1k_all']

DOCS_DIR = os.path.dirname(os.path.realpath(__file__)) + '/docs/'

SHELL_PLUS_POST_IMPORTS = (
    ('xbrowse_server.shell_helpers', 'getproj'),
)

FAMILY_LOAD_BATCH_SIZE = 24

ANNOTATION_BATCH_SIZE = 25000

DEFAULT_REFERENCE_POPULATIONS = [
    {'slug': 'esp_ea', 'name': 'ESP Europeans'},
    {'slug': 'esp_aa', 'name': 'ESP AF/AM'},
    {'slug': 'g1k_all', 'name': '1000 Genomes'},
    {'slug': 'atgu_controls', 'name': 'ATGU Controls'},
]
