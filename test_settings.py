from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': os.environ.get('POSTGRES_SERVICE_HOSTNAME', 'localhost'),
        'PORT': int(os.environ.get('POSTGRES_SERVICE_PORT', '5432')),
        'NAME': 'seqrdb',
        'USER': os.environ.get('POSTGRES_USERNAME', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'TEST': {
            'NAME': 'seqr_test_db'
        }
    }
}

ALLOWED_HOSTS = ['*']
