from clickhouse_backend import models
from django.db import connections


MATERIALIZED_VIEW_META_FIELDS = ['to_table', 'source_table', 'source_sql', 'column_selects', 'refreshable']


class MaterializedView(models.ClickhouseModel):

    @classmethod
    def refresh(cls):
        if getattr(cls._meta, 'refreshable', False):
            with connections['clickhouse_write'].cursor() as cursor:
                cursor.execute(f'SYSTEM REFRESH VIEW "{cls._meta.db_table}"')
                cursor.execute(f'SYSTEM WAIT VIEW "{cls._meta.db_table}"')

    class Meta:
        abstract = True
