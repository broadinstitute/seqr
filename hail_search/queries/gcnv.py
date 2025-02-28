import hail as hl

from hail_search.constants import COMP_HET_ALT, HAS_ALT, HAS_REF, REF_REF, FILTERED_GENE_TRANSCRIPTS, \
    ALLOWED_TRANSCRIPTS, ALLOWED_SECONDARY_TRANSCRIPTS
from hail_search.queries.sv import SvHailTableQuery


class GcnvHailTableQuery(SvHailTableQuery):

    DATA_TYPE = 'SV_WES'
    SV_TYPE_PREFIX = 'gCNV_'

    #  gCNV data has no ref/ref calls so a missing entry indicates ref/ref
    GENOTYPE_QUERY_MAP = {
        **SvHailTableQuery.GENOTYPE_QUERY_MAP,
        REF_REF: hl.is_missing,
        HAS_REF: lambda gt: hl.is_missing(gt) | gt.is_het_ref(),
        HAS_ALT: hl.is_defined,
        COMP_HET_ALT: hl.is_defined,
    }
    MISSING_NUM_ALT = 0

    GENOTYPE_FIELDS = {
        **SvHailTableQuery.GENOTYPE_FIELDS,
        **{f.lower(): f for f in ['QS', 'defragged']},
    }
    del GENOTYPE_FIELDS['gq']
    GENOTYPE_QUERY_FIELDS = {}
    GENOTYPE_OVERRIDE_FIELDS = {
        'start': (hl.min, lambda r: r.start_locus.position),
        'end': (hl.max, lambda r: r.end_locus.position),
        'num_exon': (hl.max, lambda r: r.num_exon),
        'gene_ids': (
            lambda entry_gene_ids: entry_gene_ids.fold(lambda s1, s2: s1.union(s2), hl.empty_set(hl.tstr)),
            lambda r: hl.missing(hl.tset(hl.tstr)),
        ),
    }
    COMPUTED_GENOTYPE_FIELDS = {
        **SvHailTableQuery.COMPUTED_GENOTYPE_FIELDS,
        **{k: lambda entry, field, r: hl.or_missing(
            hl.is_missing(r[field]) | (r[field] != entry[f'sample_{field}']), entry[f'sample_{field}']
        ) for k in GENOTYPE_OVERRIDE_FIELDS.keys()},
    }
    COMPUTED_GENOTYPE_FIELDS['prev_overlap'] = COMPUTED_GENOTYPE_FIELDS.pop('prev_num_alt')

    CORE_FIELDS = SvHailTableQuery.CORE_FIELDS[:-1]
    BASE_ANNOTATION_FIELDS = {
        **SvHailTableQuery.BASE_ANNOTATION_FIELDS,
        'pos': lambda r: r.start,
        'end': lambda r: r.end,
        'numExon': lambda r: r.num_exon,
    }
    del BASE_ANNOTATION_FIELDS['bothsidesSupport']

    TRANSCRIPTS_ENUM_FIELD = SvHailTableQuery.ENUM_ANNOTATION_FIELDS[SvHailTableQuery.TRANSCRIPTS_FIELD]
    ENUM_ANNOTATION_FIELDS = {SvHailTableQuery.TRANSCRIPTS_FIELD: {
        **TRANSCRIPTS_ENUM_FIELD,
        'format_array_values': lambda values, r: GcnvHailTableQuery.TRANSCRIPTS_ENUM_FIELD['format_array_values'](
            hl.if_else(hl.is_missing(r.gene_ids), values, values.filter(lambda t: r.gene_ids.contains(t.geneId))), r,
        ),
    }}

    POPULATIONS = {k: v for k, v in SvHailTableQuery.POPULATIONS.items() if k != 'gnomad_svs'}

    @classmethod
    def _get_genotype_override_field(cls, r, field):
        agg, get_default = cls.GENOTYPE_OVERRIDE_FIELDS[field]
        sample_field = f'sample_{field}'
        entries = r.family_entries.flatmap(lambda x: x)
        return hl.if_else(
            entries.any(lambda g: hl.is_defined(g.GT) & hl.is_missing(g[sample_field])),
            get_default(r), agg(entries.map(lambda g: g[sample_field]))
        )

    def _format_results(self, ht, *args, include_genotype_overrides=True, **kwargs):
        ht = ht.annotate(**{
            k: self._get_genotype_override_field(ht, k) if include_genotype_overrides
            else self.GENOTYPE_OVERRIDE_FIELDS[k][1](ht)
            for k in self.GENOTYPE_OVERRIDE_FIELDS
        })
        return super()._format_results(ht, *args, **kwargs)

    def get_allowed_sv_type_ids(self, sv_types):
        return super().get_allowed_sv_type_ids([
            type.replace(self.SV_TYPE_PREFIX, '') for type in sv_types if type.startswith(self.SV_TYPE_PREFIX)
        ])

    def _annotate_families_table_annotations(self, families_ht, annotations_ht, is_comp_het=False):
        ht = super()._annotate_families_table_annotations(families_ht, annotations_ht)
        transcript_fields = [
            transcript_field for transcript_field in [
                ALLOWED_TRANSCRIPTS, ALLOWED_SECONDARY_TRANSCRIPTS, FILTERED_GENE_TRANSCRIPTS,
            ] if hasattr(ht, transcript_field)
        ]
        if not transcript_fields:
            return ht

        ht = ht.annotate(all_gene_ids=self._get_genotype_override_field(ht, 'gene_ids'))
        for transcript_field in transcript_fields:
            transcript_has_gene = lambda t: hl.is_missing(ht.all_gene_ids) | ht.all_gene_ids.contains(t.gene_id)
            if transcript_field == FILTERED_GENE_TRANSCRIPTS:
                ht = ht.filter(ht[transcript_field].any(transcript_has_gene))
            else:
                ht = ht.annotate(**{transcript_field: ht[transcript_field].filter(transcript_has_gene)})
                if not is_comp_het:
                    #  Will trigger re-filtering the ht for allowed annotations
                    self._has_secondary_annotations = True

        return ht.drop('all_gene_ids')

    def _filter_by_gene_ids(self, ht, gene_ids):
        if not hasattr(ht, 'family_entries'):
            return super()._filter_by_gene_ids(ht, gene_ids)

        #  Gene and annotation filters should only consider genes present in the genotype override gene_ids
        row_gene_ids = self._gene_ids_expr(ht)

        if gene_ids is None:
            return self._annotate_filtered_gene_transcripts(ht, row_gene_ids)

        return super()._filter_by_gene_ids(ht, gene_ids.intersection(row_gene_ids))

    @classmethod
    def _gene_ids_expr(cls, ht, filtered_genes_only=False):
        gene_ids_expr = super()._gene_ids_expr(ht)
        if filtered_genes_only:
            return gene_ids_expr
        return hl.or_else(
            cls._get_genotype_override_field(ht, 'gene_ids'),
            gene_ids_expr,
        )

    def _additional_annotation_fields(self):
        return {}
