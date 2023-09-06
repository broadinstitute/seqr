from hail_search.queries.base import BaseHailTableQuery
from hail_search.queries.variants import VariantHailTableQuery
from hail_search.queries.sv import SvHailTableQuery
from hail_search.queries.gcnv import GcnvHailTableQuery

QUERY_CLASS_MAP = {cls.DATA_TYPE: cls for cls in [VariantHailTableQuery, SvHailTableQuery, GcnvHailTableQuery]}


class MultiDataTypeHailTableQuery(BaseHailTableQuery):

    def __init__(self, sample_data, *args, **kwargs):
        self._data_type_queries = {k: QUERY_CLASS_MAP[k](v, *args, **kwargs) for k, v in sample_data.items()}
        super().__init__(sample_data, *args, **kwargs)

    def _load_filtered_table(self, sample_data, **kwargs):
        pass

    def format_search_ht(self):
        ht = None
        for data_type, query in self._data_type_queries.items():
            dt_ht = query.format_search_ht()
            dt_ht = dt_ht.select('_sort', **{data_type: dt_ht.row})
            if ht is None:
                ht = dt_ht
            else:
                ht = ht.join(dt_ht, 'outer')
                ht = ht.transmute(_sort=hl.or_else(ht._sort, ht._sort_1))
        return ht

    def _format_collected_row(self, ht):
        return hl.array(self._data_type_queries.keys()).map(
            lambda data_type: ht[data_type]).find(lambda x: hl.is_defined(x))

    # TODO gene counts

    # TODO merged sorts
