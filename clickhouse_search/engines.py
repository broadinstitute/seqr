from clickhouse_backend import models
from django.db.models import Value


def _no_validate(value, name):
    return value


class CollapsingMergeTree(models.CollapsingMergeTree):
    setting_types = {
        **models.CollapsingMergeTree.setting_types,
        _no_validate: ['deduplicate_merge_projection_mode']
    }


class EmbeddedRocksDB(models.BaseMergeTree):
    max_arity = 2

    def __init__(self, *expressions, **settings):
        super().__init__(*[Value(e) for e in expressions], **settings)


class Join(models.Engine):
    arity = 3

    def __init__(self, *expressions, **settings):
        super().__init__(*[Value(e) for e in expressions], **settings)
