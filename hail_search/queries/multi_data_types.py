import hail as hl

from hail_search.constants import ALT_ALT, REF_REF, CONSEQUENCE_SORT, OMIM_SORT, GROUPED_VARIANTS_FIELD, GENOME_VERSION_GRCh38
from hail_search.queries.base import BaseHailTableQuery
from hail_search.queries.mito import MitoHailTableQuery
from hail_search.queries.snv_indel import SnvIndelHailTableQuery
from hail_search.queries.snv_indel_37 import SnvIndelHailTableQuery37
from hail_search.queries.sv import SvHailTableQuery
from hail_search.queries.gcnv import GcnvHailTableQuery

QUERY_CLASSES = [SnvIndelHailTableQuery, SnvIndelHailTableQuery37, MitoHailTableQuery, SvHailTableQuery, GcnvHailTableQuery]
QUERY_CLASS_MAP = {(cls.DATA_TYPE, cls.GENOME_VERSION): cls for cls in QUERY_CLASSES}
SNV_INDEL_DATA_TYPE = SnvIndelHailTableQuery.DATA_TYPE


class MultiDataTypeHailTableQuery(BaseHailTableQuery):

    LOADED_GLOBALS = True

    def __init__(self, sample_data, *args, **kwargs):
        self._data_type_queries = {
            k: QUERY_CLASS_MAP[(k, GENOME_VERSION_GRCh38)](v, *args, override_comp_het_alt=k == SNV_INDEL_DATA_TYPE, **kwargs)
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
            self.max_unaffected_samples = min(variant_query.max_unaffected_samples, sv_query.max_unaffected_samples)
            merged_ht = self._filter_data_type_comp_hets(variant_query, variant_families, sv_query)
            if merged_ht is not None:
                self._comp_het_hts[data_type] = merged_ht.key_by()

    def _filter_data_type_comp_hets(self, variant_query, variant_families, sv_query):
        variant_ht = variant_query.unfiltered_comp_het_ht
        sv_ht = sv_query.unfiltered_comp_het_ht
        sv_type_del_ids = sv_query.get_allowed_sv_type_ids([f'{getattr(sv_query, "SV_TYPE_PREFIX", "")}DEL'])
        self._sv_type_del_id = list(sv_type_del_ids)[0] if sv_type_del_ids else None

        sv_families = hl.eval(sv_ht.family_guids)
        overlapped_families = list(set(variant_families).intersection(sv_families))
        if not overlapped_families:
            return None

        if variant_families != sv_families:
            variant_ht = self._family_filtered_ch_ht(variant_ht, overlapped_families, variant_families)
            sv_ht = self._family_filtered_ch_ht(sv_ht, overlapped_families, sv_families)
        else:
            overlapped_families = variant_families

        variant_samples_by_family = variant_query.entry_samples_by_family_guid
        sv_samples_by_family = sv_query.entry_samples_by_family_guid
        if any(f for f in overlapped_families if variant_samples_by_family[f] != sv_samples_by_family[f]):
            sv_sample_indices = hl.array([[
                sv_samples_by_family[f].index(s) if s in sv_samples_by_family[f] else None
                for s in variant_samples_by_family[f]
            ] for f in overlapped_families])
            sv_ht = sv_ht.annotate(family_entries=hl.enumerate(sv_sample_indices).starmap(
                lambda family_i, indices: hl.bind(
                    lambda family_entry: hl.or_missing(
                        hl.is_defined(family_entry),
                        indices.map(lambda sample_i: family_entry[sample_i]),
                    ),
                    sv_ht.family_entries[family_i],
                )
            ))

        variant_ch_ht = variant_ht.group_by('gene_ids').aggregate(v1=hl.agg.collect(variant_ht.row))
        sv_ch_ht = sv_ht.group_by('gene_ids').aggregate(v2=hl.agg.collect(sv_ht.row))

        variants = variant_ch_ht.join(sv_ch_ht).collect(_localize=False)
        variants = variants.flatmap(lambda gvs: hl.rbind(
            hl.set({gvs.gene_ids}),
            lambda comp_het_gene_ids: gvs.v1.flatmap(
                lambda v1: gvs.v2.map(lambda v2: hl.struct(
                    v1=v1.annotate(comp_het_gene_ids=comp_het_gene_ids),
                    v2=v2.annotate(comp_het_gene_ids=comp_het_gene_ids),
                ))
            )
        ))
        variants = self._filter_comp_het_families(variants, set_secondary_annotations=False)
        return hl.Table.parallelize(variants)

    @staticmethod
    def _family_filtered_ch_ht(ht, overlapped_families, families):
        family_indices = hl.array([families.index(family_guid) for family_guid in overlapped_families])
        return ht.annotate(family_entries=family_indices.map(lambda i: ht.family_entries[i]))

    def _is_valid_comp_het_family(self, v1, v2, family_index):
        is_valid = super()._is_valid_comp_het_family(v1, v2, family_index)

        # SNPs overlapped by trans deletions may be incorrectly called as hom alt, and should be
        # considered comp hets with said deletions. Any other hom alt variants are not valid comp hets
        entries_1 = v1.family_entries[family_index]
        is_allowed_hom_alt = entries_1.all(lambda g: ~self.GENOTYPE_QUERY_MAP[ALT_ALT](g.GT)) | hl.all([
            v2.sv_type_id == self._sv_type_del_id,
            v2.start_locus.position <= v1.locus.position,
            v1.locus.position <= v2.end_locus.position,
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
            dt_ht = self._merged_sort(data_type, dt_ht)
            hts.append(dt_ht.select('_sort', **{data_type: dt_ht.row}))

        for data_type, ch_ht in self._comp_het_hts.items():
            ch_ht = ch_ht.annotate(
                v1=self._format_comp_het_result(ch_ht.v1, SNV_INDEL_DATA_TYPE),
                v2=self._format_comp_het_result(ch_ht.v2, data_type),
            )
            hts.append(ch_ht.select(
                _sort=hl.sorted([ch_ht.v1._sort.map(hl.float64), ch_ht.v2._sort.map(hl.float64)])[0],
                **{f'comp_het_{data_type}': ch_ht.row},
            ))

        ht = hts[0]
        for sub_ht in hts[1:]:
            ht = ht.union(sub_ht, unify=True)

        return ht

    def _format_comp_het_result(self, v, data_type):
        result = self._data_type_queries[data_type]._format_results(v)
        return self._merged_sort(data_type, result)

    def _merged_sort(self, data_type, ht):
        # Certain sorts have an extra element for variant-type data, so need to add an element for SV data
        if not data_type.startswith('SV'):
            return ht

        sort_expr = None
        if self._sort == CONSEQUENCE_SORT:
            sort_expr = hl.array([hl.float64(4.5)]).extend(ht._sort.map(hl.float64))
        elif self._sort == OMIM_SORT:
            sort_expr = hl.array([hl.int64(0)]).extend(ht._sort)
        elif self._sort_metadata:
            sort_expr = ht._sort[:1].extend(ht._sort)

        if sort_expr is not None:
            ht = ht.annotate(_sort=sort_expr)

        return ht

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
