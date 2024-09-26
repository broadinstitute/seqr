from collections import defaultdict

from aiohttp.web import HTTPNotFound
import hail as hl
import logging
import os

from hail_search.constants import ABSENT_PATH_SORT_OFFSET, CLINVAR_KEY, CLINVAR_MITO_KEY, CLINVAR_LIKELY_PATH_FILTER, \
    CLINVAR_PATH_FILTER, \
    CLINVAR_PATH_RANGES, CLINVAR_PATH_SIGNIFICANCES, ALLOWED_TRANSCRIPTS, ALLOWED_SECONDARY_TRANSCRIPTS, \
    PATHOGENICTY_SORT_KEY, CONSEQUENCE_SORT, \
    PATHOGENICTY_HGMD_SORT_KEY, MAX_LOAD_INTERVALS
from hail_search.definitions import SampleType
from hail_search.queries.base import BaseHailTableQuery, PredictionPath, QualityFilterFormat, MAX_PARTITIONS, \
    HT_CHUNK_SIZE

REFERENCE_DATASETS_DIR = os.environ.get('REFERENCE_DATASETS_DIR', '/seqr/seqr-reference-data')

logger = logging.getLogger(__name__)


def _clinvar_sort(clinvar_field, r):
    return hl.or_else(r[clinvar_field].pathogenicity_id, ABSENT_PATH_SORT_OFFSET)


class MitoHailTableQuery(BaseHailTableQuery):

    DATA_TYPE = 'MITO'
    KEY_FIELD = ('locus', 'alleles')

    TRANSCRIPTS_FIELD = 'sorted_transcript_consequences'
    TRANSCRIPT_CONSEQUENCE_FIELD = 'consequence_term'
    GENOTYPE_FIELDS = {
        'dp': 'DP',
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
        'sift': PredictionPath('dbnsfp_mito', 'SIFT_score'),
    }

    PATHOGENICITY_FILTERS = {
        CLINVAR_KEY: ('pathogenicity', CLINVAR_PATH_RANGES),
    }
    PATHOGENICITY_FIELD_MAP = {CLINVAR_KEY: CLINVAR_MITO_KEY}

    GLOBALS = BaseHailTableQuery.GLOBALS + ['versions']
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid']
    MITO_ANNOTATION_FIELDS = {
        'commonLowHeteroplasmy': lambda r: r.common_low_heteroplasmy,
        'highConstraintRegion': (
            lambda r: r.high_constraint_region if hasattr(r, 'high_constraint_region') else r.high_constraint_region_mito
        ),
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
        CLINVAR_MITO_KEY: {
            'response_key': CLINVAR_KEY,
            'include_version': True,
            'annotate_value': lambda value, enum: {
                'conflictingPathogenicities': MitoHailTableQuery._format_enum(
                    value, 'conflictingPathogenicities', enum, enum_keys=['pathogenicity']),
            },
        },
        TRANSCRIPTS_FIELD: {
            **BaseHailTableQuery.ENUM_ANNOTATION_FIELDS['transcripts'],
            'annotate_value': lambda transcript, *args: {'major_consequence': transcript.consequence_terms.first()},
            'drop_fields': ['consequence_terms'],
            'format_array_values': lambda values, *args: BaseHailTableQuery.ENUM_ANNOTATION_FIELDS['transcripts']['format_array_values'](values).map_values(
                lambda transcripts: hl.enumerate(transcripts).starmap(lambda i, t: t.annotate(transcriptRank=i))
            ),
        }
    }

    CLINVAR_SORT = _clinvar_sort
    SORTS = {
        CONSEQUENCE_SORT: lambda r: [
            hl.min(r.sorted_transcript_consequences.flatmap(lambda t: t.consequence_term_ids)),
            hl.min(r.selected_transcript.consequence_term_ids),
        ],
        PATHOGENICTY_SORT_KEY: lambda r: [_clinvar_sort(CLINVAR_MITO_KEY, r)],
        **BaseHailTableQuery.SORTS,
    }
    SORTS[PATHOGENICTY_HGMD_SORT_KEY] = SORTS[PATHOGENICTY_SORT_KEY]

    PREFILTER_TABLES = {
        CLINVAR_KEY: 'clinvar_path_variants.ht',
    }

    def _import_and_filter_entries_ht(
        self, project_guid: str, num_families: int, project_sample_type_data, **kwargs
    ) -> tuple[hl.Table, hl.Table]:
        sample_types = set(project_sample_type_data.keys())
        if len(sample_types) == 1:
            # Import and filter entry table for one family or one project with one sample type
            return super()._import_and_filter_entries_ht(project_guid, num_families, project_sample_type_data, **kwargs)

        self._has_both_sample_types = True
        entries = {}
        for sample_type in sample_types:
            ht, sample_data = self._load_family_or_project_ht(
                num_families, project_guid, project_sample_type_data, sample_type, **kwargs
            )
            entries[sample_type] = (ht, sample_data)

        return self._filter_entries_ht_both_sample_types(
            *entries[SampleType.WES.value], *entries[SampleType.WGS.value], **kwargs
        )

    def _import_and_filter_multiple_project_hts(
        self, project_samples: dict, n_partitions=MAX_PARTITIONS, **kwargs
    ) -> tuple[hl.Table, hl.Table]:
        sample_types = set()
        for sample_dict in project_samples.values():
            sample_types.update(sample_dict.keys())
        if len(sample_types) == 1:
            return super()._import_and_filter_multiple_project_hts(project_samples, n_partitions, **kwargs)

        self._has_both_sample_types = True
        entries = self._load_project_hts_both_sample_types(project_samples, n_partitions, **kwargs)

        filtered_project_hts = []
        filtered_comp_het_project_hts = []
        for entry in entries:
            wes_ht, wes_project_samples = entry[SampleType.WES.value]
            wgs_ht, wgs_project_samples = entry[SampleType.WGS.value]
            ht, comp_het_ht = self._filter_entries_ht_both_sample_types(
                wes_ht, wes_project_samples, wgs_ht, wgs_project_samples, **kwargs
            )
            if ht is not None:
                filtered_project_hts.append(ht)
            if comp_het_ht is not None:
                filtered_comp_het_project_hts.append(comp_het_ht)

        return self._merge_filtered_hts(filtered_comp_het_project_hts, filtered_project_hts, n_partitions)

    def _load_project_hts_both_sample_types(
        self, project_samples: dict, n_partitions: int, **kwargs
    ) -> list[dict[str, tuple[hl.Table, dict]]]:
        all_project_hts = []
        project_hts = defaultdict(list)
        sample_data = defaultdict(dict)
        for project_guid, project_sample_type_data in project_samples.items():
            for sample_type, family_sample_data in project_sample_type_data.items():
                project_ht = self._read_project_table(project_guid, sample_type)
                if project_ht is None:
                    continue
                project_ht = project_ht.select_globals('sample_type', 'family_guids', 'family_samples')
                project_hts[sample_type].append(project_ht)
                sample_data[sample_type].update(family_sample_data)

            # Merge both WES and WGS project_hts when either of their lengths reaches the chunk size
            if len(project_hts[SampleType.WES.value]) >= HT_CHUNK_SIZE or len(project_hts[SampleType.WGS.value]) >= HT_CHUNK_SIZE:
                project_ht_dict = {}
                for sample_type in project_hts:
                    ht = self._prefilter_merged_project_hts(project_hts[sample_type], n_partitions, **kwargs)
                    project_ht_dict[sample_type] = (ht, sample_data[sample_type])
                all_project_hts.append(project_ht_dict)
                project_hts = defaultdict(list)
                sample_data = defaultdict(dict)

        project_ht_dict = {}
        for sample_type in project_hts:
            ht = self._prefilter_merged_project_hts(project_hts[sample_type], n_partitions, **kwargs)
            project_ht_dict[sample_type] = (ht, sample_data[sample_type])
        all_project_hts.append(project_ht_dict)
        return all_project_hts

    def _filter_entries_ht_both_sample_types(
        self, wes_ht, wes_project_samples, wgs_ht, wgs_project_samples, inheritance_filter=None, quality_filter=None, **kwargs
    ):
        wes_ht, sorted_wes_family_sample_data = self._add_entry_sample_families(wes_ht, wes_project_samples)
        wgs_ht, sorted_wgs_family_sample_data = self._add_entry_sample_families(wgs_ht, wgs_project_samples)
        wes_ht = wes_ht.rename({'family_entries': SampleType.WES.family_entries_field, 'filters': SampleType.WES.filters_field})
        wgs_ht = wgs_ht.rename({'family_entries': SampleType.WGS.family_entries_field, 'filters': SampleType.WGS.filters_field})
        ht = wes_ht.join(wgs_ht, how='outer')

        sample_types = [
            (SampleType.WES, sorted_wes_family_sample_data),
            (SampleType.WGS, sorted_wgs_family_sample_data)
        ]
        for sample_type, _ in sample_types:
            ht = self._filter_quality(
                ht, quality_filter, filters_field_name=sample_type.filters_field,
                annotation=sample_type.passes_quality_field, entries_ht_field=sample_type.family_entries_field, **kwargs
            )

        ch_ht = None
        for sample_type, family_sample_data in sample_types:
            ht, ch_ht = self._filter_inheritance(
                ht, ch_ht, inheritance_filter, family_sample_data,
                annotation=sample_type.passes_inheritance_field, entries_ht_field=sample_type.family_entries_field
            )

        family_idx_map = self._build_family_index_map(sample_types, sorted_wes_family_sample_data, sorted_wgs_family_sample_data)
        ht = self._apply_multi_sample_type_entry_filters(ht, family_idx_map)
        ch_ht = self._apply_multi_sample_type_entry_filters(ch_ht, family_idx_map)

        return ht, ch_ht

    @staticmethod
    def _build_family_index_map(sample_types, sorted_wes_family_sample_data, sorted_wgs_family_sample_data):
        family_guid_idx_map = defaultdict(dict)
        for sample_type, sorted_family_sample_data in sample_types:
            for family_idx, samples in enumerate(sorted_family_sample_data):
                family_guid = samples[0]['familyGuid']
                family_guid_idx_map[family_guid][sample_type.value] = family_idx
        return hl.dict(family_guid_idx_map)

    def _apply_multi_sample_type_entry_filters(self, ht, family_idx_map):
        if ht is None:
            return ht

        # Keep family from both sample types if either passes quality AND inheritance
        for sample_type in SampleType:
            ht = ht.annotate(**{
                sample_type.family_entries_field: hl.enumerate(ht[sample_type.family_entries_field]).starmap(
                    lambda i, samples: hl.or_missing(
                        self._family_passes_quality_inheritance(
                            ht, sample_type, i, samples[0]['familyGuid'], family_idx_map
                        ), samples)
                )})

        # Merge family entries and filters from both sample types
        ht = ht.transmute(
            family_entries=hl.coalesce(
                ht[SampleType.WES.family_entries_field], hl.empty_array(ht[SampleType.WES.family_entries_field].dtype.element_type)
            ).extend(hl.coalesce(
                ht[SampleType.WGS.family_entries_field], hl.empty_array(ht[SampleType.WGS.family_entries_field].dtype.element_type)
            )).filter(lambda entries: entries.any(hl.is_defined)),
            filters=hl.coalesce(ht[SampleType.WES.filters_field], hl.empty_set(hl.tstr)).union(
                hl.coalesce(ht[SampleType.WGS.filters_field], hl.empty_set(hl.tstr))
            )
        )
        # Filter out families with no valid entries in either sample type
        return ht.filter(ht.family_entries.any(hl.is_defined))

    @staticmethod
    def _family_passes_quality_inheritance(ht, sample_type, sample_type_family_idx, family_guid, family_idx_map):
        # Note: This logic does not sufficiently handle case 2 here https://docs.google.com/presentation/d/1hqDV8ulhviUcR5C4PtNUqkCLXKDsc6pccgFVlFmWUAU/edit?usp=sharing
        # and will need to be changed to support it.
        return (
            hl.is_defined(ht[sample_type.passes_quality_field][sample_type_family_idx]) &
            hl.is_defined(ht[sample_type.passes_inheritance_field][sample_type_family_idx])
        ) | (
            (hl.is_defined(family_guid) & family_idx_map.get(family_guid).contains(sample_type.other_sample_type.value)) &
            hl.bind(lambda other_sample_type_family_idx: (
                hl.is_defined(ht[sample_type.other_sample_type.passes_quality_field][other_sample_type_family_idx]) &
                hl.is_defined(ht[sample_type.other_sample_type.passes_inheritance_field][other_sample_type_family_idx])
            ), family_idx_map[family_guid][sample_type.other_sample_type.value])
        )

    def _get_sample_genotype(
        self, samples, r=None, include_genotype_overrides=False, select_fields=None, all_samples=False, **kwargs
    ):
        if not self._has_both_sample_types and not all_samples:
            return super()._get_sample_genotype(samples, r, include_genotype_overrides, select_fields)

        return samples.map(lambda sample: self._select_genotype_for_sample(
            sample, r, include_genotype_overrides, select_fields
        ))

    @staticmethod
    def _selected_main_transcript_expr(ht):
        comp_het_gene_ids = getattr(ht, 'comp_het_gene_ids', None)
        if comp_het_gene_ids is not None:
            gene_transcripts = ht.sorted_transcript_consequences.filter(lambda t: comp_het_gene_ids.contains(t.gene_id))
        else:
            gene_transcripts = getattr(ht, 'gene_transcripts', None)

        allowed_transcripts = getattr(ht, ALLOWED_TRANSCRIPTS, None)
        if comp_het_gene_ids is not None and hasattr(ht, ALLOWED_SECONDARY_TRANSCRIPTS):
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
        self._has_both_sample_types = False
        super().__init__(*args, **kwargs)

    def _parse_intervals(self, intervals, exclude_intervals=False, **kwargs):
        parsed_intervals = super()._parse_intervals(intervals,**kwargs)
        if parsed_intervals and not exclude_intervals and len(parsed_intervals) < MAX_LOAD_INTERVALS:
            self._load_table_kwargs = {'_intervals': parsed_intervals, '_filter_intervals': True}
        return parsed_intervals

    def _get_family_passes_quality_filter(self, quality_filter, ht, pathogenicity=None, **kwargs):
        passes_quality = super()._get_family_passes_quality_filter(quality_filter, ht)
        clinvar_path_ht = False if passes_quality is None else self._get_loaded_clinvar_prefilter_ht(pathogenicity)
        if not clinvar_path_ht:
            return passes_quality

        return lambda entries: hl.is_defined(clinvar_path_ht[ht.key]) | passes_quality(entries)

    def _get_loaded_filter_ht(self, key, get_filters, **kwargs):
        if self._filter_hts.get(key) is None:
            ht_filter = get_filters(**kwargs)
            if ht_filter is False:
                self._filter_hts[key] = False
            else:
                ht = self._read_table(self.PREFILTER_TABLES[key])
                if ht_filter is not True:
                    ht = ht.filter(ht_filter(ht))
                self._filter_hts[key] = ht

        return self._filter_hts[key]

    @classmethod
    def _get_table_dir(cls, path):
        if path in cls.PREFILTER_TABLES.values():
            return REFERENCE_DATASETS_DIR
        return super()._get_table_dir(path)

    def _get_loaded_clinvar_prefilter_ht(self, pathogenicity):
        return self._get_loaded_filter_ht(
            CLINVAR_KEY, self._get_clinvar_prefilter, pathogenicity=pathogenicity)

    def _get_clinvar_prefilter(self, pathogenicity=None):
        clinvar_path_filters = self._get_clinvar_path_filters(pathogenicity)
        if not clinvar_path_filters:
            return False

        if CLINVAR_LIKELY_PATH_FILTER not in clinvar_path_filters:
            return lambda ht: ht.is_pathogenic
        elif CLINVAR_PATH_FILTER not in clinvar_path_filters:
            return lambda ht: ht.is_likely_pathogenic
        return True

    def _filter_variant_ids(self, ht, variant_ids):
        if len(variant_ids) == 1:
            variant_id_q = ht.alleles == [variant_ids[0][2], variant_ids[0][3]]
        else:
            variant_id_q = hl.any([
                (ht.locus == hl.locus(chrom, pos, reference_genome=self.GENOME_VERSION)) &
                (ht.alleles == [ref, alt])
                for chrom, pos, ref, alt in variant_ids
            ])
        return ht.filter(variant_id_q)

    def _parse_variant_keys(self, variant_ids=None, **kwargs):
        if not variant_ids:
            return variant_ids

        return [
            hl.struct(
                locus=hl.locus(f'chr{chrom}' if self._should_add_chr_prefix() else chrom, pos, reference_genome=self.GENOME_VERSION),
                alleles=[ref, alt],
            ) for chrom, pos, ref, alt in variant_ids
        ]

    def _prefilter_entries_table(self, ht, parsed_intervals=None, exclude_intervals=False, **kwargs):
        num_intervals = len(parsed_intervals or [])
        if exclude_intervals and parsed_intervals:
            ht = hl.filter_intervals(ht, parsed_intervals, keep=False)
        elif num_intervals >= MAX_LOAD_INTERVALS:
            ht = hl.filter_intervals(ht, parsed_intervals)

        if '_n_partitions' not in self._load_table_kwargs and num_intervals > self._n_partitions:
            ht = ht.naive_coalesce(self._n_partitions)

        return ht

    def _get_allowed_consequence_ids(self, annotations):
        consequence_ids = super()._get_allowed_consequence_ids(annotations)
        canonical_consequences = {
            c.replace('__canonical', '') for consequences in annotations.values()
            if consequences for c in consequences if c.endswith('__canonical')
        }
        if canonical_consequences:
            canonical_consequence_ids = super()._get_allowed_consequence_ids({'canonical': canonical_consequences})
            canonical_consequence_ids -= consequence_ids
            consequence_ids.update({f'{cid}__canonical' for cid in canonical_consequence_ids})
        return consequence_ids

    @staticmethod
    def _get_allowed_transcripts_filter(allowed_consequence_ids):
        canonical_consequences = set()
        any_consequences = set()
        for c in allowed_consequence_ids:
            if str(c).endswith('__canonical'):
                canonical_consequences.add(int(c.replace('__canonical', '')))
            else:
                any_consequences.add(c)

        all_consequence_ids = None
        if canonical_consequences:
            all_consequence_ids = hl.set({*canonical_consequences, *any_consequences})

        allowed_consequence_ids = hl.set(any_consequences) if any_consequences else hl.empty_set(hl.tint)
        return lambda tc: tc.consequence_term_ids.any(
            (hl.if_else(hl.is_defined(tc.canonical), all_consequence_ids, allowed_consequence_ids)
             if canonical_consequences else allowed_consequence_ids
        ).contains)

    def _get_annotation_override_fields(self, annotations, pathogenicity=None, **kwargs):
        annotation_overrides = super()._get_annotation_override_fields(annotations, **kwargs)
        for key in self.PATHOGENICITY_FILTERS.keys():
            path_terms = (pathogenicity or {}).get(key)
            if path_terms:
                annotation_overrides[key] = path_terms
        return annotation_overrides

    def _get_annotation_override_filters(self, ht, annotation_overrides):
        annotation_filters = []

        for key in self.PATHOGENICITY_FILTERS.keys():
            if key in annotation_overrides:
                annotation_filters.append(self._has_path_expr(ht, annotation_overrides[key], key))

        return annotation_filters

    def _frequency_override_filter(self, ht, pathogenicity):
        path_terms = self._get_clinvar_path_filters(pathogenicity)
        return self._has_path_expr(ht, path_terms, CLINVAR_KEY) if path_terms else None

    @staticmethod
    def _get_clinvar_path_filters(pathogenicity):
        return {
            f for f in (pathogenicity or {}).get(CLINVAR_KEY) or [] if f in CLINVAR_PATH_SIGNIFICANCES
        }

    def _has_path_expr(self, ht, terms, field):
        subfield, range_configs = self.PATHOGENICITY_FILTERS[field]
        field_name = self.PATHOGENICITY_FIELD_MAP.get(field, field)
        enum_lookup = self._get_enum_lookup(field_name, subfield)

        ranges = [[None, None]]
        for path_filter, start, end in range_configs:
            if path_filter in terms:
                ranges[-1][1] = len(enum_lookup) if end is None else enum_lookup[end]
                if ranges[-1][0] is None:
                    ranges[-1][0] = enum_lookup[start]
            elif ranges[-1] != [None, None]:
                ranges.append([None, None])

        ranges = [r for r in ranges if r[0] is not None]
        value = ht[field_name][f'{subfield}_id']
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

    def _add_project_lookup_data(self, ht, annotation_fields, *args, **kwargs):
        # Get all the project-families for the looked up variant formatted as a dict of dicts:
        # {<project_guid>: {<sample_type>: {<family_guid>: True}, <sample_type_2>: {<family_guid_2>: True}}, <project_guid_2>: ...}
        lookup_ht = self._read_table('lookup.ht', skip_missing_field='project_stats')
        if lookup_ht is None:
            raise HTTPNotFound()
        variant_projects = lookup_ht.aggregate(hl.agg.take(
            hl.dict(hl.enumerate(lookup_ht.project_stats).starmap(lambda i, ps: (
                lookup_ht.project_sample_types[i],
                hl.enumerate(ps).starmap(
                    lambda j, s: hl.or_missing(self._stat_has_non_ref(s), j)
                ).filter(hl.is_defined),
            )).filter(
                lambda x: x[1].any(hl.is_defined)
            ).starmap(lambda project_key, family_indices: (
                project_key,
                hl.dict(family_indices.map(lambda j: (lookup_ht.project_families[project_key][j], True))),
            )).group_by(
                lambda x: x[0][0]
            ).map_values(
                lambda project_data: hl.dict(project_data.starmap(
                    lambda project_key, families: (project_key[1], families)
            )))), 1)
        )[0]

        # Variant can be present in the lookup table with only ref calls, so is still not present in any projects
        if not variant_projects:
            raise HTTPNotFound()

        annotation_fields.update({
            'familyGenotypes': lambda r: hl.dict(r.family_entries.map(
                lambda entries: (entries.first().familyGuid, self._get_sample_genotype(entries.filter(hl.is_defined), all_samples=True))
            )),
        })

        logger.info(f'Looking up {self.DATA_TYPE} variant in {len(variant_projects)} projects')

        return super()._add_project_lookup_data(ht, annotation_fields, project_samples=variant_projects, **kwargs)

    @staticmethod
    def _stat_has_non_ref(s):
        return (s.heteroplasmic_samples > 0) | (s.homoplasmic_samples > 0)
