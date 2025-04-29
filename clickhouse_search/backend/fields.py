from clickhouse_backend import models
from itertools import groupby

class NestedField(models.TupleField):

    def __init__(self, *args, group_key=None, flatten_groups=False, **kwargs):
        self.group_key = group_key
        self.flatten_groups = flatten_groups
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "NestedField"

    @property
    def description(self):
        return super().description().replace('Tuple', 'Nested', 1)

    def db_type(self, connection):
        return super().db_type(connection).replace('Tuple', 'Nested', 1)

    def cast_db_type(self, connection):
        return super().cast_db_type(connection).replace('Tuple', 'Nested', 1)

    def from_db_value(self, *args, **kwargs):
        return self._from_db_value(*args, format_item=self._convert_type, **kwargs)

    def _from_db_value(self, value, expression, connection, format_item=None):
        if value is None:
            return value
        value = [
            (format_item(item) if format_item else super(NestedField, self)._from_db_value(item, expression, connection))._asdict()
            for item in value
        ]
        if self.group_key:
            group_agg = next if self.flatten_groups else list
            value = {k: group_agg(v) for k, v in groupby(value, lambda x: x[self.group_key])}
        return value


class UInt64FieldDeltaCodecField(models.UInt64Field):

    def db_type(self, connection):
        return f'{super().db_type(connection)} CODEC(Delta(8), ZSTD(1))'


class NamedTupleField(models.TupleField):

    def _convert_type(self, value):
        value = super()._convert_type(value)
        return value._asdict() if value is not None else value
