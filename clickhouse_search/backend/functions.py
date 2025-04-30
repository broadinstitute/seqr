from django.db.models import Func

class Array(Func):
    function = 'array'


class ArrayMap(Func):
    function = 'arrayMap'
    template = "%(function)s(x -> %(mapped_expression)s, %(expressions)s)"


class Tuple(Func):
    function = 'tuple'
