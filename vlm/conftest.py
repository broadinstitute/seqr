import pytest

@pytest.fixture(scope='session')
def django_db_blocker(django_db_blocker, db):
    pass

@pytest.fixture(scope='session')
def django_db_setup(request, django_db_blocker,django_db_keepdb):
    from django.core.management import call_command
    from django.test.utils import setup_databases, teardown_databases

    with django_db_blocker.unblock():
        db_cfg = setup_databases(
            verbosity=request.config.option.verbose,
            interactive=False,
            aliases=['default', 'reference_data', 'clickhouse_write'],
            keepdb=django_db_keepdb,
        )
        call_command('loaddata', 'clickhouse_search', '--database=clickhouse_write')

    yield

    if not django_db_keepdb:
        with django_db_blocker.unblock():
            try:
                teardown_databases(db_cfg, verbosity=request.config.option.verbose)
            except Exception as exc:  # noqa: BLE001
                request.node.warn(
                    pytest.PytestWarning(f"Error when trying to teardown test databases: {exc!r}")
                )
