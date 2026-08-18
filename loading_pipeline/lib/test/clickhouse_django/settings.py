import os

from loading_pipeline.lib.test.clickhouse_django import (
    dictionary_overrides,  # noqa: F401
)

FIXTURE_DIRS = [os.path.join(os.path.dirname(__file__), '..', 'fixtures')]

INSTALLED_APPS = [
    'clickhouse_backend',
    'seqr',  # stub package (see seqr/__init__.py), not the real app
    'clickhouse_search',
]


class _NoOtherAppMigrationsRouter:
    """Only `clickhouse_search` may migrate anywhere; everything else is vetoed."""

    @staticmethod
    def allow_migrate(db, app_label, model_name=None, **hints):  # noqa: ARG004
        if app_label == 'clickhouse_search':
            return None  # defer to ClickHouseRouter
        return False


DATABASE_ROUTERS = [
    'clickhouse_search.models.ClickHouseRouter',
    'settings._NoOtherAppMigrationsRouter',
]

USE_TZ = True
SECRET_KEY = 'loading-pipeline-test'  # noqa: S105 # nosec B105
DEPLOYMENT_TYPE = os.environ.get('DEPLOYMENT_TYPE', 'dev')
PIPELINE_RUNNER_SERVER = os.environ.get('PIPELINE_RUNNER_SERVER', 'http://localhost')
CLICKHOUSE_IN_MEMORY_DIR = os.environ.get(
    'CLICKHOUSE_IN_MEMORY_DIR',
    '/tmp/loading_pipeline_test_clickhouse_in_memory',  # noqa: S108 # nosec B108
)
CLICKHOUSE_DATA_DIR = os.environ.get(
    'CLICKHOUSE_DATA_DIR',
    '/tmp/loading_pipeline_test_clickhouse_data',  # noqa: S108 # nosec B108
)

CLICKHOUSE_WRITER_USER = os.environ.get('CLICKHOUSE_WRITER_USER', 'default')
CLICKHOUSE_WRITER_PASSWORD = os.environ.get(
    'CLICKHOUSE_WRITER_PASSWORD',
    'default_password',
)
CLICKHOUSE_DATABASE_NAME = os.environ.get('CLICKHOUSE_DATABASE', 'seqr')

CLICKHOUSE_DB_CONFIG = {
    'ENGINE': 'clickhouse_search.backend',
    'NAME': CLICKHOUSE_DATABASE_NAME,
    'USER': CLICKHOUSE_WRITER_USER,
    'PASSWORD': CLICKHOUSE_WRITER_PASSWORD,
    'HOST': os.environ.get('CLICKHOUSE_SERVICE_HOSTNAME', 'localhost'),
    'PORT': int(os.environ.get('CLICKHOUSE_SERVICE_PORT', '9000')),
    'OPTIONS': {
        'settings': {
            'use_client_time_zone': False,
        },
    },
    'TEST': {
        # Skip Django's default `test_<NAME>` prefix; land on the name Env.CLICKHOUSE_DATABASE already expects.
        'NAME': CLICKHOUSE_DATABASE_NAME,
        # Without this, Django assumes this alias depends on `default` and never resolves it
        'DEPENDENCIES': [],
    },
}

DATABASES = {
    'clickhouse_write': CLICKHOUSE_DB_CONFIG,
    # Mirrored so Django doesn't create/destroy a second real test database for it.
    'clickhouse': {
        **CLICKHOUSE_DB_CONFIG,
        'TEST': {'MIRROR': 'clickhouse_write'},
    },
    'default': {
        'ENGINE': 'django.db.backends.dummy',
        'NAME': 'test_default_unused',
    },
    'reference_data': {
        'ENGINE': 'django.db.backends.dummy',
        'NAME': 'test_reference_data_unused',
    },
}
