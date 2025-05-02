from django.db.models import Func

class Array(Func):
    function = 'array'


class ArrayMap(Func):
    function = 'arrayMap'
    template = "%(function)s(x -> %(mapped_expression)s, %(expressions)s)"


class GtStatsDictGet(Func):
    function = 'dictGet'
    template = "%(function)s(seqr.`GRCh38/SNV_INDEL/gt_stats_dict`, %(dict_attrs)s, %(expressions)s)"


class Tuple(Func):
    function = 'tuple'


class TupleConcat(Func):
    function = 'tupleConcat'
