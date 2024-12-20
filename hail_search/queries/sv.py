import hail as hl


from hail_search.constants import CONSEQUENCE_SORT, NEW_SV_FIELD, STRUCTURAL_ANNOTATION_FIELD, FAMILY_GUID_FIELD, \
    GENOTYPES_FIELD
from hail_search.queries.base import BaseHailTableQuery, PredictionPath


class SvHailTableQuery(BaseHailTableQuery):

    DATA_TYPE = 'SV_WGS'
    KEY_FIELD = ('variant_id',)

    GENOTYPE_FIELDS = {f.lower(): f for f in ['CN', 'GQ']}
    COMPUTED_GENOTYPE_FIELDS = {
        k: lambda entry, field, *args: entry.concordance[field] for k in ['new_call', 'prev_call', 'prev_num_alt']
    }
    GENOTYPE_QUERY_FIELDS = {'gq_sv': 'GQ', 'gq': None}

    TRANSCRIPTS_FIELD = 'sorted_gene_consequences'
    TRANSCRIPT_CONSEQUENCE_FIELD = 'major_consequence'
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['algorithms']
    BASE_ANNOTATION_FIELDS = {
        'bothsidesSupport': lambda r: r.bothsides_support,
        'chrom': lambda r: r.start_locus.contig.replace('^chr', ''),
        'pos': lambda r: r.start_locus.position,
        'end': lambda r: r.end_locus.position,
        'rg37LocusEnd': lambda r: hl.or_missing(
            hl.is_defined(r.rg37_locus_end), hl.struct(contig=r.rg37_locus_end.contig, position=r.rg37_locus_end.position)
        ),
        **BaseHailTableQuery.BASE_ANNOTATION_FIELDS,
    }
    ENUM_ANNOTATION_FIELDS = {
        TRANSCRIPTS_FIELD: BaseHailTableQuery.ENUM_ANNOTATION_FIELDS['transcripts'],
    }

    POPULATIONS = {
        'sv_callset': {'hemi': None, 'sort': 'callset_af'},
        'gnomad_svs': {'id': 'ID', 'ac': None, 'an': None, 'hom': None, 'hemi': None, 'het': None, 'sort': 'gnomad'},
    }
    POPULATION_FIELDS = {'sv_callset': 'gt_stats'}
    PREDICTION_FIELDS_CONFIG = {
        'strvctvre': PredictionPath('strvctvre', 'score'),
    }
    ANNOTATION_OVERRIDE_FIELDS = [STRUCTURAL_ANNOTATION_FIELD]
    SECONDARY_ANNOTATION_OVERRIDE_FIELDS = [STRUCTURAL_ANNOTATION_FIELD]

    SORTS = {
        **BaseHailTableQuery.SORTS,
        CONSEQUENCE_SORT: lambda r: [hl.min(r.sorted_gene_consequences.map(lambda g: g.major_consequence_id))],
        'size': lambda r: [hl.if_else(
            r.start_locus.contig == r.end_locus.contig, r.start_locus.position - r.end_locus.position, -50,
        )],
    }

    @classmethod
    def _get_sample_type(cls, *args):
        return cls.DATA_TYPE.split('_')[-1]

    def _read_project_table(self, project_guid: str, sample_type: str):
        ht = super()._read_project_table(project_guid, sample_type)
        return ht.annotate_globals(sample_type=sample_type)

    def _filter_annotated_table(self, ht, *args, parsed_intervals=None, exclude_intervals=False, padded_interval=None, gene_ids=None, **kwargs):
        if parsed_intervals and len(parsed_intervals) != len(gene_ids or []):
            interval_filter = hl.array(parsed_intervals).any(lambda interval: hl.if_else(
                ht.start_locus.contig == ht.end_locus.contig,
                interval.overlaps(hl.interval(ht.start_locus, ht.end_locus)),
                interval.contains(ht.start_locus) | interval.contains(ht.end_locus),
            ))
            if exclude_intervals:
                interval_filter = ~interval_filter
            ht = ht.filter(interval_filter)
        if padded_interval:
            padding = int((padded_interval['end'] - padded_interval['start']) * padded_interval['padding'])
            chrom = f"chr{padded_interval['chrom']}"
            ht = ht.filter(hl.all([
                self._locus_in_range(ht.start_locus, chrom, padded_interval['start'], padding),
                self._locus_in_range(ht.end_locus, chrom, padded_interval['end'], padding)
            ]))

        return super()._filter_annotated_table(ht, *args, gene_ids=gene_ids, **kwargs)

    def _locus_in_range(self, locus, chrom, position, padding):
        window = hl.locus(chrom, position, reference_genome=self.GENOME_VERSION).window(padding, padding)
        return window.contains(locus)

    def _parse_annotations(self, annotations, *args, **kwargs):
        parsed_annotations = super()._parse_annotations(annotations, *args, **kwargs)
        parsed_annotations[NEW_SV_FIELD] = (annotations or {}).get(NEW_SV_FIELD)
        return parsed_annotations

    def _get_family_passes_quality_filter(self, quality_filter, ht, parsed_annotations=None, **kwargs):
        passes_quality = super()._get_family_passes_quality_filter(quality_filter, ht)
        if not (parsed_annotations or {}).get(NEW_SV_FIELD):
            return passes_quality

        entries_has_new_call = lambda entries: entries.any(lambda x: x.concordance.new_call)
        if passes_quality is None:
            return entries_has_new_call

        return lambda entries: entries_has_new_call(entries) & passes_quality(entries)

    def _get_annotation_override_filters(self, ht, annotation_overrides):
        annotation_filters = []
        if annotation_overrides.get(STRUCTURAL_ANNOTATION_FIELD):
            allowed_type_ids = self.get_allowed_sv_type_ids(annotation_overrides[STRUCTURAL_ANNOTATION_FIELD])
            if allowed_type_ids:
                annotation_filters.append(hl.set(allowed_type_ids).contains(ht.sv_type_id))

        return annotation_filters

    def get_allowed_sv_type_ids(self, sv_types):
        return self._get_enum_terms_ids('sv_type', None, sv_types)

    def _additional_annotation_fields(self):
        sv_type_enum = self._enums['sv_type']
        insertion_type_id = sv_type_enum.index('INS')
        get_end_chrom = lambda r: hl.or_missing(r.start_locus.contig != r.end_locus.contig, r.end_locus.contig.replace('^chr', ''))
        return {
            'cpxIntervals': lambda r: self._format_enum(
                r, 'cpx_intervals', {'type': sv_type_enum}, annotate_value=lambda val, *args: {
                    'chrom': val.start.contig,
                    'start': val.start.position,
                    'end': val.end.position,
                },
            ),
            # For insertions, end_locus represents the svSourceDetail, otherwise represents the endChrom
            'endChrom': lambda r: hl.or_missing(r.sv_type_id != insertion_type_id, get_end_chrom(r)),
            'svSourceDetail': lambda r: hl.or_missing(r.sv_type_id == insertion_type_id, hl.bind(
                lambda end_chrom: hl.or_missing(hl.is_defined(end_chrom), hl.struct(chrom=end_chrom)),
                get_end_chrom(r),
            )),
        }

    def _import_variant_projects_ht(self, variant_id, sample_data=None, **kwargs):
        project_samples, _ = self._parse_sample_data(sample_data)
        projects_ht = super()._import_variant_projects_ht(variant_id, project_samples=project_samples)

        annotation_fields = self.annotation_fields(include_genotype_overrides=False)
        return projects_ht.select(**{k: annotation_fields[k](projects_ht) for k in [FAMILY_GUID_FIELD, GENOTYPES_FIELD]})
