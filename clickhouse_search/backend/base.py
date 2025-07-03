from clickhouse_backend.backend.base import (
    DatabaseWrapper as BaseDatabaseWrapper,
    DatabaseSchemaEditor as BaseDatabaseSchemaEditor,
)

from clickhouse_search.backend.engines import Join

class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    def table_sql(self, model):
        sql, params = super().table_sql(model)
        projection = getattr(model._meta, 'projection', None)
        if projection:
            sql = sql.replace(
                ') ENGINE',
                f', PROJECTION {projection.name} (SELECT {projection.select} ORDER BY {projection.order_by})) ENGINE',
            )
        return sql, params

    def _get_engine_expression(self, model, engine):
        prev_quote_value = self.quote_value   # pylint: disable=access-member-before-definition
        if isinstance(engine, Join):
            self.quote_value = self.no_quote_value
        expression = super()._get_engine_expression(model, engine)
        self.quote_value = prev_quote_value
        return expression

    def no_quote_value(self, value):
        return value

    def _create_index_sql( self,
        model,
        *args,
        fields=None,
        name=None,
        sql=None,
        suffix="",
        col_suffixes=None,
        type=None,
        granularity=None,
        expressions=None,
        inline=False,
        **kwargs,
   ):
        return super()._create_index_sql(model, *args, fields, name, sql, suffix, col_suffixes, type, granularity, expressions, inline)

class DatabaseWrapper(BaseDatabaseWrapper):
    SchemaEditorClass = DatabaseSchemaEditor
