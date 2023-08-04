from aiohttp.web import HTTPBadRequest
from collections import defaultdict, namedtuple
import hail as hl
import logging
import os

from hail_search.constants import AFFECTED, UNAFFECTED, AFFECTED_ID, UNAFFECTED_ID, MALE, VARIANT_DATASET, \
    VARIANT_KEY_FIELD, GNOMAD_GENOMES_FIELD, XPOS, GENOME_VERSION_GRCh38_DISPLAY, INHERITANCE_FILTERS, \
    ANY_AFFECTED, X_LINKED_RECESSIVE, REF_REF, REF_ALT, COMP_HET_ALT, ALT_ALT, HAS_ALT, HAS_REF, \
    ANNOTATION_OVERRIDE_FIELDS, SCREEN_KEY, SPLICE_AI_FIELD, CLINVAR_KEY, HGMD_KEY, CLINVAR_PATH_RANGES, HGMD_PATH_RANGES

DATASETS_DIR = os.environ.get('DATASETS_DIR', '/hail_datasets')

logger = logging.getLogger(__name__)


PredictionPath = namedtuple('PredictionPath', ['source', 'field'])
QualityFilterFormat = namedtuple('QualityFilterFormat', ['scale', 'override'], defaults=[None, None])


def _to_camel_case(snake_case_str):
    converted = snake_case_str.replace('_', ' ').title().replace(' ', '')
    return converted[0].lower() + converted[1:]


class BaseHailTableQuery(object):

    GENOTYPE_QUERY_MAP = {
        REF_REF: lambda gt: gt.is_hom_ref(),
        REF_ALT: lambda gt: gt.is_het(),
        COMP_HET_ALT: lambda gt: gt.is_het(),
        ALT_ALT: lambda gt: gt.is_hom_var(),
        HAS_ALT: lambda gt: gt.is_non_ref(),
        HAS_REF: lambda gt: gt.is_hom_ref() | gt.is_het_ref(),
    }

    GENOTYPE_FIELDS = {}
    QUALITY_FILTER_FORMAT = {}
    POPULATIONS = {}
    POPULATION_FIELDS = {}
    POPULATION_KEYS = ['AF', 'AC', 'AN', 'Hom', 'Hemi', 'Het']
    PREDICTION_FIELDS_CONFIG = {}

    GLOBALS = ['enums']
    CORE_FIELDS = [XPOS]
    BASE_ANNOTATION_FIELDS = {
        'familyGuids': lambda r: r.genotypes.group_by(lambda x: x.familyGuid).keys(),
        'genotypes': lambda r: r.genotypes.group_by(lambda x: x.individualGuid).map_values(lambda x: x[0]),
    }
    ENUM_ANNOTATION_FIELDS = {}
    LIFTOVER_ANNOTATION_FIELDS = {
        'liftedOverGenomeVersion': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), '37'),
        'liftedOverChrom': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), r.rg37_locus.contig),
        'liftedOverPos': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), r.rg37_locus.position),
    }

    SORTS = {
        XPOS: lambda r: [r.xpos],
    }

    @classmethod
    def _format_population_config(cls, pop_config):
        base_pop_config = {field.lower(): field for field in cls.POPULATION_KEYS}
        base_pop_config.update(pop_config)
        return base_pop_config

    def annotation_fields(self):
        annotation_fields = {
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population) for population in self.POPULATIONS.keys()
            }),
            'predictions': lambda r: hl.struct(**{
                prediction: hl.array(self._enums[path.source][path.field])[r[path.source][f'{path.field}_id']]
                if self._enums.get(path.source, {}).get(path.field) else r[path.source][path.field]
                for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
            'transcripts': lambda r: hl.or_else(
                r.sorted_transcript_consequences, hl.empty_array(r.sorted_transcript_consequences.dtype.element_type)
            ).map(
                lambda t: self._enum_field(t, self._enums['sorted_transcript_consequences'], **self._format_transcript_args())
            ).group_by(lambda t: t.geneId),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)

        format_enum = lambda k, enum_config: lambda r: self._enum_field(r[k], self._enums[k], ht_globals=self._globals, **enum_config)
        annotation_fields.update({
            enum_config.get('response_key', k): format_enum(k, enum_config)
            for k, enum_config in self.ENUM_ANNOTATION_FIELDS.items()
        })

        if self._genome_version == GENOME_VERSION_GRCh38_DISPLAY:
            annotation_fields.update(self.LIFTOVER_ANNOTATION_FIELDS)
        return annotation_fields

    def population_expression(self, r, population):
        pop_config = self._format_population_config(self.POPULATIONS[population])
        pop_field = self.POPULATION_FIELDS.get(population, population)
        return hl.struct(**{
            response_key: hl.or_else(r[pop_field][field], '' if response_key == 'id' else 0)
            for response_key, field in pop_config.items() if field is not None
        })

    def _format_transcript_args(self):
        return {
            'format_value': lambda value: value.rename({k: _to_camel_case(k) for k in value.keys()}),
        }

    def _get_enum_lookup(self, field, subfield):
        enum_field = self._enums.get(field, {}).get(subfield)
        if enum_field is None:
            return None
        return {v: i for i, v in enumerate(enum_field)}

    @staticmethod
    def _enum_field(value, enum, ht_globals=None, annotate_value=None, format_value=None, drop_fields=None, **kwargs):
        annotations = {}
        drop = [] + (drop_fields or [])
        value_keys = value.keys()
        for field, field_enum in enum.items():
            is_array = f'{field}_ids' in value_keys
            value_field = f"{field}_id{'s' if is_array else ''}"
            drop.append(value_field)

            enum_array = hl.array(field_enum)
            if is_array:
                annotations[f'{field}s'] = value[value_field].map(lambda v: enum_array[v])
            else:
                annotations[field] = enum_array[value[value_field]]

        value = value.annotate(**annotations)
        if annotate_value:
            annotations = annotate_value(value, enum, ht_globals)
            value = value.annotate(**annotations)
        value = value.drop(*drop)

        if format_value:
            value = format_value(value)

        return value

    def __init__(self, data_type, sample_data, genome_version, sort=XPOS, num_results=100, **kwargs):
        self._genome_version = genome_version
        self._sort = sort
        self._num_results = num_results
        self._ht = None
        self._enums = None
        self._globals = None

        self._load_filtered_table(data_type, sample_data, **kwargs)

    def _load_filtered_table(self, data_type, sample_data, intervals=None, exclude_intervals=False, variant_ids=None, **kwargs):
        parsed_intervals, variant_ids = self._parse_intervals(intervals, variant_ids)
        excluded_intervals = None
        if exclude_intervals:
            excluded_intervals = parsed_intervals
            parsed_intervals = None
        self.import_filtered_table(
            data_type, sample_data, intervals=parsed_intervals, excluded_intervals=excluded_intervals,
            variant_ids=variant_ids, **kwargs)

    def import_filtered_table(self, data_type, sample_data, intervals=None, **kwargs):
        tables_path = f'{DATASETS_DIR}/{self._genome_version}/{data_type}'
        load_table_kwargs = {'_intervals': intervals, '_filter_intervals': bool(intervals)}

        family_samples = defaultdict(list)
        project_samples = defaultdict(list)
        for s in sample_data:
            family_samples[s['family_guid']].append(s)
            project_samples[s['project_guid']].append(s)

        logger.info(f'Loading {data_type} data for {len(family_samples)} families in {len(project_samples)} projects')
        if len(family_samples) == 1:
            family_guid, family_sample_data = list(family_samples.items())[0]
            family_ht = hl.read_table(f'{tables_path}/families/{family_guid}.ht', **load_table_kwargs)
            families_ht = self._filter_entries_table(family_ht, family_sample_data, **kwargs)
        else:
            filtered_project_hts = []
            exception_messages = set()
            for project_guid, project_sample_data in project_samples.items():
                project_ht = hl.read_table(f'{tables_path}/projects/{project_guid}.ht', **load_table_kwargs)
                try:
                    filtered_project_hts.append(self._filter_entries_table(project_ht, project_sample_data, **kwargs))
                except HTTPBadRequest as e:
                    exception_messages.add(e.text)

            if exception_messages:
                raise HTTPBadRequest(text='; '.join(exception_messages))

            families_ht = filtered_project_hts[0]
            default_entries = hl.empty_array(families_ht.family_entries.dtype.element_type)
            for project_ht in filtered_project_hts[1:]:
                families_ht = families_ht.join(project_ht, how='outer')
                families_ht = families_ht.select(
                    filters=families_ht.filters.union(families_ht.filters_1),
                    family_entries=hl.bind(
                        lambda a1, a2: a1.extend(a2),
                        hl.or_else(families_ht.family_entries, default_entries),
                        hl.or_else(families_ht.family_entries_1, default_entries),
                    ),
                )

        annotations_ht_path = f'{tables_path}/annotations.ht'
        annotation_ht_query_result = hl.query_table(
            annotations_ht_path, families_ht.key).first().drop(*families_ht.key)
        ht = families_ht.annotate(**annotation_ht_query_result)

        # Get globals
        annotation_globals_ht = hl.read_table(annotations_ht_path).head(0).select()
        self._globals = {k: hl.eval(annotation_globals_ht[k]) for k in self.GLOBALS}
        self._enums = self._globals.pop('enums')

        self._ht = ht.transmute(
            genotypes=ht.family_entries.flatmap(lambda x: x).filter(
                lambda gt: hl.is_defined(gt.individualGuid)
            ).map(lambda gt: gt.select(
                'sampleId', 'individualGuid', 'familyGuid',
                numAlt=hl.if_else(hl.is_defined(gt.GT), gt.GT.n_alt_alleles(), -1),
                **{k: gt[field] for k, field in self.GENOTYPE_FIELDS.items()}
            ))
        )
        self._filter_annotated_table(**kwargs)

    def _filter_entries_table(self, ht, sample_data,  inheritance_mode=None, inheritance_filter=None, quality_filter=None,
                              excluded_intervals=None, variant_ids=None, **kwargs):
        if excluded_intervals:
            ht = hl.filter_intervals(ht, excluded_intervals, keep=False)

        if variant_ids:
            ht = self._filter_variant_ids(ht, variant_ids)

        ht, sample_id_family_index_map = self._add_entry_sample_families(ht, sample_data)

        ht = self._filter_inheritance(
            ht, inheritance_mode, inheritance_filter, sample_data, sample_id_family_index_map,
        )

        quality_filter = quality_filter or {}
        if quality_filter.get('vcf_filter'):
            ht = self._filter_vcf_filters(ht)

        passes_quality_filter = self._get_genotype_passes_quality_filter(quality_filter)
        if passes_quality_filter is not None:
            ht = ht.annotate(family_entries=ht.family_entries.map(
                lambda entries: hl.or_missing(entries.all(passes_quality_filter), entries)
            ))
            ht = ht.filter(ht.family_entries.any(hl.is_defined))

        return ht.select_globals()

    @classmethod
    def _add_entry_sample_families(cls, ht, sample_data):
        sample_index_id_map = dict(enumerate(hl.eval(ht.sample_ids)))
        sample_id_index_map = {v: k for k, v in sample_index_id_map.items()}
        sample_index_id_map = hl.dict(sample_index_id_map)
        sample_individual_map = {s['sample_id']: s['individual_guid'] for s in sample_data}
        missing_samples = set(sample_individual_map.keys()) - set(sample_id_index_map.keys())
        if missing_samples:
            raise HTTPBadRequest(
                text=f'The following samples are available in seqr but missing the loaded data: {", ".join(sorted(missing_samples))}'
            )

        affected_id_map = {AFFECTED: AFFECTED_ID, UNAFFECTED: UNAFFECTED_ID}
        sample_index_affected_status = hl.dict({
            sample_id_index_map[s['sample_id']]: affected_id_map.get(s['affected']) for s in sample_data
        })
        sample_index_individual_map = hl.dict({
            sample_id_index_map[sample_id]: i_guid for sample_id, i_guid in sample_individual_map.items()
        })
        sample_id_family_map = {s['sample_id']: s['family_guid'] for s in sample_data}
        sample_index_family_map = hl.dict({sample_id_index_map[k]: v for k, v in sample_id_family_map.items()})
        family_index_map = {f: i for i, f in enumerate(sorted(set(sample_id_family_map.values())))}
        family_sample_indices = [None] * len(family_index_map)
        sample_id_family_index_map = {}
        for sample_id, family_guid in sample_id_family_map.items():
            sample_index = sample_id_index_map[sample_id]
            family_index = family_index_map[family_guid]
            if not family_sample_indices[family_index]:
                family_sample_indices[family_index] = []
            sample_id_family_index_map[sample_id] = (family_index, len(family_sample_indices[family_index]))
            family_sample_indices[family_index].append(sample_index)
        family_sample_indices = hl.array(family_sample_indices)

        ht = ht.transmute(
            family_entries=family_sample_indices.map(lambda sample_indices: sample_indices.map(
                lambda i: hl.or_else(ht.entries[i], cls._missing_entry(ht.entries[i])).annotate(
                    sampleId=sample_index_id_map.get(i),
                    individualGuid=sample_index_individual_map.get(i),
                    familyGuid=sample_index_family_map.get(i),
                    affected_id=sample_index_affected_status.get(i),
                )
            ))
        )

        return ht, sample_id_family_index_map

    @staticmethod
    def _missing_entry(entry):
        entry_type = dict(**entry.dtype)
        return hl.struct(**{k: hl.missing(v) for k, v in entry_type.items()})

    def _filter_inheritance(self, ht, inheritance_mode, inheritance_filter, sample_data, sample_id_family_index_map):
        any_valid_entry = lambda x: self.GENOTYPE_QUERY_MAP[HAS_ALT](x.GT)

        is_any_affected = inheritance_mode == ANY_AFFECTED
        if is_any_affected:
            prev_any_valid_entry = any_valid_entry
            any_valid_entry = lambda x: prev_any_valid_entry(x) & (x.affected_id == AFFECTED_ID)

        ht = ht.annotate(family_entries=ht.family_entries.map(
            lambda entries: hl.or_missing(entries.any(any_valid_entry), entries))
        )

        if not (inheritance_filter or inheritance_mode):
            return ht

        if inheritance_mode == X_LINKED_RECESSIVE:
            x_chrom_interval = hl.parse_locus_interval(
                hl.get_reference(self._genome_version).x_contigs[0], reference_genome=self._genome_version)
            ht = ht.filter(self.get_x_chrom_filter(ht, x_chrom_interval))

        if not is_any_affected:
            ht = self._filter_families_inheritance(
                ht, inheritance_mode, inheritance_filter, sample_id_family_index_map, sample_data,
            )

        return ht.filter(ht.family_entries.any(hl.is_defined))

    @classmethod
    def _filter_families_inheritance(cls, ht, inheritance_mode, inheritance_filter, sample_id_family_index_map, sample_data):
        individual_genotype_filter = (inheritance_filter or {}).get('genotype')

        entry_indices_by_gt = defaultdict(lambda: defaultdict(list))
        for s in sample_data:
            genotype = individual_genotype_filter.get(s['individual_guid']) \
                if individual_genotype_filter else INHERITANCE_FILTERS[inheritance_mode].get(s['affected'])
            if inheritance_mode == X_LINKED_RECESSIVE and s['affected'] == UNAFFECTED and s['sex'] == MALE:
                genotype = REF_REF
            if genotype:
                family_index, entry_index = sample_id_family_index_map[s['sample_id']]
                entry_indices_by_gt[genotype][family_index].append(entry_index)

        for genotype, entry_indices in entry_indices_by_gt.items():
            entry_indices = hl.dict(entry_indices)
            ht = ht.annotate(family_entries=hl.enumerate(ht.family_entries).map(
                lambda x: cls._valid_genotype_family_entries(x[1], entry_indices.get(x[0]), genotype)))

        return ht

    @classmethod
    def _valid_genotype_family_entries(cls, entries, gentoype_entry_indices, genotype):
        is_valid = hl.is_missing(gentoype_entry_indices) | gentoype_entry_indices.all(
            lambda i: cls.GENOTYPE_QUERY_MAP[genotype](entries[i].GT)
        )
        return hl.or_missing(is_valid, entries)

    @classmethod
    def _get_genotype_passes_quality_filter(cls, quality_filter):
        affected_only = quality_filter.get('affected_only')
        passes_quality_filters = []
        for filter_k, value in quality_filter.items():
            field = cls.GENOTYPE_FIELDS.get(filter_k.replace('min_', ''))
            if field and value:
                passes_quality_filters.append(cls._get_genotype_passes_quality_field(field, value, affected_only))

        if not passes_quality_filters:
            return None

        def passes_quality(gt):
            pq = passes_quality_filters[0](gt)
            for q in passes_quality_filters[1:]:
                pq &= q(gt)
            return pq

        return passes_quality

    @classmethod
    def _get_genotype_passes_quality_field(cls, field, value, affected_only):
        field_config = cls.QUALITY_FILTER_FORMAT.get(field) or QualityFilterFormat()
        if field_config.scale:
            value = value / field_config.scale

        def passes_quality_field(gt):
            is_valid = (gt[field] >= value) | hl.is_missing(gt[field])
            if field_config.override:
                is_valid |= field_config.override(gt)
            if affected_only:
                is_valid |= gt.affected_id == UNAFFECTED_ID
            return is_valid

        return passes_quality_field

    @staticmethod
    def _filter_vcf_filters(ht):
        return ht.filter(hl.is_missing(ht.filters) | (ht.filters.length() < 1))

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return x_interval.contains(ht.locus)

    def _filter_variant_ids(self, ht, variant_ids):
        if len(variant_ids) == 1:
            variant_id_q = ht.alleles == [variant_ids[0][2], variant_ids[0][3]]
        else:
            variant_id_qs = [
                (ht.locus == hl.locus(chrom, pos, reference_genome=self._genome_version)) &
                (ht.alleles == [ref, alt])
                for chrom, pos, ref, alt in variant_ids
            ]
            variant_id_q = variant_id_qs[0]
            for q in variant_id_qs[1:]:
                variant_id_q |= q
        return ht.filter(variant_id_q)

    def _filter_annotated_table(self, gene_ids=None, rs_ids=None, frequencies=None, in_silico=None, pathogenicity=None, annotations=None, **kwargs):
        if gene_ids:
            self._filter_by_gene_ids(gene_ids)

        if rs_ids:
            self._filter_rs_ids(rs_ids)

        self._filter_by_frequency(frequencies)

        self._filter_by_in_silico(in_silico)

        self._filter_by_annotations(pathogenicity, annotations)

    def _filter_by_gene_ids(self, gene_ids):
        gene_ids = hl.set(gene_ids)
        gene_id_filter = self._get_gene_id_filter(gene_ids)
        self._ht = self._ht.filter(gene_id_filter)

    def _get_gene_id_filter(self, gene_ids):
        raise NotImplementedError

    def _filter_rs_ids(self, rs_ids):
        rs_id_set = hl.set(rs_ids)
        self._ht = self._ht.filter(rs_id_set.contains(self._ht.rsid))

    @staticmethod
    def _formatted_chr_interval(interval):
        return f'[chr{interval.replace("[", "")}' if interval.startswith('[') else f'chr{interval}'

    def _parse_intervals(self, intervals, variant_ids):
        if not (intervals or variant_ids):
            return intervals, variant_ids

        reference_genome = hl.get_reference(self._genome_version)
        should_add_chr_prefix = any(c.startswith('chr') for c in reference_genome.contigs)

        raw_intervals = intervals
        if variant_ids:
            if should_add_chr_prefix:
                variant_ids = [(f'chr{chr}', *v_id) for chr, *v_id in variant_ids]
            intervals = [f'[{chrom}:{pos}-{pos}]' for chrom, pos, _, _ in variant_ids]
        elif should_add_chr_prefix:
            intervals = [
                f'[chr{interval.replace("[", "")}' if interval.startswith('[') else f'chr{interval}'
                for interval in intervals
            ]

        parsed_intervals = [
            hl.eval(hl.parse_locus_interval(interval, reference_genome=self._genome_version, invalid_missing=True))
            for interval in intervals
        ]
        invalid_intervals = [raw_intervals[i] for i, interval in enumerate(parsed_intervals) if interval is None]
        if invalid_intervals:
            raise HTTPBadRequest(text=f'Invalid intervals: {", ".join(invalid_intervals)}')

        return parsed_intervals, variant_ids

    def _filter_by_frequency(self, frequencies):
        frequencies = {k: v for k, v in (frequencies or {}).items() if k in self.POPULATIONS}
        if not frequencies:
            return

        for pop, freqs in sorted(frequencies.items()):
            pop_filters = []
            pop_expr = self._ht[self.POPULATION_FIELDS.get(pop, pop)]
            pop_config = self._format_population_config(self.POPULATIONS[pop])
            if freqs.get('af') is not None:
                af_field = pop_config.get('filter_af') or pop_config['af']
                pop_filters.append(pop_expr[af_field] <= freqs['af'])
            elif freqs.get('ac') is not None:
                ac_field = pop_config['ac']
                if ac_field:
                    pop_filters.append(pop_expr[ac_field] <= freqs['ac'])

            if freqs.get('hh') is not None:
                hom_field = pop_config['hom']
                hemi_field = pop_config['hemi']
                if hom_field:
                    pop_filters.append(pop_expr[hom_field] <= freqs['hh'])
                if hemi_field:
                    pop_filters.append(pop_expr[hemi_field] <= freqs['hh'])

            if pop_filters:
                pop_filter = pop_filters[0]
                for pf in pop_filters[1:]:
                    pop_filter &= pf
                self._ht = self._ht.filter(hl.is_missing(pop_expr) | pop_filter)

    def _filter_by_in_silico(self, in_silico_filters):
        in_silico_filters = in_silico_filters or {}
        require_score = in_silico_filters.get('requireScore', False)
        in_silico_filters = {k: v for k, v in in_silico_filters.items() if k in self.PREDICTION_FIELDS_CONFIG and v}
        if not in_silico_filters:
            return

        in_silico_qs = []
        missing_qs = []
        for in_silico, value in in_silico_filters.items():
            score_filter, ht_value = self._get_in_silico_filter(in_silico, value)
            in_silico_qs.append(score_filter)
            if not require_score:
                missing_qs.append(hl.is_missing(ht_value))

        if missing_qs:
            missing_q = missing_qs[0]
            for q in missing_qs[1:]:
                missing_q &= q
            in_silico_qs.append(missing_q)

        self._ht = self._ht.filter(self._or_filter(in_silico_qs))

    def _get_in_silico_filter(self, in_silico, value):
        score_path = self.PREDICTION_FIELDS_CONFIG[in_silico]
        enum_lookup = self._get_enum_lookup(*score_path)
        if enum_lookup is not None:
            ht_value = self._ht[score_path.source][f'{score_path.field}_id']
            score_filter = ht_value == enum_lookup[value]
        else:
            ht_value = self._ht[score_path.source][score_path.field]
            score_filter = ht_value >= float(value)

        return score_filter, ht_value

    def _filter_by_annotations(self, pathogenicity, annotations):
        annotation_override_filters = self._get_annotation_override_filters(pathogenicity, annotations)

        self._annotate_allowed_consequences(annotations, annotation_override_filters)
        if 'has_allowed_annotation' in self._ht.row:
            self._ht = self._ht.filter(self._ht.has_allowed_annotation)

    def _annotate_allowed_consequences(self, annotations, annotation_filters):
        raise NotImplementedError

    def _get_annotation_override_filters(self, pathogenicity, annotations):
        return []

    @staticmethod
    def _or_filter(filters):
        if not filters:
            return None
        filter_expr = filters[0]
        for f in filters[1:]:
            filter_expr |= f
        return filter_expr

    def _format_results(self, ht):
        annotations = {k: v(ht) for k, v in self.annotation_fields().items()}
        annotations.update({
            '_sort': self._sort_order(ht),
            'genomeVersion': self._genome_version.replace('GRCh', ''),
        })
        results = ht.annotate(**annotations)
        return results.select(*self.CORE_FIELDS, *list(annotations.keys()))

    def search(self):
        ht = self._format_results(self._ht)

        (total_results, collected) = ht.aggregate((hl.agg.count(), hl.agg.take(ht.row, self._num_results, ordering=ht._sort)))
        logger.info(f'Total hits: {total_results}. Fetched: {self._num_results}')

        return collected, total_results

    def _sort_order(self, ht):
        sort_expressions = self._get_sort_expressions(ht, XPOS)
        if self._sort != XPOS:
            sort_expressions = self._get_sort_expressions(ht, self._sort) + sort_expressions
        return sort_expressions

    def _get_sort_expressions(self, ht, sort):
        return self.SORTS[sort](ht)


class VariantHailTableQuery(BaseHailTableQuery):

    GENOTYPE_FIELDS = {f.lower(): f for f in ['DP', 'GQ', 'AB']}
    QUALITY_FILTER_FORMAT = {
        'AB': QualityFilterFormat(override=lambda gt: ~gt.GT.is_het(), scale=100),
    }
    POPULATIONS = {
        'seqr': {'hom': 'hom', 'hemi': None, 'het': None},
        'topmed': {'hemi': None},
        'exac': {
            'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi',
            'het': 'AC_Het',
        },
        'gnomad_exomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
        GNOMAD_GENOMES_FIELD: {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
    }
    POPULATION_FIELDS = {'seqr': 'gt_stats'}
    PREDICTION_FIELDS_CONFIG = {
        'cadd': PredictionPath('cadd', 'PHRED'),
        'eigen': PredictionPath('eigen', 'Eigen_phred'),
        'fathmm': PredictionPath('dbnsfp', 'fathmm_MKL_coding_pred'),
        'gnomad_noncoding': PredictionPath('gnomad_non_coding_constraint', 'z_score'),
        'mpc': PredictionPath('mpc', 'MPC'),
        'mut_pred': PredictionPath('dbnsfp', 'MutPred_score'),
        'primate_ai': PredictionPath('primate_ai', 'score'),
        SPLICE_AI_FIELD: PredictionPath(SPLICE_AI_FIELD, 'delta_score'),
        'splice_ai_consequence': PredictionPath(SPLICE_AI_FIELD, 'splice_consequence'),
        'vest': PredictionPath('dbnsfp', 'VEST4_score'),
        'mut_taster': PredictionPath('dbnsfp', 'MutationTaster_pred'),
        'polyphen': PredictionPath('dbnsfp', 'Polyphen2_HVAR_pred'),
        'revel': PredictionPath('dbnsfp', 'REVEL_score'),
        'sift': PredictionPath('dbnsfp', 'SIFT_pred'),
    }
    PATHOGENICITY_FILTERS = [
        (CLINVAR_KEY, 'pathogenicity', CLINVAR_PATH_RANGES),
        (HGMD_KEY, 'class', HGMD_PATH_RANGES),
    ]

    GLOBALS = BaseHailTableQuery.GLOBALS + ['versions']
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid']
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),
        'mainTranscriptId': lambda r: r.sorted_transcript_consequences.first().transcript_id,
        'selectedMainTranscriptId': lambda r: hl.or_missing(
            r.selected_transcript != r.sorted_transcript_consequences.first(), r.selected_transcript.transcript_id,
        ),
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)
    ENUM_ANNOTATION_FIELDS = {
        'clinvar': {'annotate_value': lambda value, enum, ht_globals: {
            'conflictingPathogenicities': value.conflictingPathogenicities.map(
                lambda p: VariantHailTableQuery._enum_field(p, {k: enum[k] for k in ['pathogenicity']})
            ),
            'version': ht_globals['versions'].clinvar,
        }},
        'hgmd': {},
        'screen': {
            'response_key': 'screenRegionType',
            'format_value': lambda value: value.region_types.first(),
        },
    }

    @staticmethod
    def _selected_main_transcript_expr(ht):
        has_gene_transcripts = 'gene_transcripts' in ht.row
        has_allowed_transcripts = 'allowed_transcripts' in ht.row

        main_transcript = ht.sorted_transcript_consequences.first()
        if has_gene_transcripts:
            matched_transcript = ht.gene_transcripts.first()
            if has_allowed_transcripts:
                allowed_transcript_ids = hl.set(ht.allowed_transcripts.map(lambda t: t.transcript_id))
                matched_transcript = hl.or_else(
                    ht.gene_transcripts.find(lambda t: allowed_transcript_ids.contains(t.transcript_id)),
                    matched_transcript,
                )
        elif has_allowed_transcripts:
            matched_transcript = ht.allowed_transcripts.first()
        else:
            matched_transcript = main_transcript

        return hl.or_else(matched_transcript, main_transcript)

    def import_filtered_table(self, *args, **kwargs):
        super(VariantHailTableQuery, self).import_filtered_table(*args, **kwargs)
        self._ht = self._ht.key_by(**{VARIANT_KEY_FIELD: self._ht.variant_id})

    def _format_transcript_args(self):
        args = super(VariantHailTableQuery, self)._format_transcript_args()
        args.update({
            'annotate_value': lambda transcript, *args: {'major_consequence': transcript.consequence_terms.first()},
            'drop_fields': ['consequence_terms'],
        })
        return args

    def _get_gene_id_filter(self, gene_ids):
        self._ht = self._ht.annotate(
            gene_transcripts=self._ht.sorted_transcript_consequences.filter(lambda t: gene_ids.contains(t.gene_id))
        )
        return hl.is_defined(self._ht.gene_transcripts.first())

    def _annotate_allowed_consequences(self, annotations, annotation_filters):
        allowed_consequences = {
            ann for field, anns in (annotations or {}).items()
            if anns and (field not in ANNOTATION_OVERRIDE_FIELDS) for ann in anns
        }
        consequence_enum = self._get_enum_lookup('sorted_transcript_consequences', 'consequence_term')
        allowed_consequence_ids = {consequence_enum[c] for c in allowed_consequences if consequence_enum.get(c)}

        annotation_exprs = {}
        if allowed_consequence_ids:
            allowed_consequence_ids = hl.set(allowed_consequence_ids)
            allowed_transcripts = self._ht.sorted_transcript_consequences.filter(
                lambda tc: tc.consequence_term_ids.any(allowed_consequence_ids.contains)
            )
            annotation_exprs['allowed_transcripts'] = allowed_transcripts
            annotation_filters = annotation_filters + [hl.is_defined(allowed_transcripts.first())]

        consequence_filter = self._or_filter(annotation_filters)
        if consequence_filter is not None:
            annotation_exprs['has_allowed_annotation'] = consequence_filter

        if annotation_exprs:
            self._ht = self._ht.annotate(**annotation_exprs)

    def _get_annotation_override_filters(self, pathogenicity, annotations):
        annotation_filters = []

        for key, *args in self.PATHOGENICITY_FILTERS:
            path_terms = (pathogenicity or {}).get(key)
            if path_terms:
                annotation_filters.append(self._has_terms_range_expr(path_terms, key, *args))
        if (annotations or {}).get(SCREEN_KEY):
            screen_enum = self._get_enum_lookup(SCREEN_KEY.lower(), 'region_type')
            allowed_consequences = hl.set({screen_enum[c] for c in annotations[SCREEN_KEY]})
            annotation_filters.append(allowed_consequences.contains(self._ht.screen.region_type_ids.first()))
        if (annotations or {}).get(SPLICE_AI_FIELD):
            score_filter, _ = self._get_in_silico_filter(SPLICE_AI_FIELD, annotations[SPLICE_AI_FIELD])
            annotation_filters.append(score_filter)

        return annotation_filters

    def _has_terms_range_expr(self, terms, field, subfield, range_configs):
        enum_lookup = self._get_enum_lookup(field, subfield)

        ranges = [[None, None]]
        for path_filter, start, end in range_configs:
            if path_filter in terms:
                ranges[-1][1] = len(enum_lookup) if end is None else enum_lookup[end]
                if ranges[-1][0] is None:
                    ranges[-1][0] = enum_lookup[start]
            else:
                ranges.append([None, None])

        ranges = [r for r in ranges if r[0] is not None]
        value = self._ht[field][f'{subfield}_id']
        return self._or_filter([(value >= r[0]) & (value <= r[1]) for r in ranges])

    def _format_results(self, ht):
        ht = ht.annotate(selected_transcript=self._selected_main_transcript_expr(ht))
        return super(VariantHailTableQuery, self)._format_results(ht)


QUERY_CLASS_MAP = {
    VARIANT_DATASET: VariantHailTableQuery,
}
