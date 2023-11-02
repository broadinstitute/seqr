import hail as hl

from hail_search.constants import ABSENT_PATH_SORT_OFFSET, CLINVAR_KEY, CLINVAR_LIKELY_PATH_FILTER, CLINVAR_PATH_FILTER, \
    CLINVAR_PATH_RANGES, CLINVAR_PATH_SIGNIFICANCES, ALLOWED_TRANSCRIPTS, ALLOWED_SECONDARY_TRANSCRIPTS, PATHOGENICTY_SORT_KEY, CONSEQUENCE_SORT, \
    PATHOGENICTY_HGMD_SORT_KEY
from hail_search.queries.base import BaseHailTableQuery, PredictionPath, QualityFilterFormat


class MitoHailTableQuery(BaseHailTableQuery):

    DATA_TYPE = 'MITO'
    KEY_FIELD = ('locus', 'alleles')

    TRANSCRIPTS_FIELD = 'sorted_transcript_consequences'
    TRANSCRIPT_CONSEQUENCE_FIELD = 'consequence_term'
    GENOTYPE_FIELDS = {
        'dp': 'DP',
        'gq': 'GQ',
        'hl': 'HL',
        'mitoCn': 'mito_cn',
        'contamination': 'contamination',
    }
    QUALITY_FILTER_FORMAT = {
        'HL': QualityFilterFormat(scale=100),
    }

    POPULATION_FIELDS = {'helix': 'helix_mito', 'seqr': 'gt_stats'}
    POPULATIONS = {}
    for pop, sort in {'seqr': 'callset_af', 'gnomad_mito': 'gnomad', 'helix': None}.items():
        pop_het = f'{pop}_heteroplasmy'
        POPULATIONS.update({
            pop: {'af': 'AF_hom', 'ac': 'AC_hom', 'hom': None, 'hemi': None, 'het': None, 'sort': sort},
            pop_het: {
                'af': 'AF_het', 'ac': 'AC_het', 'max_hl': None if pop == 'seqr' else 'max_hl',
                'hom': None, 'hemi': None, 'het': None,
            },
        })
        POPULATION_FIELDS[pop_het] = POPULATION_FIELDS.get(pop, pop)
    PREDICTION_FIELDS_CONFIG = {
        'apogee': PredictionPath('mitimpact', 'score'),
        'haplogroup_defining': PredictionPath('haplogroup', 'is_defining', lambda v: hl.or_missing(v, 'Y')),
        'hmtvar': PredictionPath('hmtvar', 'score'),
        'mitotip': PredictionPath('mitotip', 'trna_prediction'),
        'mut_taster': PredictionPath('dbnsfp_mito', 'MutationTaster_pred'),
        'sift': PredictionPath('dbnsfp_mito', 'SIFT_pred'),
    }

    PATHOGENICITY_FILTERS = {
        CLINVAR_KEY: ('pathogenicity', CLINVAR_PATH_RANGES),
    }

    GLOBALS = BaseHailTableQuery.GLOBALS + ['versions']
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid']
    MITO_ANNOTATION_FIELDS = {
        'commonLowHeteroplasmy': lambda r: r.common_low_heteroplasmy,
        'highConstraintRegion': lambda r: r.high_constraint_region,
        'mitomapPathogenic': lambda r: r.mitomap.pathogenic,
    }
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'mainTranscriptId': lambda r: r.sorted_transcript_consequences.first().transcript_id,
        'selectedMainTranscriptId': lambda r: hl.or_missing(
            r.selected_transcript != r.sorted_transcript_consequences.first(), r.selected_transcript.transcript_id,
        ),
        **MITO_ANNOTATION_FIELDS,
        **BaseHailTableQuery.BASE_ANNOTATION_FIELDS,
    }
    ENUM_ANNOTATION_FIELDS = {
        'clinvar': {'annotate_value': lambda value, enum, ht_globals: {
            'conflictingPathogenicities': MitoHailTableQuery._format_enum(
                value, 'conflictingPathogenicities', enum, enum_keys=['pathogenicity']),
            'version': ht_globals['versions'].clinvar,
        }},
        TRANSCRIPTS_FIELD: {
            **BaseHailTableQuery.ENUM_ANNOTATION_FIELDS['transcripts'],
            'annotate_value': lambda transcript, *args: {'major_consequence': transcript.consequence_terms.first()},
            'drop_fields': ['consequence_terms'],
        }
    }

    SORTS = {
        CONSEQUENCE_SORT: lambda r: [
            hl.min(r.sorted_transcript_consequences.flatmap(lambda t: t.consequence_term_ids)),
            hl.min(r.selected_transcript.consequence_term_ids),
        ],
        PATHOGENICTY_SORT_KEY: lambda r: [hl.or_else(r.clinvar.pathogenicity_id, ABSENT_PATH_SORT_OFFSET)],
        **BaseHailTableQuery.SORTS,
    }
    SORTS[PATHOGENICTY_HGMD_SORT_KEY] = SORTS[PATHOGENICTY_SORT_KEY]

    @staticmethod
    def _selected_main_transcript_expr(ht):
        gene_id = getattr(ht, 'gene_id', None)
        if gene_id is not None:
            gene_transcripts = ht.sorted_transcript_consequences.filter(lambda t: t.gene_id == ht.gene_id)
        else:
            gene_transcripts = getattr(ht, 'gene_transcripts', None)

        allowed_transcripts = getattr(ht, ALLOWED_TRANSCRIPTS, None)
        if gene_id is not None and hasattr(ht, ALLOWED_SECONDARY_TRANSCRIPTS):
            allowed_transcripts = hl.if_else(
                allowed_transcripts.any(hl.is_defined), allowed_transcripts, ht[ALLOWED_SECONDARY_TRANSCRIPTS],
            ) if allowed_transcripts is not None else ht[ALLOWED_SECONDARY_TRANSCRIPTS]

        main_transcript = ht.sorted_transcript_consequences.first()
        if gene_transcripts is not None and allowed_transcripts is not None:
            allowed_transcript_ids = hl.set(allowed_transcripts.map(lambda t: t.transcript_id))
            matched_transcript = hl.or_else(
                gene_transcripts.find(lambda t: allowed_transcript_ids.contains(t.transcript_id)),
                gene_transcripts.first(),
            )
        elif gene_transcripts is not None:
            matched_transcript = gene_transcripts.first()
        elif allowed_transcripts is not None:
            matched_transcript = allowed_transcripts.first()
        else:
            matched_transcript = main_transcript

        return hl.or_else(matched_transcript, main_transcript)

    def __init__(self, *args, **kwargs):
        self._filter_hts = {}
        super().__init__(*args, **kwargs)

    def _parse_intervals(self, intervals, exclude_intervals=False, **kwargs):
        parsed_intervals = super()._parse_intervals(intervals,**kwargs)
        if parsed_intervals and not exclude_intervals:
            self._load_table_kwargs = {'_intervals': parsed_intervals, '_filter_intervals': True}
        return parsed_intervals

    def _get_family_passes_quality_filter(self, quality_filter, ht=None, pathogenicity=None, **kwargs):
        passes_quality = super()._get_family_passes_quality_filter(quality_filter)
        clinvar_path_ht = False if passes_quality is None else self._get_loaded_filter_ht(
            CLINVAR_KEY, 'clinvar_path_variants.ht', self._get_clinvar_prefilter, pathogenicity=pathogenicity)
        if not clinvar_path_ht:
            return passes_quality

        return lambda entries: hl.is_defined(clinvar_path_ht[ht.key]) | passes_quality(entries)

    def _get_loaded_filter_ht(self, key, table_path, get_filters, **kwargs):
        if self._filter_hts.get(key) is None:
            ht_filter = get_filters(**kwargs)
            if ht_filter is False:
                self._filter_hts[key] = False
            else:
                ht = self._read_table(table_path)
                if ht_filter is not True:
                    ht = ht.filter(ht[ht_filter])
                self._filter_hts[key] = ht

        return self._filter_hts[key]

    def _get_clinvar_prefilter(self, pathogenicity=None):
        clinvar_path_filters = self._get_clinvar_path_filters(pathogenicity)
        if not clinvar_path_filters:
            return False

        if CLINVAR_LIKELY_PATH_FILTER not in clinvar_path_filters:
            return 'is_pathogenic'
        elif CLINVAR_PATH_FILTER not in clinvar_path_filters:
            return 'is_likely_pathogenic'
        return True

    def _filter_variant_ids(self, ht, variant_ids):
        if len(variant_ids) == 1:
            variant_id_q = ht.alleles == [variant_ids[0][2], variant_ids[0][3]]
        else:
            variant_id_q = hl.any([
                (ht.locus == hl.locus(chrom, pos, reference_genome=self._genome_version)) &
                (ht.alleles == [ref, alt])
                for chrom, pos, ref, alt in variant_ids
            ])
        return ht.filter(variant_id_q)

    def _parse_variant_keys(self, variant_ids=None, **kwargs):
        if not variant_ids:
            return variant_ids

        return [
            hl.struct(
                locus=hl.locus(f'chr{chrom}' if self._should_add_chr_prefix() else chrom, pos, reference_genome=self._genome_version),
                alleles=[ref, alt],
            ) for chrom, pos, ref, alt in variant_ids
        ]

    def _prefilter_entries_table(self, ht, parsed_intervals=None, exclude_intervals=False, **kwargs):
        if exclude_intervals and parsed_intervals:
            ht = hl.filter_intervals(ht, parsed_intervals, keep=False)
        return ht

    def _get_transcript_consequence_filter(self, allowed_consequence_ids, allowed_consequences):
        canonical_consequences = {
            c.replace('__canonical', '') for c in allowed_consequences if c.endswith('__canonical')
        }
        canonical_consequences -= allowed_consequences

        all_consequence_ids = None
        if canonical_consequences:
            all_consequence_ids = hl.set({
                *self._get_allowed_consequence_ids(canonical_consequences), *allowed_consequence_ids,
            })
        elif not allowed_consequence_ids:
            return None

        allowed_consequence_ids = hl.set(allowed_consequence_ids) if allowed_consequence_ids else hl.empty_set(hl.tint)
        return lambda tc: tc.consequence_term_ids.any(
            (hl.if_else(hl.is_defined(tc.canonical), all_consequence_ids, allowed_consequence_ids)
             if canonical_consequences else allowed_consequence_ids
        ).contains)

    def _get_annotation_override_filters(self, annotations, pathogenicity=None, **kwargs):
        annotation_filters = []

        for key in self.PATHOGENICITY_FILTERS.keys():
            path_terms = (pathogenicity or {}).get(key)
            if path_terms:
                annotation_filters.append(self._has_path_expr(path_terms, key))

        return annotation_filters

    def _frequency_override_filter(self, pathogenicity):
        path_terms = self._get_clinvar_path_filters(pathogenicity)
        return self._has_path_expr(path_terms, CLINVAR_KEY) if path_terms else None

    @staticmethod
    def _get_clinvar_path_filters(pathogenicity):
        return {
            f for f in (pathogenicity or {}).get(CLINVAR_KEY) or [] if f in CLINVAR_PATH_SIGNIFICANCES
        }

    def _has_path_expr(self, terms, field):
        subfield, range_configs = self.PATHOGENICITY_FILTERS[field]
        enum_lookup = self._get_enum_lookup(field, subfield)

        ranges = [[None, None]]
        for path_filter, start, end in range_configs:
            if path_filter in terms:
                ranges[-1][1] = len(enum_lookup) if end is None else enum_lookup[end]
                if ranges[-1][0] is None:
                    ranges[-1][0] = enum_lookup[start]
            elif ranges[-1] != [None, None]:
                ranges.append([None, None])

        ranges = [r for r in ranges if r[0] is not None]
        value = self._ht[field][f'{subfield}_id']
        return hl.any(lambda r: (value >= r[0]) & (value <= r[1]), ranges)

    def _format_results(self, ht, *args, **kwargs):
        ht = ht.annotate(selected_transcript=self._selected_main_transcript_expr(ht))
        return super()._format_results(ht, *args, **kwargs)

    @classmethod
    def _omim_sort(cls, r, omim_gene_set):
        return [
            hl.if_else(omim_gene_set.contains(r.selected_transcript.gene_id), 0, 1),
        ] + super()._omim_sort(r, omim_gene_set)

    @classmethod
    def _gene_rank_sort(cls, r, gene_ranks):
        return [gene_ranks.get(r.selected_transcript.gene_id)] + super()._gene_rank_sort(r, gene_ranks)
