import json
import os
import random
import string
import subprocess  # nosec

from ssl import create_default_context

import google.auth
import google.auth.transport.requests

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#########################################################
#  Django settings
#########################################################

# Password validation - https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators
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
    'admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'guardian',
    'anymail',
    'clickhouse_backend',
    'notifications',
    'seqr',
    'reference_data',
    'clickhouse_search',
    'matchmaker',
    'social_django',
    'panelapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'seqr.utils.middleware.CacheControlMiddleware',
    'seqr.utils.middleware.LogRequestMiddleware',
    'seqr.utils.middleware.JsonErrorMiddleware',
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

ALLOWED_HOSTS = ['*']

CSRF_COOKIE_NAME = 'csrf_token'
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_AGE = 86400  # seconds in 1 day
X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_BROWSER_XSS_FILTER = True

CSP_INCLUDE_NONCE_IN = ['script-src', 'style-src', 'style-src-elem']
CSP_FONT_SRC = ('https://fonts.gstatic.com', 'data:', "'self'")
CSP_CONNECT_SRC = ("'self'", 'https://gtexportal.org', 'https://www.google-analytics.com', 'https://igv.org',
                   'https://storage.googleapis.com', 'https://s3.amazonaws.com', 'https://igv-genepattern-org.s3.amazonaws.com', 'https://hgdownload.soe.ucsc.edu',  # used by IGV
                   'https://reg.genome.network')
CSP_SCRIPT_SRC = ("'self'", "'unsafe-eval'", 'https://www.googletagmanager.com',
                  "'sha256-A16xkExeIj9J9P70pOQ+HDBXdFYcm2Cn3J/phdqk9hc='")  # luigi UI script
CSP_IMG_SRC = ("'self'", 'https://www.google-analytics.com', 'https://storage.googleapis.com',
   'https://user-images.githubusercontent.com', 'https://private-user-images.githubusercontent.com', # for images in GitHub discussions on Feature Updates page
   'data:')
CSP_OBJECT_SRC = ("'none'")
CSP_BASE_URI = ("'none'")
# IGV js injects CSS into the page head so there is no way to set nonce. Therefore, support hashed value of the CSS
IGV_CSS_HASHES = (
    "'sha256-dUpUK4yXR60CNDI/4ZeR/kpSqQ3HmniKj/Z7Hw9ZNTA='",
    "'sha256-s8l0U2/BsebhfOvm08Z+4w1MnftmnPeoOMbSi+f5hCI='",
    "'sha256-T9widob1zmlNnk3NzLRUfXFToG7AkPTuLDXaKU2tc6c='",
    "'sha256-ITHmamcImsZ/Je1xrdtDLZVvRSpj1Zokb6uHXORB824='",
)
CSP_STYLE_SRC = ('https://fonts.googleapis.com', "'self'") + IGV_CSS_HASHES
CSP_STYLE_SRC_ELEM = ('https://fonts.googleapis.com', "'self'") + IGV_CSS_HASHES

# django-debug-toolbar settings
ENABLE_DJANGO_DEBUG_TOOLBAR = False
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INSTALLED_APPS = ['debug_toolbar'] + INSTALLED_APPS
    INTERNAL_IPS = ['127.0.0.1']
    SHOW_COLLAPSED = True
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.history.HistoryPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
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
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STATIC_URL = '/static/'
STATICFILES_DIRS = ['ui/dist']
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}
}

# If specified, store data in the named GCS bucket and use the gcloud storage backend.
# Else, fall back to a path on the local filesystem.
GCS_MEDIA_ROOT_BUCKET = os.environ.get('GCS_MEDIA_ROOT_BUCKET')
if GCS_MEDIA_ROOT_BUCKET:
    STORAGES['default'] = {'BACKEND': 'storages.backends.gcloud.GoogleCloudStorage'}
    GS_BUCKET_NAME = GCS_MEDIA_ROOT_BUCKET
    GS_DEFAULT_ACL = 'publicRead'
    MEDIA_ROOT = False
    MEDIA_URL = 'https://storage.googleapis.com/{bucket_name}/'.format(bucket_name=GS_BUCKET_NAME)
else:
    GENERATED_FILES_DIR = os.path.join(os.environ.get('STATIC_MEDIA_DIR', BASE_DIR), 'generated_files')
    MEDIA_ROOT = os.path.join(GENERATED_FILES_DIR, 'media/')
    MEDIA_URL = '/media/'

LOADING_DATASETS_DIR = os.environ.get('LOADING_DATASETS_DIR')
PIPELINE_DATA_DIR = os.environ.get('PIPELINE_DATA_DIR')

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
ANVIL_UI_URL = 'https://anvil.terra.bio/'

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.azuread_tenant.AzureADV2TenantOAuth2',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# set the secret key
SECRET_KEY = os.environ.get('DJANGO_KEY')
if not SECRET_KEY:
    SECRET_FILE = os.path.join(BASE_DIR, 'django_key')
    try:
        with open(SECRET_FILE) as f:
            SECRET_KEY = f.read().strip()
    except IOError:
        SECRET_KEY = ''.join(random.SystemRandom().choice(string.printable) for i in range(50))
        with open(SECRET_FILE, 'w') as f:
            f.write(SECRET_KEY)

ROOT_URLCONF = 'seqr.urls'

LOGOUT_URL = '/logout'

POSTGRES_DB_CONFIG = {
    'ENGINE': 'django.db.backends.postgresql',
    'HOST': os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'localhost'),
    'PORT': int(os.environ.get('POSTGRES_SERVICE_PORT', '5432')),
    'USER': os.environ.get('POSTGRES_USERNAME', 'postgres'),
    'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'pgtest'),
}
DATABASES = {
    'default': dict(NAME='seqrdb', **POSTGRES_DB_CONFIG),
    'reference_data': dict(NAME='reference_data_db', **POSTGRES_DB_CONFIG),
}
DATABASE_ROUTERS = ['reference_data.models.ReferenceDataRouter', 'clickhouse_search.models.ClickHouseRouter']

CLICKHOUSE_IN_MEMORY_DIR = os.environ.get('CLICKHOUSE_IN_MEMORY_DIR', '/in-memory-dir')
CLICKHOUSE_DATA_DIR = os.getenv('CLICKHOUSE_DATA_DIR', '/var/seqr/clickhouse-data')
CLICKHOUSE_SERVICE_HOSTNAME =  os.environ.get('CLICKHOUSE_SERVICE_HOSTNAME')
if CLICKHOUSE_SERVICE_HOSTNAME:
    DATABASES['clickhouse_write'] = {
        'ENGINE': 'clickhouse_search.backend',
        'NAME': 'seqr',
        'HOST': CLICKHOUSE_SERVICE_HOSTNAME,
        'PORT': int(os.environ.get('CLICKHOUSE_SERVICE_PORT', '9000')),
        'USER': os.environ.get('CLICKHOUSE_WRITER_USER', 'clickhouse'),
        'PASSWORD': os.environ.get('CLICKHOUSE_WRITER_PASSWORD', 'clickhouse_test'),
        'OPTIONS': {
            'settings': {
                'use_client_time_zone': False,
            }
        },
    }
    DATABASES['clickhouse'] = {
        **DATABASES['clickhouse_write'],
        'USER': os.environ.get('CLICKHOUSE_READER_USER', 'clickhouse'),
        'PASSWORD': os.environ.get('CLICKHOUSE_READER_PASSWORD', 'clickhouse_test'),
    }

TEST_RUNNER = "seqr.testrunner.OrderedDatabaseDeletionRunner"

WSGI_APPLICATION = 'wsgi.application'

WHITENOISE_ALLOW_ALL_ORIGINS = False

# Email settings
EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
DEFAULT_FROM_EMAIL = "seqr@broadinstitute.org"

ANYMAIL = {
    "POSTMARK_SERVER_TOKEN": os.environ.get('POSTMARK_SERVER_TOKEN', 'postmark-server-token-placeholder'),
}

TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, 'ui/dist'),
]

DEPLOYMENT_TYPE = os.environ.get('DEPLOYMENT_TYPE')
BASE_URL = os.environ.get("BASE_URL", "/")
if DEPLOYMENT_TYPE in {'prod', 'dev'}:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = [BASE_URL.rstrip('/')]
    DEBUG = False
else:
    DEBUG = True
    # Enable CORS and hijak for local development
    INSTALLED_APPS += ['corsheaders', 'hijack']
    MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')
    MIDDLEWARE.append('hijack.middleware.HijackUserMiddleware')
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
    TEMPLATE_DIRS.append('ui')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': TEMPLATE_DIRS,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',  # required for admin template
                'django.template.context_processors.request',  # must be enabled in DjangoTemplates (TEMPLATES) in order to use the admin navigation sidebar
                'social_django.context_processors.backends',  # required for social_auth, same for below
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

#########################################################
#  seqr specific settings
#########################################################

SEQR_VERSION = 'v1.0'
SEQR_PRIVACY_VERSION = float(os.environ.get('SEQR_PRIVACY_VERSION', 1.1))
SEQR_TOS_VERSION = float(os.environ.get('SEQR_TOS_VERSION', 1.2))

GA_TOKEN_ID = os.environ.get("GA_TOKEN_ID")

SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

AIRTABLE_URL = 'https://api.airtable.com/v0'
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")

GREGOR_DATA_MODEL_URL = os.environ.get('GREGOR_DATA_MODEL_URL', 'https://raw.githubusercontent.com/UW-GAC/gregor_data_models/main/GREGoR_data_model.json')

API_LOGIN_REQUIRED_URL = '/api/login-required-error'
API_POLICY_REQUIRED_URL = '/api/policy-required-error'
POLICY_REQUIRED_URL = '/accept_policies'

INTERNAL_NAMESPACES = os.environ.get('INTERNAL_NAMESPACES', '').split(',')
ANALYST_USER_GROUP = os.environ.get('ANALYST_USER_GROUP')
PM_USER_GROUP = os.environ.get('PM_USER_GROUP')

IS_ANVIL_LOADING_DELAY = bool(os.environ.get('IS_ANVIL_LOADING_DELAY'))

# External service settings
ELASTICSEARCH_SERVICE_HOSTNAME = os.environ.get('ELASTICSEARCH_SERVICE_HOSTNAME')
ELASTICSEARCH_SERVICE_PORT = os.environ.get('ELASTICSEARCH_SERVICE_PORT', '9200')
ELASTICSEARCH_SERVER = '{host}:{port}'.format(
    host=ELASTICSEARCH_SERVICE_HOSTNAME, port=ELASTICSEARCH_SERVICE_PORT)

SEQR_ELASTICSEARCH_PASSWORD = os.environ.get('SEQR_ES_PASSWORD')
ELASTICSEARCH_USER = os.environ.get('ELASTICSEARCH_USER', 'seqr')
ELASTICSEARCH_CREDENTIALS = (ELASTICSEARCH_USER, SEQR_ELASTICSEARCH_PASSWORD) if SEQR_ELASTICSEARCH_PASSWORD else None
ELASTICSEARCH_PROTOCOL = os.environ.get('ELASTICSEARCH_PROTOCOL', 'http')
ELASTICSEARCH_CA_PATH = os.environ.get('ELASTICSEARCH_CA_PATH')
# if we have a custom CA certificate for elasticsearch, add it to the verification path for connections
if ELASTICSEARCH_CA_PATH:
    ES_SSL_CONTEXT = create_default_context(cafile=ELASTICSEARCH_CA_PATH)
else:
    ES_SSL_CONTEXT = None

KIBANA_SERVER = '{host}:{port}'.format(
    host=os.environ.get('KIBANA_SERVICE_HOSTNAME', 'localhost'),
    port=os.environ.get('KIBANA_SERVICE_PORT', 5601)
)
KIBANA_ELASTICSEARCH_USER = os.environ.get('KIBANA_ELASTICSEARCH_USER', 'kibana')
KIBANA_ELASTICSEARCH_PASSWORD = os.environ.get('KIBANA_ES_PASSWORD')

REDIS_SERVICE_HOSTNAME = os.environ.get('REDIS_SERVICE_HOSTNAME', 'localhost')
REDIS_SERVICE_PORT = int(os.environ.get('REDIS_SERVICE_PORT', '6379'))

PIPELINE_RUNNER_HOSTNAME = os.environ.get('PIPELINE_RUNNER_HOSTNAME', 'pipeline-runner')
PIPELINE_RUNNER_PORT = os.environ.get('PIPELINE_RUNNER_PORT', '6000')
PIPELINE_RUNNER_SERVER = f'http://{PIPELINE_RUNNER_HOSTNAME}:{PIPELINE_RUNNER_PORT}'

LUIGI_UI_SERVICE_HOSTNAME = os.environ.get('LUIGI_UI_SERVICE_HOSTNAME')
LUIGI_UI_SERVICE_PORT = int(os.environ.get('LUIGI_UI_SERVICE_PORT', '8082'))

# Matchmaker
MME_DEFAULT_CONTACT_NAME = 'Samantha Baxter'
MME_DEFAULT_CONTACT_INSTITUTION = 'Broad Center for Mendelian Genomics'
MME_DEFAULT_CONTACT_EMAIL = 'matchmaker@broadinstitute.org'
MME_DEFAULT_CONTACT_HREF = 'mailto:{}'.format(MME_DEFAULT_CONTACT_EMAIL)

VLM_DEFAULT_CONTACT_EMAIL = os.environ.get('VLM_DEFAULT_CONTACT_EMAIL', 'vlm@broadinstitute.org')
VLM_SEND_EMAIL = os.environ.get('VLM_SEND_EMAIL', 'vlm-noreply@broadinstitute.org')
VLM_CLIENT_ID = os.environ.get('VLM_CLIENT_ID')
VLM_CLIENT_SECRET = os.environ.get('VLM_CLIENT_SECRET')
VLM_AUTH_API = 'https://vlm-auth.us.auth0.com/'

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

SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL = 'seqr-data-loading'
SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL = 'anvil-data-loading'
SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL = 'seqr_loading_notifications'

#########################################################
#  Social auth specific settings
#########################################################
SOCIAL_AUTH_PROVIDER = ''

#########################################################
#  AZUREAD
SOCIAL_AUTH_AZUREAD_V2_TENANT_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_AZUREAD_V2_OAUTH2_CLIENT_ID')
SOCIAL_AUTH_AZUREAD_V2_TENANT_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_AZUREAD_V2_OAUTH2_SECRET')
SOCIAL_AUTH_AZUREAD_V2_TENANT_OAUTH2_TENANT_ID = os.environ.get('SOCIAL_AUTH_AZUREAD_V2_OAUTH2_TENANT')
if SOCIAL_AUTH_AZUREAD_V2_TENANT_OAUTH2_KEY:
    SOCIAL_AUTH_PROVIDER = 'azuread-v2-tenant-oauth2'

#########################################################
# GOOGLE
SOCIAL_AUTH_GOOGLE_OAUTH2_IGNORE_DEFAULT_SCOPE = True
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# Use Google sub ID as the user ID, safer than using email
USE_UNIQUE_USER_ID = True
GOOGLE_LOGIN_REQUIRED_URL = '/login/google-oauth2'
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_CLIENT_ID')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')
if SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
    SOCIAL_AUTH_PROVIDER = 'google-oauth2'

# Build the login URL based on the provider (if any).
LOGIN_URL = '/'.join(filter(None, ['/login', SOCIAL_AUTH_PROVIDER]))

SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_REDIRECT_IS_HTTPS = not DEBUG

SOCIAL_AUTH_PIPELINE_BASE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.social_auth.associate_by_email',
)
SOCIAL_AUTH_PIPELINE_USER_EXIST = ('seqr.utils.social_auth_pipeline.validate_user_exist',)
SOCIAL_AUTH_PIPELINE_ASSOCIATE_USER = ('social_core.pipeline.social_auth.associate_user',)
SOCIAL_AUTH_PIPELINE_LOG = ('seqr.utils.social_auth_pipeline.log_signed_in',)
SOCIAL_AUTH_PIPELINE_CLOUD_BASE = (
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user') + \
    SOCIAL_AUTH_PIPELINE_ASSOCIATE_USER + \
    ('social_core.pipeline.social_auth.load_extra_data',
     'social_core.pipeline.user.user_details')

TERRA_PERMS_CACHE_EXPIRE_SECONDS = os.environ.get('TERRA_PERMS_CACHE_EXPIRE_SECONDS', 60)
TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS = os.environ.get('TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS', 300)

SERVICE_ACCOUNT_FOR_ANVIL = None
SERVICE_ACCOUNT_CREDENTIALS = None

if TERRA_API_ROOT_URL:
    try:
       # Refresh pattern taken from: https://stackoverflow.com/a/74377391
        SERVICE_ACCOUNT_CREDENTIALS, project_id = google.auth.default(scopes=SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE)
        request = google.auth.transport.requests.Request()
        SERVICE_ACCOUNT_CREDENTIALS.refresh(request=request)
        SERVICE_ACCOUNT_FOR_ANVIL = SERVICE_ACCOUNT_CREDENTIALS.service_account_email
    except Exception:
        raise Exception('Error starting seqr - gcloud auth credentials are not properly configured')

    # activate command line account if failed on start up
    activated_service_account = subprocess.run(['gcloud auth list --filter=status:ACTIVE --format="value(account)"'],
                                               capture_output=True, text=True, shell=True).stdout.split('\n')[0] # nosec
    if activated_service_account != SERVICE_ACCOUNT_FOR_ANVIL:
        raise Exception('Error starting seqr - attempt to authenticate gcloud cli failed')

    SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
        'access_type': 'offline',  # to make the access_token can be refreshed after expired (expiration time is 1 hour)
        'approval_prompt': 'auto', # required for successful token refresh
    }

    SOCIAL_AUTH_PIPELINE = ('seqr.utils.social_auth_pipeline.validate_anvil_registration',) + \
                           SOCIAL_AUTH_PIPELINE_BASE + \
                           SOCIAL_AUTH_PIPELINE_CLOUD_BASE + \
                           SOCIAL_AUTH_PIPELINE_LOG
elif SOCIAL_AUTH_AZUREAD_V2_TENANT_OAUTH2_KEY:
    SOCIAL_AUTH_PIPELINE = SOCIAL_AUTH_PIPELINE_BASE + \
                           SOCIAL_AUTH_PIPELINE_CLOUD_BASE + \
                           ('seqr.utils.social_auth_pipeline.log_signed_in',)
else:
    SOCIAL_AUTH_PIPELINE = SOCIAL_AUTH_PIPELINE_BASE + SOCIAL_AUTH_PIPELINE_USER_EXIST + \
                           SOCIAL_AUTH_PIPELINE_ASSOCIATE_USER + SOCIAL_AUTH_PIPELINE_LOG
