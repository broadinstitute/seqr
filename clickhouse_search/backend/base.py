from clickhouse_backend.backend.base import (
    DatabaseWrapper as BaseDatabaseWrapper,
    DatabaseSchemaEditor as BaseDatabaseSchemaEditor,
)

from clickhouse_search.backend.engines import Join
from settings import CLICKHOUSE_WRITER_USER, CLICKHOUSE_WRITER_PASSWORD, DATABASES


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    def _is_materialized_view(self, model):
        return getattr(model._meta, 'to_table', None) is not None

    def _is_dictionary(self, model):
        return getattr(model._meta, 'layout', None) is not None

    def table_sql(self, model):
        if self._is_materialized_view(model):
            return self._materialized_view_sql(model)
        elif self._is_dictionary(model):
            return self._dictionary_sql(model)

        sql, params = super().table_sql(model)
        projection = getattr(model._meta, 'projection', None)
        if projection:
            sql = sql.replace(
                ') ENGINE',
                f', PROJECTION {projection.name} (SELECT {projection.select} ORDER BY {projection.order_by})) ENGINE',
            )
        return sql, params

    def _table_name(self, meta, table_model_name):
        table_model = meta.apps.get_model('clickhouse_search', table_model_name)
        return self.quote_name(table_model._meta.db_table)

    def _materialized_view_sql(self, model):
        original_sql_create_table = self.sql_create_table  # pylint: disable=access-member-before-definition
        self.sql_create_table = 'CREATE MATERIALIZED VIEW %(table)s %(engine)s (%(definition)s)'
        table_sql, params = super().table_sql(model)
        if getattr(model._meta, 'create_empty', False):
            table_sql = table_sql + ' EMPTY'
        meta = model._meta
        selects = [
            f'{meta.column_selects[field.column]} {field.column}' if field.column in meta.column_selects else field.column
            for field in meta.local_fields
        ]

        source_url = getattr(meta, 'source_url', None)
        if source_url:
            source_url_template = getattr(meta, 'source_url_template', "{source_func}('{source_url}')}")
            source_func = 'gcs' if source_url.endswith('.parquet') else 'url'
            source = source_url_template.format(source_func=source_func, source_url=source_url)
        else:
            source = self._table_name(meta, meta.source_table)

        sql = f'{table_sql} AS SELECT {", ".join(selects)} FROM {source} {meta.source_sql}'  # nosec
        self.sql_create_table = original_sql_create_table
        return sql, params

    def _get_engine_expression(self, model, engine):
        if self._is_materialized_view(model):
            return self._get_materialized_view_engine_expression(model)

        prev_quote_value = self.quote_value   # pylint: disable=access-member-before-definition
        if isinstance(engine, Join):
            self.quote_value = self.no_quote_value
        expression = super()._get_engine_expression(model, engine)
        self.quote_value = prev_quote_value
        return expression

    def _get_materialized_view_engine_expression(self, model):
        sql = f'TO {self._table_name(model._meta, model._meta.to_table)}'
        if getattr(model._meta, 'refreshable', False):
            sql = 'REFRESH EVERY 10 YEAR ' + sql
        return sql

    def _dictionary_sql(self, model):
        original_sql_create_table = self.sql_create_table  # pylint: disable=access-member-before-definition
        meta = model._meta

        postgres_query = getattr(meta, 'postgres_query', None)
        if postgres_query:
            db = DATABASES[getattr(meta, 'postgres_db', 'default')]['NAME']
            source = f"POSTGRESQL(NAME 'seqr_postgres_named_collection' DATABASE {db} QUERY '{postgres_query}')"
        else:
            source_table = self._table_name(meta, meta.source_table)
            clickhouse_query_template = getattr(meta, 'clickhouse_query_template', None)
            table_source = f"QUERY '{clickhouse_query_template.format(table=source_table)}'" \
                if clickhouse_query_template else f'TABLE {source_table}'
            source = f"CLICKHOUSE(USER '{CLICKHOUSE_WRITER_USER}' PASSWORD '{CLICKHOUSE_WRITER_PASSWORD}' {table_source})"

        layout = f'LAYOUT({meta.layout})'
        if meta.layout == 'RANGE_HASHED()':
            layout += ' RANGE(MIN start MAX end)'

        self.sql_create_table = f"""
        CREATE DICTIONARY %(table)s (%(definition)s) %(extra)s
        SOURCE({source})
        LIFETIME(MIN 0 MAX {getattr(meta, 'lifetime_max', 0)})
        {layout}
        """
        sql, params = super().table_sql(model)
        self.sql_create_table = original_sql_create_table
        return sql, params

    def delete_model(self, model):
        if self._is_dictionary(model):
            self.sql_delete_table = self.sql_delete_table.replace('TABLE', 'DICTIONARY')
        super().delete_model(model)
        self.sql_delete_table = self.sql_delete_table.replace('DICTIONARY', 'TABLE')

    def no_quote_value(self, value):
        return value


class DatabaseWrapper(BaseDatabaseWrapper):
    SchemaEditorClass = DatabaseSchemaEditor
