from clickhouse_backend.models.fields.array import ArrayField, ArrayLookup
from django.db.models import Func

from clickhouse_search.backend.fields import NestedField

class Array(Func):
    function = 'array'


class ArrayMap(Func):
    function = 'arrayMap'
    template = "%(function)s(x -> %(mapped_expression)s, %(expressions)s)"


@NestedField.register_lookup
@ArrayField.register_lookup
class ArrayExists(ArrayLookup):
    lookup_name = "array_exists"
    function = "arrayExists"
    swap_args = True
    prepare_rhs = False

    @staticmethod
    def _format_condition(filters):
        conditions = [
            (template[0] if template else '{field} = {value}').format(field=f'x.{field}', value=value)
            for field, (value, *template) in filters.items()  # pylint: disable=access-member-before-definition
        ]
        return f'and({", ".join(conditions)})' if len(conditions) > 1 else conditions[0]

    def get_prep_lookup(self):
        or_filters = self.rhs.get('OR', [self.rhs]) # pylint: disable=access-member-before-definition
        conditions = [self._format_condition(f) for f in or_filters]
        condition = f'or({", ".join(conditions)})' if len(conditions) > 1 else conditions[0]
        self.rhs = f'x -> {condition}'
        return super().get_prep_lookup()

    def process_rhs(self, compiler, connection):
        _, rhs_params = super().process_rhs(compiler, connection)
        return rhs_params[0], []


class GtStatsDictGet(Func):
    function = 'tuplePlus'
    template = '%(function)s(dictGet("GRCh38/SNV_INDEL/gt_stats_dict", %(dict_attrs_1)s, %(expressions)s), dictGet("GRCh38/SNV_INDEL/gt_stats_dict", %(dict_attrs_2)s, %(expressions)s))'


class Tuple(Func):
    function = 'tuple'


class TupleConcat(Func):
    function = 'tupleConcat'
