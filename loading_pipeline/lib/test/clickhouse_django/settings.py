"""Minimal Django settings for standing up the `clickhouse_search` schema in tests.

This module is intentionally NOT the main seqr app's `settings.py` — `loading_pipeline` has its
own, much smaller, dependency footprint and only needs enough Django configuration to run
`clickhouse_search`'s migrations against a test ClickHouse database.

It is deliberately placed in its own directory that gets prepended to `sys.path` via pytest's
`pythonpath` option (see `pyproject.toml`), for two reasons:
  1. It's used as `DJANGO_SETTINGS_MODULE`.
  2. `clickhouse_search/backend/base.py` does a bare `from settings import ...` (not
     `django.conf.settings`), so a top-level module literally named `settings` has to be
     importable on `sys.path` and resolve to *this* module rather than the main app's
     `settings.py` (which pulls in postgres/guardian/social_django/etc. that `loading_pipeline`
     doesn't depend on).

Only a single real ClickHouse connection/credential set is configured, on the `clickhouse_write`
alias. `ClickHouseRouter.allow_migrate` (in `clickhouse_search/models/__init__.py`) hardcodes
`db == 'clickhouse_write'` for the `clickhouse_search` app, so migrations must run against an
alias literally named `clickhouse_write` - that's the one Django actually creates/migrates a real
test database for. `clickhouse` and `default` are present only because
`clickhouse_search/backend/base.py` looks up `DATABASES['clickhouse_write']['NAME']` /
`DATABASES['default']['NAME']` to embed a database name string into generated dictionary DDL - not
because either needs its own real connection:
  - `clickhouse` mirrors the `clickhouse_write` alias's test database (`TEST: {'MIRROR': ...}`),
    so Django doesn't create/destroy a second real test database for it.
  - `default` is a `dummy` backend entry - it's never actually opened. pytest-django only calls
    `create_test_db()` for aliases a given test's `databases` attribute names (see
    `pytest_django.fixtures._get_databases_for_setup`); it does not unconditionally create every
    alias in `DATABASES`. As long as every `TestCase` subclass in this suite declares
    `databases = ['clickhouse_write']` (per the shared base class), `default` is never touched, so
    the dummy backend never needs to support real connections - only `DATABASES['default']['NAME']`
    ever gets read, purely as a string.

Only `clickhouse_search`'s own migrations are permitted to run anywhere: `DATABASE_ROUTERS`
appends a small catch-all router (`_NoOtherAppMigrationsRouter`, below) that vetoes migrations for
every app *other* than `clickhouse_search`. Without it, Django's default routing would try to
migrate `clickhouse_search`'s (undeclared, but still `INSTALLED_APPS`-adjacent) dependencies onto
`default`, which would fail against the dummy backend - `clickhouse_search`'s migrations use
ClickHouse-only DDL/field types that don't apply to any other app.

`clickhouse_search`'s migration `0040_gnomadnoncodingconstraintdict.py` has a
`conditionally_refresh_reference_dataset` step that skips a live network call
(`requests.post(...)`) when `DATABASES['default']['NAME'].startswith('test_')`. That module-level
`DATABASES` reference is the plain dict below, not a Django-test-remapped one (since `default` is
never created/mutated by the test runner, per above), so `default`'s `NAME` is just set directly to
a literal `test_`-prefixed string to keep that guard working and avoid the network call during test
runs.
"""

import os

INSTALLED_APPS = [
    'clickhouse_backend',
    'clickhouse_search',
]


class _NoOtherAppMigrationsRouter:
    """Prevents any app other than `clickhouse_search` from having migrations applied anywhere.

    `clickhouse_search`'s modules pull in a handful of other apps transitively (see module
    docstring); this keeps those apps' own schemas from ever being created against the throwaway
    `default` dummy database (which can't support them; they're never needed here anyway).
    """

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
CLICKHOUSE_IN_MEMORY_DIR = os.environ.get('CLICKHOUSE_IN_MEMORY_DIR', '/tmp')  # noqa: S108
CLICKHOUSE_DATA_DIR = os.environ.get('CLICKHOUSE_DATA_DIR', '/tmp')  # noqa: S108

CLICKHOUSE_WRITER_USER = os.environ.get('CLICKHOUSE_WRITER_USER', 'default')
CLICKHOUSE_WRITER_PASSWORD = os.environ.get('CLICKHOUSE_WRITER_PASSWORD', 'default_password')
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
    # Avoid Django's default `test_<NAME>` prefix so the schema lands in the database name that
    # `loading_pipeline.lib.core.environment.Env.CLICKHOUSE_DATABASE` already expects.
    'TEST': {
        'NAME': CLICKHOUSE_DATABASE_NAME,
    },
}

DATABASES = {
    'clickhouse_write': CLICKHOUSE_DB_CONFIG,
    'clickhouse': {
        **CLICKHOUSE_DB_CONFIG,
        'TEST': {'MIRROR': 'clickhouse_write'},
    },
    'default': {
        'ENGINE': 'django.db.backends.dummy',
        'NAME': 'test_default_unused',
    },
}
