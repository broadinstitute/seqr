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

    def get_prep_lookup(self):
        conditions = [[
            (template[0] if template else '{field} = {value}').format(field=f'x.{field}', value=value)
            for field, (value, *template) in condition_set.items()
        ] for condition_set in self.rhs]  # pylint: disable=access-member-before-definition
        conditions = [
            f'and({", ".join(condition_set)})' if len(condition_set) > 1 else condition_set[0]
            for condition_set in conditions
        ]
        condition = f'or({", ".join(conditions)})' if len(conditions) > 1 else conditions[0]
        self.rhs = f'x -> {condition}'
        return super().get_prep_lookup()

    def process_rhs(self, compiler, connection):
        _, rhs_params = super().process_rhs(compiler, connection)
        return rhs_params[0], []


class GtStatsDictGet(Func):
    function = 'dictGet'
    template = '%(function)s("GRCh38/SNV_INDEL/gt_stats_dict", %(dict_attrs)s, %(expressions)s)'


class Tuple(Func):
    function = 'tuple'


class TupleConcat(Func):
    function = 'tupleConcat'
