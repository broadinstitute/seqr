from clickhouse_backend.backend.base import (
    DatabaseWrapper as BaseDatabaseWrapper,
    DatabaseSchemaEditor as BaseDatabaseSchemaEditor,
)

from clickhouse_search.backend.engines import Join
from settings import CLICKHOUSE_WRITER_USER, CLICKHOUSE_WRITER_PASSWORD


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    def _is_materialzed_view(self, model):
        return getattr(model._meta, 'to_table', None) is not None

    def _is_dictionary(self, model):
        return not self._is_materialzed_view(model) and getattr(model._meta, 'source_table', None) is not None

    def table_sql(self, model):
        if self._is_materialzed_view(model):
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
        meta = model._meta
        selects = [
            f'{meta.column_selects[field.column]} {field.column}' if field.column in meta.column_selects else field.column
            for field in meta.local_fields
        ]
        sql = f'{table_sql} AS SELECT {", ".join(selects)} FROM {self._table_name(meta, meta.source_table)} {meta.source_sql}'  # nosec
        self.sql_create_table = original_sql_create_table
        return sql, params

    def _get_engine_expression(self, model, engine):
        if self._is_materialzed_view(model):
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
        source_table = self._table_name(meta, meta.source_table)
        self.sql_create_table = f"""
        CREATE DICTIONARY %(table)s (%(definition)s) %(extra)s
        SOURCE(CLICKHOUSE(USER {CLICKHOUSE_WRITER_USER} PASSWORD {CLICKHOUSE_WRITER_PASSWORD} TABLE {source_table}))
        LIFETIME(MIN 0 MAX 0)
        LAYOUT(FLAT(MAX_ARRAY_SIZE {meta.size}))
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
