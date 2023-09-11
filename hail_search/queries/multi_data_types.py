import hail as hl

from hail_search.constants import ALT_ALT, CONSEQUENCE_SORT, OMIM_SORT
from hail_search.queries.base import BaseHailTableQuery
from hail_search.queries.variants import VariantHailTableQuery
from hail_search.queries.sv import SvHailTableQuery
from hail_search.queries.gcnv import GcnvHailTableQuery

QUERY_CLASS_MAP = {cls.DATA_TYPE: cls for cls in [VariantHailTableQuery, SvHailTableQuery, GcnvHailTableQuery]}
VARIANT_DATA_TYPE = VariantHailTableQuery.DATA_TYPE


class MultiDataTypeHailTableQuery(BaseHailTableQuery):

    def __init__(self, sample_data, *args, **kwargs):
        self._data_type_queries = {
            k: QUERY_CLASS_MAP[k](v, *args, override_comp_het_alt=k == VARIANT_DATA_TYPE, **kwargs)
            for k, v in sample_data.items()
        }
        self._comp_het_hts = []
        self._sv_type_del_id = None
        super().__init__(sample_data, *args, **kwargs)

    def _load_filtered_table(self, *args, **kwargs):
        variant_query = self._data_type_queries.get(VARIANT_DATA_TYPE)
        sv_queries = [
            self._data_type_queries[data_type] for data_type in [SvHailTableQuery.DATA_TYPE, GcnvHailTableQuery.DATA_TYPE]
            if data_type in self._data_type_queries
        ]
        if not (self._has_comp_het_search and variant_query is not None and sv_queries):
            return

        variant_ht = variant_query.unfiltered_comp_het_ht
        variant_families = hl.eval(variant_ht.family_guids)
        for sv_query in sv_queries:
            merged_ht = self._filter_data_type_comp_hets(variant_ht, variant_families, sv_query)
            if merged_ht is not None:
                self._comp_het_hts.append(merged_ht)

    def _filter_data_type_comp_hets(self, variant_ht, variant_families, sv_query):
        sv_ht = sv_query.unfiltered_comp_het_ht
        sv_type_del_ids = sv_query.get_allowed_sv_type_ids(['DEL'])
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
        is_allowed_hom_alt = entries_1.all(lambda g: ~self.GENOTYPE_QUERY_MAP[ALT_ALT](g.GT))
        if self._sv_type_del_id is not None:
            is_allowed_hom_alt |= hl.all([
                ch_ht.v2.sv_type_id == self._sv_type_del_id,
                ch_ht.v2.start_locus.position <= ch_ht.v1.locus.position,
                ch_ht.v1.locus.position <= ch_ht.v2.end_locus.position,
            ])
        return is_valid & is_allowed_hom_alt

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
        # TODO add _comp_het_hts
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
        # TODO add _comp_het_hts
        return super()._format_collected_rows([
            next(row.get(data_type) for data_type in self._data_type_queries if row.get(data_type))
            for row in collected
        ])

    def format_gene_counts_ht(self):
        # TODO add _comp_het_hts
        hts = [query.format_gene_counts_ht() for query in self._data_type_queries.values()]
        ht = hts[0]
        for dt_ht in hts[1:]:
            ht = ht.join(dt_ht, 'outer')
            ht = ht.transmute(**{k: hl.or_else(ht[k], ht[f'{k}_1']) for k in ['gene_ids', 'families']})
        return ht
