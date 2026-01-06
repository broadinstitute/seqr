from clickhouse_backend import models
from django.db.migrations import state
from django.db.models import options

from clickhouse_search.backend.table_models import MATERIALIZED_VIEW_META_FIELDS, DICTIONARY_META_FIELDS

options.DEFAULT_NAMES = (
    *options.DEFAULT_NAMES,
    'projection',
    *MATERIALIZED_VIEW_META_FIELDS,
    *DICTIONARY_META_FIELDS,
)
state.DEFAULT_NAMES = options.DEFAULT_NAMES

class ClickHouseRouter:
    """
    Adapted from https://github.com/jayvynl/django-clickhouse-backend/blob/v1.3.2/README.md#configuration
    """

    def __init__(self):
        self.route_model_names = set()
        for model in self._get_subclasses(models.ClickhouseModel):
            if model._meta.abstract:
                continue
            self.route_model_names.add(model._meta.label_lower)

    @staticmethod
    def _get_subclasses(class_):
        classes = class_.__subclasses__()

        index = 0
        while index < len(classes):
            classes.extend(classes[index].__subclasses__())
            index += 1

        return list(set(classes))

    def db_for_read(self, model, **hints):
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def db_for_write(self, model, **hints):
        # When using Clickhouse models, the default connection routing used for writes will attempt to use read-only
        # credentials and fail. This is by design to prevent accidental writes. To write to Clickhouse, explicitly
        # set my_queryset.using('clickhouse_write') before executing a write operation
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'clickhouse_search' or hints.get('clickhouse'):
            return db == 'clickhouse_write'
        elif db in {'clickhouse', 'clickhouse_write'}:
            return False
        return None
