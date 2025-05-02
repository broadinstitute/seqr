from clickhouse_backend import models
from itertools import groupby

class NestedField(models.TupleField):

    def __init__(self, *args, null_when_empty=False, flatten_groups=False, group_by_key=None, **kwargs):
        self.null_when_empty = null_when_empty
        self.flatten_groups = flatten_groups
        self.group_by_key = group_by_key
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
        if self.null_when_empty and not value:
            return None
        value = [
            (format_item(item) if format_item else super(NestedField, self)._from_db_value(item, expression, connection))._asdict()
            for item in value
        ]
        if self.group_by_key:
            group_agg = next if self.flatten_groups else list
            value = {k: group_agg(v) for k, v in groupby(value, lambda x: x[self.group_by_key])}
        return value

    def to_python(self, value):
        return [super(NestedField, self).to_python(self.container_class(**item)) for item in value]

    def call_base_fields(self, func_name, value, *args, **kwargs):
        return [super(NestedField, self).call_base_fields(
            func_name,
            self.container_class(**item) if isinstance(value, dict) else item,
            *args,
            **kwargs,
        ) for item in value]


class UInt64FieldDeltaCodecField(models.UInt64Field):

    def db_type(self, connection):
        return f'{super().db_type(connection)} CODEC(Delta(8), ZSTD(1))'


class NamedTupleField(models.TupleField):

    def __init__(self, *args, null_if_empty=False, **kwargs):
        self.null_if_empty = null_if_empty
        super().__init__(*args, **kwargs)

    def _convert_type(self, value):
        value = super()._convert_type(value)
        if self.null_if_empty and not any(value):
            return None
        return value._asdict()

    def to_python(self, value):
        if isinstance(value, dict):
            value = self.container_class(**value)
        return super().to_python(value)

    def call_base_fields(self, func_name, value, *args, **kwargs):
        if isinstance(value, dict):
            value = self.container_class(**value)
        return super().call_base_fields(func_name, value, *args, **kwargs)
