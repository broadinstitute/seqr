import pytest

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass

@pytest.fixture(scope='session')
def django_db_setup(request, django_db_blocker,django_db_keepdb):
    from django.test.utils import setup_databases, teardown_databases

    with django_db_blocker.unblock():
        db_cfg = setup_databases(
            verbosity=request.config.option.verbose,
            interactive=False,
            aliases=['default', 'reference_data', 'clickhouse_write'],
            keepdb=django_db_keepdb,
        )
        #     TODO loaddata

    yield

    if not django_db_keepdb:
        with django_db_blocker.unblock():
            try:
                teardown_databases(db_cfg, verbosity=request.config.option.verbose)
            except Exception as exc:  # noqa: BLE001
                request.node.warn(
                    pytest.PytestWarning(f"Error when trying to teardown test databases: {exc!r}")
                )