from clickhouse_backend.models.fields.array import ArrayField, ArrayLookup
from clickhouse_backend.models import UInt32Field
from django.db.models import Func, lookups, BooleanField

from clickhouse_search.backend.fields import NamedTupleField, NestedField

class Array(Func):
    function = 'array'


class ArrayMap(Func):
    function = 'arrayMap'
    template = "%(function)s(x -> %(mapped_expression)s, %(expressions)s)"


def _format_condition(filters):
    conditions = [
        (template[0] if template else '{field} = {value}').format(field=f'x.{field}', value=value)
        for field, (value, *template) in filters.items()  # pylint: disable=access-member-before-definition
    ]
    return f'and({", ".join(conditions)})' if len(conditions) > 1 else conditions[0]


def _format_conditions(conditions):
     conditions = [_format_condition(f) for f in conditions]
     return f'or({", ".join(conditions)})' if len(conditions) > 1 else conditions[0]


@NestedField.register_lookup
@ArrayField.register_lookup
class ArrayExists(ArrayLookup):
    lookup_name = "array_exists"
    function = "arrayExists"
    swap_args = True
    prepare_rhs = False

    def get_prep_lookup(self):
        or_filters = self.rhs.get('OR', [self.rhs]) # pylint: disable=access-member-before-definition
        condition = _format_conditions(or_filters)
        self.rhs = f'x -> {condition}'
        return super().get_prep_lookup()

    def process_rhs(self, compiler, connection):
        _, rhs_params = super().process_rhs(compiler, connection)
        return rhs_params[0], []


class ArrayFilter(lookups.Transform):
    def __init__(self, *args, conditions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.conditions = _format_conditions(conditions)

    def as_sql(self, compiler, connection, *args, **kwargs):
        lhs, params = compiler.compile(self.lhs)
        return f'arrayFilter(x -> {self.conditions}, {lhs})', params


@NestedField.register_lookup
class ArrayNotEmptyTransform(lookups.Transform):
    lookup_name = "not_empty"
    function = "notEmpty"
    output_field = BooleanField()


class GtStatsDictGet(Func):
    function = 'tuplePlus'
    template = '%(function)s(dictGet("GRCh38/SNV_INDEL/gt_stats_dict", (\'ac_wes\', \'hom_wes\'), %(expressions)s), dictGet("GRCh38/SNV_INDEL/gt_stats_dict", (\'ac_wgs\', \'hom_wgs\'), %(expressions)s))'
    output_field = NamedTupleField([('ac', UInt32Field()), ('hom', UInt32Field())])


class Tuple(Func):
    function = 'tuple'


class TupleConcat(Func):
    function = 'tupleConcat'
