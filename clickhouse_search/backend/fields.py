from clickhouse_backend import models
from clickhouse_backend.models.fields.tuple import IndexTransformFactory as TupleIndexTransform
from clickhouse_backend.models.fields.array import IndexTransformFactory as ArrayIndexTransform
from collections import defaultdict

class NestedField(models.TupleField):

    def __init__(self, *args, null_when_empty=False, flatten_groups=False, group_by_key=None, **kwargs):
        self.null_when_empty = null_when_empty
        self.flatten_groups = flatten_groups
        self.group_by_key = group_by_key
        super().__init__(*args, **kwargs)

    def clone(self):
        clone = super().clone()
        clone.null_when_empty = self.null_when_empty
        clone.flatten_groups = self.flatten_groups
        clone.group_by_key = self.group_by_key
        return clone

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
            group_value = defaultdict(list)
            for item in value:
                group_value[item[self.group_by_key]].append(item)
            if self.flatten_groups:
                value = {k: v[0] if len(v) == 1 else v for k, v in group_value.items()}
            else:
                value = dict(group_value)
        return value

    def to_python(self, value):
        return [self.call_base_fields("to_python", item) for item in value]

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, (str, bytes)):
            return super(NestedField, self).get_db_prep_value(value, connection, prepared)
        return [super(NestedField, self).get_db_prep_value(item, connection, prepared) for item in value]

    def get_db_prep_save(self, value, connection):
        return [super(NestedField, self).get_db_prep_save(item, connection) for item in value]

    def get_transform(self, name):
        transform = super().get_transform(name)
        if isinstance(transform, TupleIndexTransform):
            transform = ArrayIndexTransform(index=transform.index, base_field=NamedTupleField(self.base_fields, null_if_empty=True))
        return transform


class Enum8Field(models.Enum8Field):

    def clone(self):
        clone = super().clone()
        clone.return_int = self.return_int
        return clone


class UInt64FieldDeltaCodecField(models.UInt64Field):

    def db_type(self, connection):
        return f'{super().db_type(connection)} CODEC(Delta(8), ZSTD(1))'


class NamedTupleField(models.TupleField):

    def __init__(self, *args, null_if_empty=False, null_empty_arrays=False, rename_fields=None, **kwargs):
        self.null_if_empty = null_if_empty
        self.null_empty_arrays = null_empty_arrays
        self.rename_fields = rename_fields or {}
        super().__init__(*args, **kwargs)

    def clone(self):
        clone = super().clone()
        clone.null_if_empty = self.null_if_empty
        clone.null_empty_arrays = self.null_empty_arrays
        clone.rename_fields = self.rename_fields
        return clone

    def _convert_type(self, value):
        value = super()._convert_type(value)
        if self.null_if_empty and not any(value):
            return None
        value = value._asdict()
        for key, renamed_key in self.rename_fields.items():
            value[renamed_key] = value.pop(key)
        if self.null_empty_arrays:
            for key, item in value.items():
                if item == []:
                    value[key] = None
        return value

    def to_python(self, value):
        return self.call_base_fields("to_python", value)
