from clickhouse_backend import models
from django.db import connections
from django.db.models import Func

from clickhouse_search.backend.fields import NamedTupleField

MATERIALIZED_VIEW_META_FIELDS = ['to_table', 'source_table', 'source_sql', 'column_selects', 'refreshable']
DICTIONARY_META_FIELDS = ['layout', 'lifetime_max', 'postgres_query', 'postgres_db']


class FixtureLoadableClickhouseModel(models.ClickhouseModel):

    def _save_table(
        self,
        raw=False,
        cls=None,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        # loaddata attempts to run an ALTER TABLE to update existing rows, but since primary keys can not be altered
        # and JOIN tables can not be altered this command fails so need to use the force_insert flag to run an INSERT instead
        return super()._save_table(
            raw=raw, cls=cls, force_insert=True, force_update=force_update, using=using, update_fields=update_fields,
        )

    class Meta:
        abstract = True


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
    def base_fields(cls):
        return [(field.name, field) for field in cls._meta.local_fields if field.name != 'key']

    @classmethod
    def dict_get_expression(cls, expressions, field_names=None, **kwargs):
        base_fields = cls.base_fields()
        if field_names:
            base_fields = [f for f in base_fields if f[0] in field_names]
        output_field = base_fields[0][1] if len(base_fields) == 1 else NamedTupleField(base_fields)
        dict_get_func = Func(expressions, output_field=output_field)
        dict_get_func.template = cls.dict_get_sql('%(expressions)s', [field_name for field_name, _  in base_fields], **kwargs)
        return dict_get_func

    @classmethod
    def reload(cls):
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute(f'SYSTEM RELOAD DICTIONARY "{cls._meta.db_table}"')

    class Meta:
        abstract = True
