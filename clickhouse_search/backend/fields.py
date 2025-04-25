from clickhouse_backend import models

class NestedField(models.TupleField):

    def get_internal_type(self):
        return "NestedField"

    @property
    def description(self):
        return super().description().replace('Tuple', 'Nested', 1)

    def db_type(self, connection):
        return super().db_type(connection).replace('Tuple', 'Nested', 1)

    def cast_db_type(self, connection):
        return super().cast_db_type(connection).replace('Tuple', 'Nested', 1)

    def _from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return [self.container_class(*item)._asdict() for item in value]


class UInt64FieldDeltaCodecField(models.UInt64Field):

    def db_type(self, connection):
        return f'{super().db_type(connection)} CODEC(Delta(8), ZSTD(1))'


class NamedTupleField(models.TupleField):

    def _convert_type(self, value):
        value = super()._convert_type(value)
        return value._asdict() if value is not None else value
