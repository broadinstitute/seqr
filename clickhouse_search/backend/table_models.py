from clickhouse_backend import models


MATERIALIZED_VIEW_META_FIELDS = ['to_table']


class MaterializedView(models.ClickhouseModel):

    class Meta:
        abstract = True
