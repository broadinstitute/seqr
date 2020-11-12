import logging
import json
import os
import random
import string
import sys

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
    'guardian',
    'anymail',
    'seqr',
    'reference_data',
    'matchmaker',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'seqr.utils.middleware.LogRequestMiddleware',
    'seqr.utils.middleware.JsonErrorMiddleware',
]

ALLOWED_HOSTS = ['*']

CSRF_COOKIE_NAME = 'csrf_token'
CSRF_COOKIE_HTTPONLY = False

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
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
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
        'json_log_formatter': {
            '()': 'seqr.utils.logging_utils.JsonLogFormatter',
        },
    },
    'handlers': {
        'console_json': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json_log_formatter',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        # By default, log to console as json. Gunicorn will forward console logs to kubernetes and stackdriver
        '': {
            'handlers': ['console_json'],
            'level': 'INFO',
            'propagate': True,
        },
        # Disable default server logging since we use custom request logging middlewear
        'django.server': {
            'handlers': ['null'],
            'propagate': False,
        },
        # Log all other django logs to console as json
        'django': {
            'handlers': ['console_json'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console_json'],
            'propagate': False,
        },
    }
}

TERRA_API_ROOT_URL = os.environ.get('TERRA_API_ROOT_URL')

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

if os.environ.get('DEPLOYMENT_TYPE') in {'prod', 'dev'}:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    DEBUG = False
else:
    DEBUG = True
    # Enable CORS and hijak for local development
    INSTALLED_APPS += ['corsheaders', 'hijack']
    MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')
    CORS_ORIGIN_WHITELIST = (
        'http://localhost:3000',
        'http://localhost:8000',
    )
    CORS_ALLOW_CREDENTIALS = True
    CORS_REPLACE_HTTPS_REFERER = True
    # django-hijack plugin
    HIJACK_DISPLAY_WARNING = True
    HIJACK_ALLOW_GET_REQUESTS = True
    HIJACK_LOGIN_REDIRECT_URL = '/'

#########################################################
#  seqr specific settings
#########################################################

SEQR_VERSION = 'v1.0'
SEQR_PRIVACY_VERSION = 1.0
SEQR_TOS_VERSION = 1.0

BASE_URL = os.environ.get("BASE_URL", "/")

SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

AIRTABLE_URL = 'https://api.airtable.com/v0/app3Y97xtbbaOopVR'
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")

UPLOADED_PEDIGREE_FILE_RECIPIENTS = os.environ.get('UPLOADED_PEDIGREE_FILE_RECIPIENTS', '').split(',')

API_LOGIN_REQUIRED_URL = '/api/login-required-error'

# External service settings
ELASTICSEARCH_SERVICE_HOSTNAME = os.environ.get('ELASTICSEARCH_SERVICE_HOSTNAME', 'localhost')
ELASTICSEARCH_SERVICE_PORT = os.environ.get('ELASTICSEARCH_SERVICE_PORT', '9200')
ELASTICSEARCH_SERVER = '{host}:{port}'.format(
    host=ELASTICSEARCH_SERVICE_HOSTNAME, port=ELASTICSEARCH_SERVICE_PORT)

SEQR_ELASTICSEARCH_PASSWORD = os.environ.get('SEQR_ES_PASSWORD')
ELASTICSEARCH_CREDENTIALS = ('seqr', SEQR_ELASTICSEARCH_PASSWORD) if SEQR_ELASTICSEARCH_PASSWORD else None

KIBANA_SERVER = '{host}:{port}'.format(
    host=os.environ.get('KIBANA_SERVICE_HOSTNAME', 'localhost'),
    port=os.environ.get('KIBANA_SERVICE_PORT', 5601)
)
KIBANA_ELASTICSEARCH_PASSWORD = os.environ.get('KIBANA_ES_PASSWORD')

REDIS_SERVICE_HOSTNAME = os.environ.get('REDIS_SERVICE_HOSTNAME', 'localhost')

# Matchmaker
MME_DEFAULT_CONTACT_NAME = 'Samantha Baxter'
MME_DEFAULT_CONTACT_INSTITUTION = 'Broad Center for Mendelian Genomics'
MME_DEFAULT_CONTACT_EMAIL = 'matchmaker@broadinstitute.org'
MME_DEFAULT_CONTACT_HREF = 'mailto:{}'.format(MME_DEFAULT_CONTACT_EMAIL)

MME_CONFIG_DIR = os.environ.get('MME_CONFIG_DIR', '')
MME_NODES = {}
if MME_CONFIG_DIR:
    with open(os.path.join(MME_CONFIG_DIR, 'config.json'), 'r') as f:
        mme_config = json.load(f)
        admin_token = mme_config['adminToken']
        MME_NODES[admin_token] = {'name': MME_DEFAULT_CONTACT_INSTITUTION}
        for node in mme_config['nodes']:
            MME_NODES[node['accessToken']] = node

MME_ACCEPT_HEADER = 'application/vnd.ga4gh.matchmaker.v1.0+json'

MME_SLACK_ALERT_NOTIFICATION_CHANNEL = 'matchmaker_alerts'
MME_SLACK_MATCH_NOTIFICATION_CHANNEL = 'matchmaker_matches'
MME_SLACK_SEQR_MATCH_NOTIFICATION_CHANNEL = 'matchmaker_seqr_match'

#########################################################
#  AnVIL Terra API specific settings
#########################################################
GOOGLE_AUTH_CONFIG_DIR = os.environ.get('GOOGLE_AUTH_CONFIG_DIR', '')

GOOGLE_AUTH_CLIENT_CONFIG = {}
GOOGLE_SERVICE_ACCOUNT_INFO = {}
if GOOGLE_AUTH_CONFIG_DIR:
    with open(os.path.join(GOOGLE_AUTH_CONFIG_DIR, 'client_secret.json'), 'r') as f:
        GOOGLE_AUTH_CLIENT_CONFIG = json.load(f)
    with open(os.path.join(GOOGLE_AUTH_CONFIG_DIR, 'service_account.json'), 'r') as f:
        GOOGLE_SERVICE_ACCOUNT_INFO = json.load(f)

#########################################################
#  Social auth specific settings
#########################################################
SOCIAL_AUTH_GOOGLE_OAUTH2_IGNORE_DEFAULT_SCOPE = True
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/cloud-billing',
    'openid'
]

if TERRA_API_ROOT_URL or (len(sys.argv) >= 2 and sys.argv[1] == 'test'):
    AUTHENTICATION_BACKENDS = ('social_core.backends.google.GoogleOAuth2',) + AUTHENTICATION_BACKENDS

    # Use Google sub ID as the user ID, safer than using email
    USE_UNIQUE_USER_ID = True

    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = GOOGLE_AUTH_CLIENT_CONFIG.get('web', {}).get('client_id')
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = GOOGLE_AUTH_CLIENT_CONFIG.get('web', {}).get('client_secret')

    SOCIAL_AUTH_GOOGLE_PLUS_AUTH_EXTRA_ARGUMENTS = {
          'access_type': 'offline'
    }

    SOCIAL_AUTH_POSTGRES_JSONFIELD = True
    SOCIAL_AUTH_URL_NAMESPACE = 'social'
    SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
    SOCIAL_AUTH_PIPELINE = (
        'seqr.utils.social_auth_pipeline.validate_anvil_registration',
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.social_user',
        'social_core.pipeline.user.get_username',
        'social_core.pipeline.social_auth.associate_by_email',
        'social_core.pipeline.user.create_user',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
        'social_core.pipeline.user.user_details',
    )
    INSTALLED_APPS.append('social_django')
