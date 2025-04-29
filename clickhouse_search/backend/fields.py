from clickhouse_backend import models

class NestedField(models.TupleField):

    def __init__(self, *args, group_key=None, **kwargs):
        self.group_key = group_key
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
        if self.group_key:
            value = {item[self.group_key]: item for item in value}
        return value


class UInt64FieldDeltaCodecField(models.UInt64Field):

    def db_type(self, connection):
        return f'{super().db_type(connection)} CODEC(Delta(8), ZSTD(1))'


class NamedTupleField(models.TupleField):

    def _convert_type(self, value):
        value = super()._convert_type(value)
        return value._asdict() if value is not None else value
