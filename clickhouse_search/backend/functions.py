from clickhouse_backend.models.fields.array import ArrayField, ArrayLookup
from django.db.models import Func, Subquery, lookups, BooleanField, Aggregate
from django.db.models.sql.datastructures import BaseTable, Join


from clickhouse_search.backend.fields import NestedField

class Array(Func):
    function = 'array'


class ArrayConcat(Func):
    function = 'arrayConcat'


class ArrayDistinct(Func):
    function = 'arrayDistinct'


class ArrayIntersect(Func):
    function = 'arrayIntersect'


class ArrayJoin(Func):
    function = 'arrayJoin'


class ArrayFold(Func):
    function = 'arrayFold'
    template = "%(function)s(acc, x -> %(fold_function)s, %(expressions)s, %(acc)s)"


class ArrayMap(Func):
    function = 'arrayMap'
    template = "%(function)s(x -> %(mapped_expression)s, %(expressions)s)"


class ArraySort(Func):
    function = 'arraySort'


class ArraySymmetricDifference(Func):
    function = 'arraySymmetricDifference'


class GroupArray(Aggregate):
    function = 'groupArray'

class GroupArrayArray(Aggregate):
    function = 'groupArrayArray'

class GroupArrayIntersect(Aggregate):
    function = 'groupArrayIntersect'

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


@ArrayField.register_lookup
@NestedField.register_lookup
class ArrayNotEmptyTransform(lookups.Transform):
    lookup_name = "not_empty"
    function = "notEmpty"
    output_field = BooleanField()


class DictGet(Func):
    function = 'dictGet'
    template = '%(function)s("%(dict_name)s", (%(fields)s), %(expressions)s)'


class If(Func):
    function = 'if'
    template = '%(function)s(%(condition)s, %(expressions)s)'


class MapLookup(Func):
    function = 'map'
    template = "%(function)s(%(map_values)s)[%(expressions)s]"
    arg_joiner = "]["


class NullIf(Func):
    function = 'nullIf'


class Plus(Func):
    function = 'plus'


class Tuple(Func):
    function = 'tuple'


class TupleConcat(Func):
    function = 'tupleConcat'


class SubqueryTable(BaseTable):
    def __init__(self, subquery, alias=None):
        self.subquery = Subquery(subquery)
        table_name = subquery.model._meta.db_table
        if not alias:
            alias, _ = subquery.query.table_alias(table_name, create=True)
        super().__init__(table_name, alias)

    def as_sql(self, compiler, connection):
        subquery_sql, params = self.subquery.as_sql(compiler, connection)
        return f'{subquery_sql} AS {self.table_alias}', params


class SubqueryJoin(Join):

    def as_sql(self, compiler, connection):
        qn = compiler.quote_name_unless_alias
        qn2 = connection.ops.quote_name

        on_clause_sql = ' AND '.join([
            f'{qn(self.parent_alias)}.{lhs_col} = {qn(self.table_name)}.{qn2(rhs_col)}'
            for lhs_col, rhs_col in self.join_cols
        ])

        sql = f'{self.join_type} {qn(self.parent_alias)} ON ({on_clause_sql})'
        return sql, []


class CrossJoin(Join):

    join_type = None
    parent_alias = None
    table_alias = None
    join_field = None
    join_cols = []
    nullable = False
    filtered_relation = None

    def __init__(self, query, alias, join_query, join_alias):
        self.main_table = SubqueryTable(query, alias)
        self.join_table = SubqueryTable(join_query, join_alias)
        self.table_name = alias

    def as_sql(self, compiler, connection):
        subquery_sql, params = self.main_table.as_sql(compiler, connection)
        join_subquery_sql, join_params = self.join_table.as_sql(compiler, connection)
        return f'{subquery_sql} CROSS JOIN {join_subquery_sql}', params + join_params
