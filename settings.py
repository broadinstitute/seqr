import pymongo
import os

ADMINS = (
    ('Brett Thomas', 'brettpthomas@gmail.com'),
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

SECRET_KEY = 'd#!pbr7g&amp;q$2k&amp;*v1*o_hj)-ac1q&amp;g+wbt9i58)c1!)#aq6-*x'

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

SESSION_COOKIE_NAME = "xsessionid"

AUTH_PROFILE_MODULE = 'base.UserProfile'

LOGGING_DB = pymongo.Connection().logging

UTILS_DB = pymongo.Connection().xbrowse_server_utils

FROM_EMAIL = "\"xBrowse\" <xbrowse@atgu.mgh.harvard.edu>"

TEST_RUNNER = 'xbrowse_server.test_runner.XBrowseServerTestRunner'

TEST_DATA_DIR = os.path.dirname(os.path.realpath(__file__)) + '/../test_data_files/'

XBROWSE_VERSION = 0.1

DOCS_DIR = os.path.dirname(os.path.realpath(__file__)) + '/docs/'

SHELL_PLUS_POST_IMPORTS = (
    ('xbrowse_server.shell_helpers', 'getproj'),
    ('xbrowse_server.xbrowse_controls'),
)

FAMILY_LOAD_BATCH_SIZE = 24

ANNOTATION_BATCH_SIZE = 25000

# defaults for optional local settings
CONSTRUCTION_TEMPLATE = None

from local_settings import *

#
# These are all settings that require the stuff in local_settings.py
#

TEMPLATE_DEBUG = DEBUG

MEDIA_URL = URL_PREFIX + 'media/'

STATIC_URL = URL_PREFIX + 'static/'

LOGIN_URL = BASE_URL + 'login'

LOGOUT_URL = BASE_URL + 'logout'

CSRF_COOKIE_PATH = URL_PREFIX.rstrip('/')

SESSION_COOKIE_PATH = URL_PREFIX.rstrip('/')
