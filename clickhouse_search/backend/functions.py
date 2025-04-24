from clickhouse_backend.models.fields import ArrayField
from clickhouse_backend.models.functions.base import Func

class array(Func):
    def __init__(self, *expressions, base_field=None, **extra):
        super().__init__(*expressions, output_field=ArrayField(base_field), **extra)
