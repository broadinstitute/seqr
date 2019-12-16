import logging
import json
import os
import random
import string

logger = logging.getLogger(__name__)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#########################################################
#  Django settings
#########################################################

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
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'hijack',
    'corsheaders',
    'guardian',
    'anymail',
    'seqr',
    'reference_data',
    'matchmaker',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'seqr.utils.middleware.JsonErrorMiddleware',
]

# django-hijack plugin
HIJACK_DISPLAY_WARNING = True
HIJACK_LOGIN_REDIRECT_URL = '/'

# cors settings
CORS_ORIGIN_WHITELIST = (
    'localhost:3000',
    'localhost:8000',
)
CORS_ALLOW_CREDENTIALS = True

ALLOWED_HOSTS = ['*']

CSRF_COOKIE_HTTPONLY = True

# django-debug-toolbar settings
ENABLE_DJANGO_DEBUG_TOOLBAR = False
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INSTALLED_APPS = ['debug_toolbar'] + INSTALLED_APPS
    INTERNAL_IPS = ['127.0.0.1']
    SHOW_COLLAPSED = True
    DEBUG_TOOLBAR_PANELS = [
        'ddt_request_history.panels.request_history.RequestHistoryPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
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
STATIC_ROOT = os.path.join(BASE_DIR, 'ui/dist')
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            os.path.join(BASE_DIR, 'ui/dist'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',  # required for admin template
            ],
        },
    },
]

GENERATED_FILES_DIR = os.path.join(os.environ.get('STATIC_MEDIA_DIR', BASE_DIR), 'generated_files')
MEDIA_ROOT = os.path.join(GENERATED_FILES_DIR, 'media/')
MEDIA_URL = '/media/'

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

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# set the secret key
SECRET_FILE = os.path.join(BASE_DIR, 'django_key')
try:
    SECRET_KEY = open(SECRET_FILE).read().strip()
except IOError:
    try:
        SECRET_KEY = ''.join(random.SystemRandom().choice(string.printable) for i in range(50))
        with open(SECRET_FILE, 'w') as f:
            f.write(SECRET_KEY)
    except IOError as e:
        logger.warn('Unable to generate {}: {}'.format(os.path.abspath(SECRET_FILE), e))
        SECRET_KEY = os.environ.get("DJANGO_KEY", "-placeholder-key-")

ROOT_URLCONF = 'seqr.urls'

LOGIN_URL = '/login'
LOGOUT_URL = '/logout'

POSTGRES_DB_CONFIG = {
    'ENGINE': 'django.db.backends.postgresql_psycopg2',
    'HOST': os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'localhost'),
    'PORT': int(os.environ.get('POSTGRES_SERVICE_PORT', '5432')),
    'USER': os.environ.get('POSTGRES_USERNAME', 'postgres'),
    'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
}
DATABASES = {
    'default': dict(NAME='seqrdb', **POSTGRES_DB_CONFIG),
    'reference_data': dict(NAME='reference_data_db', **POSTGRES_DB_CONFIG),
}
DATABASE_ROUTERS = ['reference_data.models.ReferenceDataRouter']

WSGI_APPLICATION = 'wsgi.application'

# Email settings
EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
DEFAULT_FROM_EMAIL = "seqr@broadinstitute.org"

ANYMAIL = {
    "POSTMARK_SERVER_TOKEN": os.environ.get('POSTMARK_SERVER_TOKEN', 'postmark-server-token-placeholder'),
}

if os.environ.get('DEPLOYMENT_TYPE') == 'prod':
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    DEBUG = False
else:
    DEBUG = True


#########################################################
#  seqr specific settings
#########################################################

SEQR_VERSION = 'v1.0'

BASE_URL = os.environ.get("BASE_URL", "/")

SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

UPLOADED_PEDIGREE_FILE_RECIPIENTS = os.environ.get('UPLOADED_PEDIGREE_FILE_RECIPIENTS', '').split(',')

API_LOGIN_REQUIRED_URL = '/api/login-required-error'

# External service settings
ELASTICSEARCH_SERVICE_HOSTNAME = os.environ.get('ELASTICSEARCH_SERVICE_HOSTNAME', 'localhost')
ELASTICSEARCH_SERVER = '{host}:{port}'.format(
    host=ELASTICSEARCH_SERVICE_HOSTNAME, port=os.environ.get('ELASTICSEARCH_SERVICE_PORT', '9200'))

KIBANA_SERVER = '{host}:{port}'.format(
    host=os.environ.get('KIBANA_SERVICE_HOSTNAME', 'localhost'),
    port=os.environ.get('KIBANA_SERVICE_PORT', 5601)
)

PHENOTIPS_SERVER = '{host}:{port}'.format(
    host=os.environ.get('PHENOTIPS_SERVICE_HOSTNAME', 'localhost'),
    port=os.environ.get('PHENOTIPS_SERVICE_PORT', 8080)
)
PHENOTIPS_ADMIN_UNAME = 'Admin'
PHENOTIPS_ADMIN_PWD = 'admin'

REDIS_SERVICE_HOSTNAME = os.environ.get('REDIS_SERVICE_HOSTNAME', 'localhost')

# Matchmaker
MME_SERVER_HOST = 'http://{host}:{port}'.format(
    host=os.environ.get('MATCHBOX_SERVICE_HOSTNAME', 'localhost'),
    port=os.environ.get('MATCHBOX_SERVICE_PORT', 9020)
)
#  TODO remove
MME_ADD_INDIVIDUAL_URL = MME_SERVER_HOST + '/patient/add'
MME_DELETE_INDIVIDUAL_URL = MME_SERVER_HOST + '/patient/delete'
MME_LOCAL_MATCH_URL = MME_SERVER_HOST + '/match'
MME_EXTERNAL_MATCH_URL = MME_SERVER_HOST + '/match/external'
MME_MATCHBOX_METRICS_URL = MME_SERVER_HOST + '/metrics'
MME_MATCHBOX_PUBLIC_METRICS_URL = MME_SERVER_HOST + '/metrics/public'

MME_DEFAULT_CONTACT_NAME = 'Samantha Baxter'
MME_DEFAULT_CONTACT_INSTITUTION = 'Broad Center for Mendelian Genomics'
MME_DEFAULT_CONTACT_EMAIL = 'matchmaker@broadinstitute.org'
MME_DEFAULT_CONTACT_HREF = 'mailto:{}'.format(MME_DEFAULT_CONTACT_EMAIL)

MME_NODES_CONFIG_FILE_PATH = os.environ.get('MME_NODES_CONFIG_FILE_PATH', '')
MME_NODES = {}
MME_NODE_ADMIN_TOKEN = "abcd"
if MME_NODES_CONFIG_FILE_PATH:
    with open(os.path.join(BASE_DIR, MME_NODES_CONFIG_FILE_PATH), 'r') as f:
        mme_config = json.load(f)
        MME_NODE_ADMIN_TOKEN = mme_config['adminToken']
        MME_NODES[MME_NODE_ADMIN_TOKEN] = {'name': MME_DEFAULT_CONTACT_INSTITUTION}
        for node in mme_config['nodes']:
            MME_NODES[node['accessToken']] = node

MME_ACCEPT_HEADER = 'application/vnd.ga4gh.matchmaker.v1.0+json'

MME_SLACK_EVENT_NOTIFICATION_CHANNEL = 'matchmaker_alerts'
MME_SLACK_MATCH_NOTIFICATION_CHANNEL = 'matchmaker_matches'
MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL = 'matchmaker_seqr_match'

# Readviz
READ_VIZ_BAM_PATH = 'https://broad-seqr'
READ_VIZ_CRAM_PATH = 'broad-seqr:5000'
