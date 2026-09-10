from typing import ClassVar

from django.db import connections
from django.test import TestCase

from loading_pipeline.lib.core import Env


class ClickhouseSchemaTestCase(TestCase):
    databases: ClassVar = ['clickhouse_write']

    def _fixture_teardown(self):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(
                """
                SELECT name FROM system.tables
                WHERE database = %(database)s AND engine NOT IN ('Dictionary', 'MaterializedView')
                AND name != 'django_migrations'
                """,
                {'database': Env.CLICKHOUSE_DATABASE},
            )
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                cursor.execute(f'TRUNCATE TABLE `{table}`')
