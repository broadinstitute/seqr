"""Minimal Django settings for running `clickhouse_search`'s real migrations in tests.

Lives in its own directory, prepended to `sys.path` via pytest's `pythonpath` option (see
`pyproject.toml`), so it doubles as both `DJANGO_SETTINGS_MODULE` and the bare `settings` module
`clickhouse_search/backend/base.py` imports directly - without pulling in the main app's much
heavier `settings.py`.
"""

import os

# Shared Django fixtures (loaddata) for clickhouse_search-backed test data - see
# lib/test/clickhouse_schema_testcase.py.
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
SECRET_KEY = 'loading-pipeline-test'  # noqa: S105
DEPLOYMENT_TYPE = os.environ.get('DEPLOYMENT_TYPE', 'dev')
PIPELINE_RUNNER_SERVER = os.environ.get('PIPELINE_RUNNER_SERVER', 'http://localhost')
# Must differ - EmbeddedRocksDB tables (annotations_memory vs annotations_disk) using the same
# path deadlock on the same file lock.
CLICKHOUSE_IN_MEMORY_DIR = os.environ.get(
    'CLICKHOUSE_IN_MEMORY_DIR',
    '/tmp/loading_pipeline_test_clickhouse_in_memory',  # noqa: S108
)
CLICKHOUSE_DATA_DIR = os.environ.get(
    'CLICKHOUSE_DATA_DIR',
    '/tmp/loading_pipeline_test_clickhouse_data',  # noqa: S108
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
        # Skip Django's default `test_<NAME>` prefix; land on the name Env.CLICKHOUSE_DATABASE
        # already expects.
        'NAME': CLICKHOUSE_DATABASE_NAME,
        # Without this, Django assumes this alias depends on `default` and never resolves it,
        # since our tests only ever request `databases = ['clickhouse_write']`.
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
    # Dummy backends: never opened (only aliases named in a test's `databases` get created), but
    # `clickhouse_search/backend/base.py` reads their `NAME` to embed in generated dictionary DDL.
    'default': {
        'ENGINE': 'django.db.backends.dummy',
        'NAME': 'test_default_unused',
    },
    'reference_data': {
        'ENGINE': 'django.db.backends.dummy',
        'NAME': 'test_reference_data_unused',
    },
}
