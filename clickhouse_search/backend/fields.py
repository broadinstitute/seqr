from clickhouse_backend import models

class NestedField(models.TupleField):

    def __init__(self, *args, group_by_key=None, **kwargs):
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
        return self._from_db_value(*args, **kwargs)

    def _from_db_value(self, value, expression, connection):
        if value is None:
            return value
        value = [self._convert_type(item)._asdict() for item in value]
        if self.group_by_key:
            value = {item[self.group_by_key]: item for item in value}
        return value


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
