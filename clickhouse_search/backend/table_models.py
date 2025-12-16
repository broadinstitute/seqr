from clickhouse_backend import models


MATERIALIZED_VIEW_META_FIELDS = ['to_table', 'source_table', 'source_sql', 'column_selects']


class MaterializedView(models.ClickhouseModel):

    class Meta:
        abstract = True
