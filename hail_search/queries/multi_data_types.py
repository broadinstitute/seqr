import hail as hl

from hail_search.constants import CONSEQUENCE_SORT, OMIM_SORT
from hail_search.queries.base import BaseHailTableQuery
from hail_search.queries.variants import VariantHailTableQuery
from hail_search.queries.sv import SvHailTableQuery
from hail_search.queries.gcnv import GcnvHailTableQuery

QUERY_CLASS_MAP = {cls.DATA_TYPE: cls for cls in [VariantHailTableQuery, SvHailTableQuery, GcnvHailTableQuery]}


class MultiDataTypeHailTableQuery(BaseHailTableQuery):

    def __init__(self, sample_data, *args, **kwargs):
        self._data_type_queries = {k: QUERY_CLASS_MAP[k](v, *args, **kwargs) for k, v in sample_data.items()}
        super().__init__(sample_data, *args, **kwargs)

    def _load_filtered_table(self, *args, **kwargs):
        pass

    def format_search_ht(self):
        ht = None
        for data_type, query in self._data_type_queries.items():
            dt_ht = query.format_search_ht()
            merged_sort_expr = self._merged_sort_expr(data_type, dt_ht)
            if merged_sort_expr is not None:
                dt_ht = dt_ht.annotate(_sort=merged_sort_expr)
            dt_ht = dt_ht.select('_sort', **{data_type: dt_ht.row})
            if ht is None:
                ht = dt_ht
            else:
                ht = ht.join(dt_ht, 'outer')
                ht = ht.transmute(_sort=hl.or_else(ht._sort, ht._sort_1))
        return ht

    def _merged_sort_expr(self, data_type, ht):
        # Certain sorts have an extra element for variant-type data, so need to add an element for SV data
        if not data_type.startswith('SV'):
            return None

        if self._sort == CONSEQUENCE_SORT:
            return hl.array([hl.float64(4.5)]).extend(ht._sort.map(hl.float64))
        elif self._sort == OMIM_SORT:
            return hl.array([hl.int64(0)]).extend(ht._sort)
        elif self._sort_metadata:
            return ht._sort[:1].extend(ht._sort)

        return None

    def _format_collected_rows(self, collected):
        return super()._format_collected_rows([
            next(row.get(data_type) for data_type in self._data_type_queries if row.get(data_type))
            for row in collected
        ])

    def format_gene_counts_ht(self):
        hts = [query.format_gene_counts_ht() for query in self._data_type_queries.values()]
        ht = hts[0]
        for dt_ht in hts[1:]:
            ht = ht.join(dt_ht, 'outer')
            ht = ht.transmute(**{k: hl.or_else(ht[k], ht[f'{k}_1']) for k in ['gene_ids', 'families']})
        return ht
