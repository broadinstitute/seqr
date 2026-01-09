from clickhouse_backend import models
from django.db import connections


MATERIALIZED_VIEW_META_FIELDS = ['to_table', 'source_table', 'source_sql', 'column_selects', 'refreshable']


class IncrementalMaterializedView(models.ClickhouseModel):

    class Meta:
        abstract = True


class RefreshableMaterializedView(IncrementalMaterializedView):

    @classmethod
    def refresh(cls):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(f'SYSTEM REFRESH VIEW "{cls._meta.db_table}"')
            cursor.execute(f'SYSTEM WAIT VIEW "{cls._meta.db_table}"')

    class Meta:
        abstract = True


class RefreshableMaterializedViewMeta:
    refreshable = True
    column_selects = {}
    source_sql = ''
