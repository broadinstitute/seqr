from clickhouse_backend import models
from collections import defaultdict

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
        if self.flatten_groups:
            value = {item[self.group_by_key]: item for item in value}
        elif self.group_by_key:
            group_value = defaultdict(list)
            for item in value:
                group_value[item[self.group_by_key]].append(item)
            value = dict(group_value)
        return value

    def to_python(self, value):
        return [self.call_base_fields("to_python", item) for item in value]

    def get_db_prep_value(self, value, connection, prepared=False):
        return [super(NestedField, self).get_db_prep_value(item, connection, prepared) for item in value]

    def get_db_prep_save(self, value, connection):
        return [super(NestedField, self).get_db_prep_save(item, connection) for item in value]


class UInt64FieldDeltaCodecField(models.UInt64Field):

    def db_type(self, connection):
        return f'{super().db_type(connection)} CODEC(Delta(8), ZSTD(1))'


class NamedTupleField(models.TupleField):

    def __init__(self, *args, null_if_empty=False, null_empty_arrays=False, **kwargs):
        self.null_if_empty = null_if_empty
        self.null_empty_arrays = null_empty_arrays
        super().__init__(*args, **kwargs)

    def _convert_type(self, value):
        value = super()._convert_type(value)
        if self.null_if_empty and not any(value):
            return None
        value = value._asdict()
        if self.null_empty_arrays:
            for key, item in value.items():
                if item == []:
                    value[key] = None
        return value

    def to_python(self, value):
        return self.call_base_fields("to_python", value)
