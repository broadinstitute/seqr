import hail as hl

from hail_search.constants import ALT_ALT, REF_REF, CONSEQUENCE_SORT, OMIM_SORT, GROUPED_VARIANTS_FIELD
from hail_search.queries.base import BaseHailTableQuery
from hail_search.queries.mito import MitoHailTableQuery
from hail_search.queries.snv_indel import SnvIndelHailTableQuery
from hail_search.queries.sv import SvHailTableQuery
from hail_search.queries.gcnv import GcnvHailTableQuery

QUERY_CLASS_MAP = {
    cls.DATA_TYPE: cls for cls in [SnvIndelHailTableQuery, MitoHailTableQuery, SvHailTableQuery, GcnvHailTableQuery]
}
SNV_INDEL_DATA_TYPE = SnvIndelHailTableQuery.DATA_TYPE


class MultiDataTypeHailTableQuery(BaseHailTableQuery):

    def __init__(self, sample_data, *args, **kwargs):
        self._data_type_queries = {
            k: QUERY_CLASS_MAP[k](v, *args, override_comp_het_alt=k == SNV_INDEL_DATA_TYPE, **kwargs)
            for k, v in sample_data.items()
        }
        self._comp_het_hts = {}
        self._sv_type_del_id = None
        self._current_sv_data_type = None
        super().__init__(sample_data, *args, **kwargs)

    def _load_filtered_table(self, *args, **kwargs):
        variant_query = self._data_type_queries.get(SNV_INDEL_DATA_TYPE)
        sv_data_types = [
            data_type for data_type in [SvHailTableQuery.DATA_TYPE, GcnvHailTableQuery.DATA_TYPE]
            if data_type in self._data_type_queries
        ]
        if not (self._has_comp_het_search and variant_query is not None and sv_data_types):
            return

        variant_ht = variant_query.unfiltered_comp_het_ht
        variant_families = hl.eval(variant_ht.family_guids)
        for data_type in sv_data_types:
            self._current_sv_data_type = data_type
            sv_query = self._data_type_queries[data_type]
            merged_ht = self._filter_data_type_comp_hets(variant_ht, variant_families, sv_query)
            if merged_ht is not None:
                self._comp_het_hts[data_type] = merged_ht.key_by()

    def _filter_data_type_comp_hets(self, variant_ht, variant_families, sv_query):
        sv_ht = sv_query.unfiltered_comp_het_ht
        sv_type_del_ids = sv_query.get_allowed_sv_type_ids([f'{getattr(sv_query, "SV_TYPE_PREFIX", "")}DEL'])
        self._sv_type_del_id = list(sv_type_del_ids)[0] if sv_type_del_ids else None

        sv_families = hl.eval(sv_ht.family_guids)
        overlapped_families = list(set(variant_families).intersection(sv_families))
        if not overlapped_families:
            return None

        variant_ch_ht = self._family_filtered_ch_ht(variant_ht, overlapped_families, variant_families, 'v1')
        sv_ch_ht = self._family_filtered_ch_ht(sv_ht, overlapped_families, sv_families, 'v2')

        ch_ht = variant_ch_ht.join(sv_ch_ht)
        return self._filter_grouped_compound_hets(ch_ht)

    @staticmethod
    def _family_filtered_ch_ht(ht, overlapped_families, families, key):
        family_indices = hl.array([families.index(family_guid) for family_guid in overlapped_families])
        ht = ht.annotate(comp_het_family_entries=family_indices.map(lambda i: ht.comp_het_family_entries[i]))
        return ht.group_by('gene_ids').aggregate(**{key: hl.agg.collect(ht.row)})

    def _is_valid_comp_het_family(self, ch_ht, entries_1, entries_2):
        is_valid = super()._is_valid_comp_het_family(ch_ht, entries_1, entries_2)

        # SNPs overlapped by trans deletions may be incorrectly called as hom alt, and should be
        # considered comp hets with said deletions. Any other hom alt variants are not valid comp hets
        is_allowed_hom_alt = entries_1.all(lambda g: ~self.GENOTYPE_QUERY_MAP[ALT_ALT](g.GT)) | hl.all([
            ch_ht.v2.sv_type_id == self._sv_type_del_id,
            ch_ht.v2.start_locus.position <= ch_ht.v1.locus.position,
            ch_ht.v1.locus.position <= ch_ht.v2.end_locus.position,
        ])
        return is_valid & is_allowed_hom_alt

    def _comp_het_entry_has_ref(self, gt1, gt2):
        variant_query = self._data_type_queries[SNV_INDEL_DATA_TYPE]
        sv_query = self._data_type_queries[self._current_sv_data_type]
        return [variant_query.GENOTYPE_QUERY_MAP[REF_REF](gt1), sv_query.GENOTYPE_QUERY_MAP[REF_REF](gt2)]

    def format_search_ht(self):
        hts = []
        for data_type, query in self._data_type_queries.items():
            dt_ht = query.format_search_ht()
            if dt_ht is None:
                continue
            merged_sort_expr = self._merged_sort_expr(data_type, dt_ht)
            if merged_sort_expr is not None:
                dt_ht = dt_ht.annotate(_sort=merged_sort_expr)
            hts.append(dt_ht.select('_sort', **{data_type: dt_ht.row}))

        for data_type, ch_ht in self._comp_het_hts.items():
            ch_ht = ch_ht.annotate(
                v1=self._format_comp_het_result(ch_ht.v1, SNV_INDEL_DATA_TYPE),
                v2=self._format_comp_het_result(ch_ht.v2, data_type),
            )
            hts.append(ch_ht.select(
                _sort=hl.sorted([ch_ht.v1._sort, ch_ht.v2._sort])[0],
                **{f'comp_het_{data_type}': ch_ht.row},
            ))

        ht = hts[0]
        for sub_ht in hts[1:]:
            ht = ht.union(sub_ht, unify=True)

        return ht

    def _format_comp_het_result(self, v, data_type):
        return self._data_type_queries[data_type]._format_results(v)

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
        data_types = [*self._data_type_queries, *[f'comp_het_{data_type}' for data_type in self._comp_het_hts]]
        return super()._format_collected_rows([self._format_collected_row(row, data_types) for row in collected])

    @staticmethod
    def _format_collected_row( row, data_types):
        data_type = next(data_type for data_type in data_types if row.get(data_type))
        formatted_row = row.get(data_type)
        if 'comp_het' in data_type:
            formatted_row = {GROUPED_VARIANTS_FIELD: sorted([formatted_row.v1, formatted_row.v2], key=lambda x: x._sort)}
        return formatted_row

    def format_gene_count_hts(self):
        hts = []
        for query in self._data_type_queries.values():
            hts += query.format_gene_count_hts()
        for data_type, ch_ht in self._comp_het_hts.items():
            hts += [
                self._comp_het_gene_count_ht(ch_ht, 'v1', SNV_INDEL_DATA_TYPE),
                self._comp_het_gene_count_ht(ch_ht, 'v2', data_type)
            ]
        return hts

    def _comp_het_gene_count_ht(self, ht, field, data_type):
        selects = {
            **self._gene_count_selects(),
            'gene_ids': self._data_type_queries[data_type]._gene_ids_expr,
        }
        return ht.select(**{k: v(ht[field]) for k, v in selects.items()})
