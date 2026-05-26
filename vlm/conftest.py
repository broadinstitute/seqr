import pytest

@pytest.fixture(autouse=True)
def enable_db_globally(django_db_blocker):
    """Globally unblocks database access for all tests and fixtures."""
    django_db_blocker.unblock()
