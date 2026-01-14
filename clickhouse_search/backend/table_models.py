from clickhouse_backend import models
from django.db import connections
from django.db.models import Func

MATERIALIZED_VIEW_META_FIELDS = ['to_table', 'source_table', 'source_sql', 'column_selects', 'refreshable']
DICTIONARY_META_FIELDS = ['layout', 'lifetime_max', 'postgres_query', 'postgres_db']


class IncrementalMaterializedView(models.ClickhouseModel):

    class Meta:
        abstract = True


class RefreshableMaterializedView(IncrementalMaterializedView):

    @classmethod
    def refresh(cls):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(f'SYSTEM START VIEW "{cls._meta.db_table}"')
            cursor.execute(f'SYSTEM REFRESH VIEW "{cls._meta.db_table}"')
            cursor.execute(f'SYSTEM WAIT VIEW "{cls._meta.db_table}"')

    class Meta:
        abstract = True


class RefreshableMaterializedViewMeta:
    refreshable = True
    column_selects = {}
    source_sql = ''


class Dictionary(models.ClickhouseModel):

    @classmethod
    def dict_get_sql(cls, key, fields, default=None):
        func_name = 'dictGet'
        fields = [f"'{field}'" for field in fields]
        field = fields[0] if len(fields) == 1 else f"({', '.join(fields)})"
        args = [f"'{cls._meta.db_table}'", field, key]
        if default is not None:
            func_name = 'dictGetOrDefault'
            args.append(f"'{default}'")
        return f'{func_name}({", ".join(args)})'

    @classmethod
    def dict_get_expression(cls, expressions, fields, default=None, **kwargs):
        dict_get_func = Func(expressions, **kwargs)
        dict_get_func.template = cls.dict_get_sql('%(expressions)s', fields, default)
        return dict_get_func

    @classmethod
    def reload(cls):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(f'SYSTEM RELOAD DICTIONARY "{cls._meta.db_table}"')

    class Meta:
        abstract = True
