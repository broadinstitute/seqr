from django.db import connections
from django.test import TestCase

from loading_pipeline.lib.core import Env


class ClickhouseSchemaTestCase(TestCase):
    databases = ['clickhouse_write']

    # Django's `flush` (the default TestCase teardown for backends without transaction support)
    # determines tables to flush from `apps.get_models()`, but nothing here imports
    # clickhouse_search's model modules, so it finds none. Truncate live tables directly instead.
    def _fixture_teardown(self):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                """
                SELECT name FROM system.tables
                WHERE database = %(database)s AND engine NOT IN ('Dictionary', 'MaterializedView')
                """,
                {'database': Env.CLICKHOUSE_DATABASE},
            )
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                cursor.execute(f'TRUNCATE TABLE `{table}`')  # noqa: S608
