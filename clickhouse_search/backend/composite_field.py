import json

from django.core import checks
from django.db.models import NOT_PROVIDED, Field
from django.db.models.expressions import Expression, Col

from django.utils.functional import cached_property


class ColPairs(Expression):
    def __init__(self, alias, targets, sources, output_field):
        super().__init__(output_field=output_field)
        self.alias = alias
        self.targets = targets
        self.sources = sources

    def __len__(self):
        return len(self.targets)

    def __iter__(self):
        return iter(self.get_cols())

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.alias!r}, {self.targets!r}, "
            f"{self.sources!r}, {self.output_field!r})"
        )

    def get_cols(self):
        return [
            Col(self.alias, target, source)
            for target, source in zip(self.targets, self.sources)
        ]

    def get_source_expressions(self):
        return self.get_cols()

    def set_source_expressions(self, exprs):
        assert all(isinstance(expr, Col) and expr.alias == self.alias for expr in exprs)
        self.targets = [col.target for col in exprs]
        self.sources = [col.field for col in exprs]

    def as_sql(self, compiler, connection):
        cols_sql = []
        cols_params = []
        cols = self.get_cols()

        for col in cols:
            sql, params = col.as_sql(compiler, connection)
            cols_sql.append(sql)
            cols_params.extend(params)

        return ", ".join(cols_sql), cols_params

    def relabeled_clone(self, relabels):
        return self.__class__(
            relabels.get(self.alias, self.alias), self.targets, self.sources, self.field
        )

    def resolve_expression(self, *args, **kwargs):
        return self

    def select_format(self, compiler, sql, params):
        return sql, params

class AttributeSetter:
    def __init__(self, name, value):
        setattr(self, name, value)


class CompositeAttribute:
    def __init__(self, field):
        self.field = field

    @property
    def attnames(self):
        return [field.attname for field in self.field.fields]

    def __get__(self, instance, cls=None):
        return tuple(getattr(instance, attname) for attname in self.attnames)

    def __set__(self, instance, values):
        attnames = self.attnames
        length = len(attnames)

        if values is None:
            values = (None,) * length

        if not isinstance(values, (list, tuple)):
            raise ValueError(f"{self.field.name!r} must be a list or a tuple.")
        if length != len(values):
            raise ValueError(f"{self.field.name!r} must have {length} elements.")

        for attname, value in zip(attnames, values):
            setattr(instance, attname, value)


class CompositePrimaryKey(Field):
    descriptor_class = CompositeAttribute

    def __init__(self, *args, **kwargs):
        if (
            not args
            or not all(isinstance(field, str) for field in args)
            or len(set(args)) != len(args)
        ):
            raise ValueError("CompositePrimaryKey args must be unique strings.")
        if len(args) == 1:
            raise ValueError("CompositePrimaryKey must include at least two fields.")
        if kwargs.get("default", NOT_PROVIDED) is not NOT_PROVIDED:
            raise ValueError("CompositePrimaryKey cannot have a default.")
        if kwargs.get("db_default", NOT_PROVIDED) is not NOT_PROVIDED:
            raise ValueError("CompositePrimaryKey cannot have a database default.")
        if kwargs.get("db_column", None) is not None:
            raise ValueError("CompositePrimaryKey cannot have a db_column.")
        if kwargs.setdefault("editable", False):
            raise ValueError("CompositePrimaryKey cannot be editable.")
        if not kwargs.setdefault("primary_key", True):
            raise ValueError("CompositePrimaryKey must be a primary key.")
        if not kwargs.setdefault("blank", True):
            raise ValueError("CompositePrimaryKey must be blank.")

        self.field_names = args
        super().__init__(**kwargs)

    def deconstruct(self):
        # args is always [] so it can be ignored.
        name, path, _, kwargs = super().deconstruct()
        return name, path, self.field_names, kwargs

    @cached_property
    def fields(self):
        meta = self.model._meta
        return tuple(meta.get_field(field_name) for field_name in self.field_names)

    @cached_property
    def columns(self):
        return tuple(field.column for field in self.fields)

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=private_only)
        cls._meta.pk = self
        setattr(cls, self.attname, self.descriptor_class(self))

    def get_attname_column(self):
        return self.get_attname(), None

    def __iter__(self):
        return iter(self.fields)

    def __len__(self):
        return len(self.field_names)

    @cached_property
    def cached_col(self):
        return ColPairs(self.model._meta.db_table, self.fields, self.fields, self)

    def get_col(self, alias, output_field=None):
        if alias == self.model._meta.db_table and (
            output_field is None or output_field == self
        ):
            return self.cached_col

        return ColPairs(alias, self.fields, self.fields, output_field)

    def get_pk_value_on_save(self, instance):
        values = []

        for field in self.fields:
            value = field.value_from_object(instance)
            if value is None:
                value = field.get_pk_value_on_save(instance)
            values.append(value)

        return tuple(values)

    def _check_field_name(self):
        if self.name == "pk":
            return []
        return [
            checks.Error(
                "'CompositePrimaryKey' must be named 'pk'.",
                obj=self,
                id="fields.E013",
            )
        ]

    def value_to_string(self, obj):
        values = []
        vals = self.value_from_object(obj)
        for field, value in zip(self.fields, vals):
            obj = AttributeSetter(field.attname, value)
            values.append(field.value_to_string(obj))
        return json.dumps(values, ensure_ascii=False)

    def to_python(self, value):
        if isinstance(value, str):
            # Assume we're deserializing.
            vals = json.loads(value)
            value = [
                field.to_python(val)
                for field, val in zip(self.fields, vals, strict=True)
            ]
        return value


def unnest(fields):
    result = []

    for field in fields:
        if isinstance(field, CompositePrimaryKey):
            result.extend(field.fields)
        else:
            result.append(field)

    return result