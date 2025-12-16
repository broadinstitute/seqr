from clickhouse_backend.backend.base import (
    DatabaseWrapper as BaseDatabaseWrapper,
    DatabaseSchemaEditor as BaseDatabaseSchemaEditor,
)

from clickhouse_search.backend.engines import Join

class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    def _is_materialzed_view(self, model):
        return getattr(model._meta, 'to_table', None) is not None

    def table_sql(self, model):
        if self._is_materialzed_view(model):
            return self._materialized_view_sql(model)

        sql, params = super().table_sql(model)
        projection = getattr(model._meta, 'projection', None)
        if projection:
            sql = sql.replace(
                ') ENGINE',
                f', PROJECTION {projection.name} (SELECT {projection.select} ORDER BY {projection.order_by})) ENGINE',
            )
        return sql, params

    def _get_engine_expression(self, model, engine):
        if self._is_materialzed_view(model):
            return self.quote_name(model._meta.to_table._meta.db_table)

        prev_quote_value = self.quote_value   # pylint: disable=access-member-before-definition
        if isinstance(engine, Join):
            self.quote_value = self.no_quote_value
        expression = super()._get_engine_expression(model, engine)
        self.quote_value = prev_quote_value
        return expression

    def no_quote_value(self, value):
        return value

    def _materialized_view_sql(self, model):
        """
         ┌─statement─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
1. │ CREATE MATERIALIZED VIEW test_seqr.`GRCh38/SNV_INDEL/entries_to_project_gt_stats_mv` TO test_seqr.`GRCh38/SNV_INDEL/project_gt_stats`↴│
   │↳(                                                                                                                                    ↴│
   │↳    `project_guid` LowCardinality(String),                                                                                           ↴│
   │↳    `key` UInt32,                                                                                                                    ↴│
   │↳    `sample_type` Enum8('WES' = 1, 'WGS' = 2),                                                                                       ↴│
   │↳    `affected` String,                                                                                                               ↴│
   │↳    `ref_samples` Int64,                                                                                                             ↴│
   │↳    `het_samples` Int64,                                                                                                             ↴│
   │↳    `hom_samples` Int64                                                                                                              ↴│
   │↳)                                                                                                                                    ↴│
   │↳AS SELECT                                                                                                                            ↴│
   │↳    project_guid,                                                                                                                    ↴│
   │↳    key,                                                                                                                             ↴│
   │↳    sample_type,                                                                                                                     ↴│
   │↳    dictGetOrDefault('test_seqr.seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U') AS affected,           ↴│
   │↳    sumIf(sign, calls.gt = 'REF') AS ref_samples,                                                                                    ↴│
   │↳    sumIf(sign, calls.gt = 'HET') AS het_samples,                                                                                    ↴│
   │↳    sumIf(sign, calls.gt = 'HOM') AS hom_samples                                                                                     ↴│
   │↳FROM test_seqr.`GRCh38/SNV_INDEL/entries`                                                                                            ↴│
   │↳ARRAY JOIN calls                                                                                                                     ↴│
   │↳GROUP BY                                                                                                                             ↴│
   │↳    project_guid,                                                                                                                    ↴│
   │↳    key,                                                                                                                             ↴│
   │↳    sample_type,                                                                                                                     ↴│
   │↳    affected                                                                                                                          │
   └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
        """

        original_sql_create_table = self.sql_create_table
        self.sql_create_table = 'CREATE MATERIALIZED VIEW %(table)s TO %(engine)s (%(definition)s)'
        sql, params = super().table_sql(model)

        import pdb; pdb.set_trace()
        self.sql_create_table = original_sql_create_table
        raise NotImplementedError


class DatabaseWrapper(BaseDatabaseWrapper):
    SchemaEditorClass = DatabaseSchemaEditor
