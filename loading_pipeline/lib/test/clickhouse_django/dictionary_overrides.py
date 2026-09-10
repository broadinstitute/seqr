"""Overrides Postgres-sourced dictionaries with ClickHouse-sourced versions"""

import re

from django.db import connections
from django.db.models.signals import post_migrate

from loading_pipeline.lib.core import Env

_POSTGRES_SOURCE_RE = re.compile(r'SOURCE\(POSTGRESQL\([^)]*\)\)')
_POSTGRES_SOURCED_DICTIONARIES = ['seqrdb_gene_ids', 'seqrdb_affected_status_dict']


def _override_postgres_sourced_dictionary(dictionary_name):
    with connections['clickhouse_write'].cursor() as cursor:
        cursor.execute(
            """
            SELECT create_table_query FROM system.tables
            WHERE database = %(database)s AND name = %(name)s
            """,
            {'database': Env.CLICKHOUSE_DATABASE, 'name': dictionary_name},
        )
        create_table_query = cursor.fetchone()[0]

        cursor.execute(f'DESCRIBE TABLE {Env.CLICKHOUSE_DATABASE}.`{dictionary_name}`')
        columns = cursor.fetchall()
        src_table = f'{dictionary_name}_src'
        column_defs = ', '.join(f'`{name}` {type_}' for name, type_, *_ in columns)
        cursor.execute(
            f"""
            CREATE OR REPLACE TABLE {Env.CLICKHOUSE_DATABASE}.{src_table} ({column_defs})
            ENGINE = Memory;
            """,
        )

        source = (
            f'SOURCE(CLICKHOUSE(USER {Env.CLICKHOUSE_WRITER_USER} '
            f"PASSWORD '{Env.CLICKHOUSE_WRITER_PASSWORD}' "
            f'DB {Env.CLICKHOUSE_DATABASE} TABLE {src_table}))'
        )
        new_create_table_query = _POSTGRES_SOURCE_RE.sub(
            source,
            create_table_query,
            count=1,
        ).replace('CREATE DICTIONARY', 'CREATE OR REPLACE DICTIONARY', 1)
        cursor.execute(new_create_table_query)


def _on_post_migrate(sender, using, **kwargs):  # noqa: ARG001
    if using != 'clickhouse_write' or sender.name != 'clickhouse_search':
        return
    for dictionary_name in _POSTGRES_SOURCED_DICTIONARIES:
        _override_postgres_sourced_dictionary(dictionary_name)


post_migrate.connect(_on_post_migrate)
