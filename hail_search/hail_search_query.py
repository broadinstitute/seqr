from aiohttp.web import HTTPBadRequest
from collections import defaultdict, namedtuple
import hail as hl
import logging
import os

from hail_search.constants import AFFECTED, UNAFFECTED, AFFECTED_ID, UNAFFECTED_ID, MALE, VARIANT_DATASET, \
    VARIANT_KEY_FIELD, GNOMAD_GENOMES_FIELD, XPOS, GENOME_VERSION_GRCh38, INHERITANCE_FILTERS, \
    ANY_AFFECTED, X_LINKED_RECESSIVE, REF_REF, REF_ALT, COMP_HET_ALT, ALT_ALT, HAS_ALT, HAS_REF, \
    ANNOTATION_OVERRIDE_FIELDS, SCREEN_KEY, SPLICE_AI_FIELD, CLINVAR_KEY, HGMD_KEY, CLINVAR_PATH_SIGNIFICANCES, \
    CLINVAR_PATH_FILTER, CLINVAR_LIKELY_PATH_FILTER, CLINVAR_PATH_RANGES, HGMD_PATH_RANGES, PATH_FREQ_OVERRIDE_CUTOFF, \
    PREFILTER_FREQ_CUTOFF, COMPOUND_HET, RECESSIVE, GROUPED_VARIANTS_FIELD, NEW_SV_FIELD, HAS_ALLOWED_ANNOTATION, \
    HAS_ALLOWED_SECONDARY_ANNOTATION, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, ABSENT_PATH_SORT_OFFSET, \
    STRUCTURAL_ANNOTATION_FIELD

DATASETS_DIR = os.environ.get('DATASETS_DIR', '/hail_datasets')

logger = logging.getLogger(__name__)


PredictionPath = namedtuple('PredictionPath', ['source', 'field'])
QualityFilterFormat = namedtuple('QualityFilterFormat', ['scale', 'override'], defaults=[None, None])


def _to_camel_case(snake_case_str):
    converted = snake_case_str.replace('_', ' ').title().replace(' ', '')
    return converted[0].lower() + converted[1:]


class BaseHailTableQuery(object):

    DATA_TYPE = None
    LOADED_GLOBALS = None

    GENOTYPE_QUERY_MAP = {
        REF_REF: lambda gt: gt.is_hom_ref(),
        REF_ALT: lambda gt: gt.is_het(),
        COMP_HET_ALT: lambda gt: gt.is_het(),
        ALT_ALT: lambda gt: gt.is_hom_var(),
        HAS_ALT: lambda gt: gt.is_non_ref(),
        HAS_REF: lambda gt: gt.is_hom_ref() | gt.is_het_ref(),
    }

    GENOTYPE_FIELDS = {}
    NESTED_GENOTYPE_FIELDS = {}
    GENOTYPE_QUERY_FIELDS = {}
    QUALITY_FILTER_FORMAT = {}
    POPULATIONS = {}
    POPULATION_FIELDS = {}
    POPULATION_KEYS = ['AF', 'AC', 'AN', 'Hom', 'Hemi', 'Het']
    PREDICTION_FIELDS_CONFIG = {}

    GENOME_VERSIONS = [GENOME_VERSION_GRCh38]
    GLOBALS = ['enums']
    TRANSCRIPTS_FIELD = None
    CORE_FIELDS = [XPOS]
    BASE_ANNOTATION_FIELDS = {
        'familyGuids': lambda r: r.family_entries.filter(hl.is_defined).map(lambda entries: entries.first().familyGuid),
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),
    }
    ENUM_ANNOTATION_FIELDS = {
        'transcripts': {
            'response_key': 'transcripts',
            'empty_array': True,
            'format_value': lambda value: value.rename({k: _to_camel_case(k) for k in value.keys()}),
            'format_values': lambda values: values.group_by(lambda t: t.geneId),
        },
    }
    LIFTOVER_ANNOTATION_FIELDS = {
        'liftedOverGenomeVersion': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), '37'),
        'liftedOverChrom': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), r.rg37_locus.contig),
        'liftedOverPos': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), r.rg37_locus.position),
    }

    SORTS = {
        XPOS: lambda r: [r.xpos],
    }

    @classmethod
    def load_globals(cls):
        cls.LOADED_GLOBALS = {}
        for genome_version in cls.GENOME_VERSIONS:
            ht_path = cls._get_generic_table_path(genome_version, 'annotations.ht')
            ht_globals = hl.eval(hl.read_table(ht_path).globals.select(*cls.GLOBALS))
            cls.LOADED_GLOBALS[genome_version] = {k: ht_globals[k] for k in cls.GLOBALS}

    @classmethod
    def _format_population_config(cls, pop_config):
        base_pop_config = {field.lower(): field for field in cls.POPULATION_KEYS}
        base_pop_config.update(pop_config)
        base_pop_config.pop('sort', None)
        return base_pop_config

    def annotation_fields(self):
        annotation_fields = {
            'genotypes': lambda r: r.family_entries.flatmap(lambda x: x).filter(
                lambda gt: hl.is_defined(gt.individualGuid)
            ).group_by(lambda x: x.individualGuid).map_values(lambda x: x[0].select(
                'sampleId', 'individualGuid', 'familyGuid',
                numAlt=hl.if_else(hl.is_defined(x[0].GT), x[0].GT.n_alt_alleles(), -1),
                **{k: x[0][field] for k, field in self.GENOTYPE_FIELDS.items()},
                **{_to_camel_case(k): x[0][field][k] for field, v in self.NESTED_GENOTYPE_FIELDS.items() for k in v},
            )),
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population) for population in self.POPULATIONS.keys()
            }),
            'predictions': lambda r: hl.struct(**{
                prediction: self._format_enum(r[path.source], path.field, self._enums[path.source][path.field])
                if self._enums.get(path.source, {}).get(path.field) else r[path.source][path.field]
                for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)
        annotation_fields.update(self._additional_annotation_fields())

        prediction_fields = {path.source for path in self.PREDICTION_FIELDS_CONFIG.values()}
        annotation_fields.update([
            self._format_enum_response(k, enum) for k, enum in self._enums.items()
            if enum and k not in prediction_fields
        ])

        if self._genome_version == GENOME_VERSION_GRCh38:
            annotation_fields.update(self.LIFTOVER_ANNOTATION_FIELDS)
        return annotation_fields

    def _additional_annotation_fields(self):
        return {}

    def population_expression(self, r, population):
        pop_config = self._format_population_config(self.POPULATIONS[population])
        pop_field = self.POPULATION_FIELDS.get(population, population)
        return hl.struct(**{
            response_key: hl.or_else(r[pop_field][field], '' if response_key == 'id' else 0)
            for response_key, field in pop_config.items() if field is not None
        })

    def _get_enum_lookup(self, field, subfield):
        enum_field = self._enums.get(field, {})
        if subfield:
            enum_field = enum_field.get(subfield)
        if enum_field is None:
            return None
        return {v: i for i, v in enumerate(enum_field)}

    def _get_enum_terms_ids(self, field, subfield, terms):
        enum = self._get_enum_lookup(field, subfield)
        return {enum[t] for t in terms if enum.get(t)}

    def _format_enum_response(self, k, enum):
        enum_config = self.ENUM_ANNOTATION_FIELDS.get(k, {})
        value = lambda r: self._format_enum(r, k, enum, ht_globals=self._globals, **enum_config)
        return enum_config.get('response_key', _to_camel_case(k)), value

    @classmethod
    def _format_enum(cls, r, field, enum, empty_array=False, format_values=None, **kwargs):
        if hasattr(r, f'{field}_id'):
            return hl.array(enum)[r[f'{field}_id']]

        value = r[field]
        if hasattr(value, 'map'):
            if empty_array:
                value = hl.or_else(value, hl.empty_array(value.dtype.element_type))
            value = value.map(lambda x: cls._enum_field(x, enum, **kwargs))
            if format_values:
                value = format_values(value)
            return value

        return cls._enum_field(value, enum, **kwargs)

    @staticmethod
    def _enum_field(value, enum, ht_globals=None, annotate_value=None, format_value=None, drop_fields=None, enum_keys=None, **kwargs):
        annotations = {}
        drop = [] + (drop_fields or [])
        value_keys = value.keys()
        for field in (enum_keys or enum.keys()):
            field_enum = enum[field]
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

    def __init__(self, sample_data, genome_version, sort=XPOS, sort_metadata=None, num_results=100, inheritance_mode=None, **kwargs):
        self._genome_version = genome_version
        self._sort = sort
        self._sort_metadata = sort_metadata
        self._num_results = num_results
        self._ht = None
        self._comp_het_ht = None
        self._inheritance_mode = inheritance_mode
        self._load_table_kwargs = {}

        self._load_filtered_table(sample_data, inheritance_mode=inheritance_mode, **kwargs)

    @property
    def _is_recessive_search(self):
        return self._inheritance_mode == RECESSIVE

    @property
    def _has_comp_het_search(self):
        return self._inheritance_mode in {RECESSIVE, COMPOUND_HET}

    @property
    def _globals(self):
        return self.LOADED_GLOBALS[self._genome_version]

    @property
    def _enums(self):
        return self._globals['enums']

    def _load_filtered_table(self, sample_data, intervals=None, variant_ids=None, **kwargs):
        parsed_intervals, variant_ids = self._parse_intervals(intervals, variant_ids, **kwargs)
        self.import_filtered_table(
            sample_data, parsed_intervals=parsed_intervals, variant_ids=variant_ids, **kwargs)

        if self._has_comp_het_search:
            self._comp_het_ht = self._filter_compound_hets()
            if self._is_recessive_search:
                self._ht = self._ht.filter(self._ht.family_entries.any(hl.is_defined))
                if HAS_ALLOWED_SECONDARY_ANNOTATION in self._ht.row:
                    self._ht = self._ht.filter(self._ht[HAS_ALLOWED_ANNOTATION]).drop(HAS_ALLOWED_SECONDARY_ANNOTATION)
            else:
                self._ht = None

    @classmethod
    def _get_generic_table_path(cls, genome_version, path):
        return f'{DATASETS_DIR}/{genome_version}/{cls.DATA_TYPE}/{path}'

    def _get_table_path(self, path):
        return self._get_generic_table_path(self._genome_version, path)

    def _read_table(self, path):
        return hl.read_table(self._get_table_path(path), **self._load_table_kwargs)

    def import_filtered_table(self, sample_data, intervals=None, **kwargs):
        family_samples = defaultdict(list)
        project_samples = defaultdict(list)
        for s in sample_data:
            family_samples[s['family_guid']].append(s)
            project_samples[s['project_guid']].append(s)

        logger.info(f'Loading {self.DATA_TYPE} data for {len(family_samples)} families in {len(project_samples)} projects')
        if len(family_samples) == 1:
            family_guid, family_sample_data = list(family_samples.items())[0]
            family_ht = self._read_table(f'families/{family_guid}.ht')
            families_ht, _ = self._filter_entries_table(family_ht, family_sample_data, **kwargs)
        else:
            filtered_project_hts = []
            exception_messages = set()
            for project_guid, project_sample_data in project_samples.items():
                project_ht = self._read_table(f'projects/{project_guid}.ht')
                try:
                    filtered_project_hts.append(self._filter_entries_table(project_ht, project_sample_data, **kwargs))
                except HTTPBadRequest as e:
                    exception_messages.add(e.reason)

            if exception_messages:
                raise HTTPBadRequest(reason='; '.join(exception_messages))

            families_ht, num_families = filtered_project_hts[0]
            entry_type = families_ht.family_entries.dtype.element_type
            for project_ht, num_project_families in filtered_project_hts[1:]:
                families_ht = families_ht.join(project_ht, how='outer')
                select_fields = {
                    'filters': families_ht.filters.union(families_ht.filters_1),
                    'family_entries': hl.bind(
                        lambda a1, a2: a1.extend(a2),
                        hl.or_else(families_ht.family_entries, hl.empty_array(entry_type)),
                        hl.or_else(families_ht.family_entries_1, hl.empty_array(entry_type)),
                    ),
                }
                if 'comp_het_family_entries_1' in families_ht.row:
                    missing_arr = lambda count: hl.range(count).map(lambda i: hl.missing(entry_type))
                    select_fields['comp_het_family_entries'] = hl.bind(
                        lambda a1, a2: a1.extend(a2),
                        hl.or_else(families_ht.comp_het_family_entries, missing_arr(num_families)),
                        hl.or_else(families_ht.comp_het_family_entries_1, missing_arr(num_project_families)),
                    )
                families_ht = families_ht.select(**select_fields)
                num_families += num_project_families

        annotations_ht_path = self._get_table_path('annotations.ht')
        annotation_ht_query_result = hl.query_table(
            annotations_ht_path, families_ht.key).first().drop(*families_ht.key)
        self._ht = families_ht.annotate(**annotation_ht_query_result)

        self._filter_annotated_table(**kwargs)
        self._ht = self._ht.key_by(**{VARIANT_KEY_FIELD: self._ht.variant_id})

    def _filter_entries_table(self, ht, sample_data, inheritance_mode=None, inheritance_filter=None, quality_filter=None,
                              variant_ids=None, **kwargs):

        if variant_ids:
            ht = self._filter_variant_ids(ht, variant_ids)
        elif not self._load_table_kwargs.get('_intervals'):
            ht = self._prefilter_entries_table(ht, **kwargs)

        ht, sample_id_family_index_map, num_families = self._add_entry_sample_families(ht, sample_data)

        quality_filter = quality_filter or {}
        if quality_filter.get('vcf_filter'):
            ht = self._filter_vcf_filters(ht)

        passes_quality_filter = self._get_family_passes_quality_filter(quality_filter, ht=ht, **kwargs)
        if passes_quality_filter is not None:
            ht = ht.annotate(family_entries=ht.family_entries.map(
                lambda entries: hl.or_missing(passes_quality_filter(entries), entries)
            ))
            ht = ht.filter(ht.family_entries.any(hl.is_defined))

        ht = self._filter_inheritance(
            ht, inheritance_mode, inheritance_filter, sample_data, sample_id_family_index_map,
        )

        return ht.select_globals(), num_families

    @classmethod
    def _add_entry_sample_families(cls, ht, sample_data):
        sample_index_id_map = dict(enumerate(hl.eval(ht.sample_ids)))
        sample_id_index_map = {v: k for k, v in sample_index_id_map.items()}
        sample_index_id_map = hl.dict(sample_index_id_map)
        sample_individual_map = {s['sample_id']: s['individual_guid'] for s in sample_data}
        missing_samples = set(sample_individual_map.keys()) - set(sample_id_index_map.keys())
        if missing_samples:
            raise HTTPBadRequest(
                reason=f'The following samples are available in seqr but missing the loaded data: {", ".join(sorted(missing_samples))}'
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
        num_families = len(family_index_map)
        family_sample_indices = [None] * num_families
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

        return ht, sample_id_family_index_map, num_families

    @classmethod
    def _missing_entry(cls, entry):
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

        if inheritance_mode == X_LINKED_RECESSIVE:
            x_chrom_interval = hl.parse_locus_interval(
                hl.get_reference(self._genome_version).x_contigs[0], reference_genome=self._genome_version)
            ht = ht.filter(self.get_x_chrom_filter(ht, x_chrom_interval))

        filter_mode_map = {}
        if (inheritance_filter or inheritance_mode) and not is_any_affected:
            filter_mode_map[inheritance_mode] = 'family_entries'
        if self._has_comp_het_search:
            filter_mode_map[COMPOUND_HET] = 'comp_het_family_entries'

        for mode, field in sorted(filter_mode_map.items()):
            ht = self._filter_families_inheritance(
                ht, mode, inheritance_filter, sample_id_family_index_map, sample_data, field,
            )

        filter_expr = ht.family_entries.any(hl.is_defined)
        if self._has_comp_het_search:
            ch_filter = ht.comp_het_family_entries.any(hl.is_defined)
            filter_expr = (filter_expr | ch_filter) if self._is_recessive_search else ch_filter

        return ht.filter(filter_expr)

    @classmethod
    def _filter_families_inheritance(cls, ht, inheritance_mode, inheritance_filter, sample_id_family_index_map, sample_data, field):
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
            ht = ht.annotate(**{field: hl.enumerate(ht.family_entries).map(
                lambda x: cls._valid_genotype_family_entries(x[1], entry_indices.get(x[0]), genotype, inheritance_mode)
            )})

        return ht

    @classmethod
    def _valid_genotype_family_entries(cls, entries, gentoype_entry_indices, genotype, inheritance_mode):
        is_valid = hl.is_missing(gentoype_entry_indices) | gentoype_entry_indices.all(
            lambda i: cls.GENOTYPE_QUERY_MAP[genotype](entries[i].GT)
        )
        if inheritance_mode == COMPOUND_HET and genotype == HAS_REF:
            is_valid &= ((gentoype_entry_indices.size() < 2) | gentoype_entry_indices.any(
                lambda i: cls.GENOTYPE_QUERY_MAP[REF_REF](entries[i].GT)
            ))
        return hl.or_missing(is_valid, entries)

    def _get_family_passes_quality_filter(self, quality_filter, **kwargs):
        affected_only = quality_filter.get('affected_only')
        passes_quality_filters = []
        for filter_k, value in quality_filter.items():
            genotype_key = filter_k.replace('min_', '')
            field = self.GENOTYPE_QUERY_FIELDS.get(genotype_key, self.GENOTYPE_FIELDS.get(genotype_key))
            if field and value:
                passes_quality_filters.append(self._get_genotype_passes_quality_field(field, value, affected_only))

        if not passes_quality_filters:
            return None

        return lambda entries: entries.all(lambda gt: hl.all([f(gt) for f in passes_quality_filters]))

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
        raise NotImplementedError

    def _prefilter_entries_table(self, ht, **kwargs):
        return ht

    def _filter_annotated_table(self, gene_ids=None, rs_ids=None, frequencies=None, in_silico=None, pathogenicity=None,
                                annotations=None, annotations_secondary=None, **kwargs):
        if gene_ids:
            self._filter_by_gene_ids(gene_ids)

        if rs_ids:
            self._filter_rs_ids(rs_ids)

        self._filter_by_frequency(frequencies, pathogenicity)

        self._filter_by_in_silico(in_silico)

        self._filter_by_annotations(pathogenicity, annotations, annotations_secondary)

    def _filter_by_gene_ids(self, gene_ids):
        gene_ids = hl.set(gene_ids)
        self._ht = self._ht.annotate(
            gene_transcripts=self._ht[self.TRANSCRIPTS_FIELD].filter(lambda t: gene_ids.contains(t.gene_id))
        )
        self._ht = self._ht.filter(hl.is_defined(self._ht.gene_transcripts.first()))

    def _filter_rs_ids(self, rs_ids):
        rs_id_set = hl.set(rs_ids)
        self._ht = self._ht.filter(rs_id_set.contains(self._ht.rsid))

    def _parse_intervals(self, intervals, variant_ids, **kwargs):
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
            raise HTTPBadRequest(reason=f'Invalid intervals: {", ".join(invalid_intervals)}')

        return parsed_intervals, variant_ids

    def _filter_by_frequency(self, frequencies, pathogenicity):
        frequencies = {k: v for k, v in (frequencies or {}).items() if k in self.POPULATIONS}
        if not frequencies:
            return

        path_override_filter = self._frequency_override_filter(pathogenicity)
        filters = []
        for pop, freqs in sorted(frequencies.items()):
            pop_filters = []
            pop_expr = self._ht[self.POPULATION_FIELDS.get(pop, pop)]
            pop_config = self._format_population_config(self.POPULATIONS[pop])
            if freqs.get('af') is not None:
                af_field = pop_config.get('filter_af') or pop_config['af']
                pop_filter = pop_expr[af_field] <= freqs['af']
                if path_override_filter is not None and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= path_override_filter & (pop_expr[af_field] <= PATH_FREQ_OVERRIDE_CUTOFF)
                pop_filters.append(pop_filter)
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
                filters.append(hl.is_missing(pop_expr) | hl.all(pop_filters))

        if filters:
            self._ht = self._ht.filter(hl.all(filters))

    def _frequency_override_filter(self, pathogenicity):
        return None

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
            in_silico_qs.append(hl.all(missing_qs))

        self._ht = self._ht.filter(hl.any(in_silico_qs))

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

    def _filter_by_annotations(self, pathogenicity, annotations, annotations_secondary):
        annotations = annotations or {}
        annotation_override_filters = self._get_annotation_override_filters(annotations, pathogenicity=pathogenicity)

        annotation_exprs = self._get_allowed_consequences_annotations(annotations, annotation_override_filters)
        secondary_exprs = self._get_allowed_consequences_annotations(annotations_secondary or {}, annotation_override_filters, is_secondary=True)
        has_secondary_annotations = 'allowed_transcripts' in secondary_exprs
        if has_secondary_annotations:
            annotation_exprs.update({f'{k}_secondary': v for k, v in secondary_exprs.items()})

        if not annotation_exprs:
            return

        self._ht = self._ht.annotate(**annotation_exprs)
        annotation_filter = self._ht[HAS_ALLOWED_ANNOTATION]
        if has_secondary_annotations:
            annotation_filter |= self._ht[HAS_ALLOWED_SECONDARY_ANNOTATION]
        self._ht = self._ht.filter(annotation_filter)

    def _get_allowed_consequences_annotations(self, annotations, annotation_filters, is_secondary=False):
        allowed_consequences = {
            ann for field, anns in annotations.items()
            if anns and (field not in ANNOTATION_OVERRIDE_FIELDS) for ann in anns
        }
        allowed_consequence_ids = self._get_enum_terms_ids(
            self.TRANSCRIPTS_FIELD, self.TRANSCRIPT_CONSEQUENCE_FIELD, allowed_consequences)

        annotation_exprs = {}
        if allowed_consequence_ids:
            allowed_consequence_ids = hl.set(allowed_consequence_ids)
            consequence_filter = self._get_consequence_filter(allowed_consequence_ids, annotation_exprs)
            annotation_filters = annotation_filters + [consequence_filter]

        if annotation_filters:
            annotation_exprs[HAS_ALLOWED_ANNOTATION] = hl.any(annotation_filters)

        return annotation_exprs

    def _get_consequence_filter(self, allowed_consequence_ids, annotation_exprs):
        raise NotImplementedError

    def _get_annotation_override_filters(self, annotations, **kwargs):
        return []

    def _filter_compound_hets(self):
        ch_ht = self._ht
        if self._is_recessive_search:
            ch_ht = ch_ht.filter(ch_ht.comp_het_family_entries.any(hl.is_defined))

        # Get possible pairs of variants within the same gene
        ch_ht = ch_ht.annotate(gene_ids=self._gene_ids_expr(ch_ht))
        ch_ht = ch_ht.explode(ch_ht.gene_ids)
        formatted_rows_expr = hl.agg.collect(ch_ht.row)
        if HAS_ALLOWED_SECONDARY_ANNOTATION in self._ht.row:
            primary_variants = hl.agg.filter(ch_ht[HAS_ALLOWED_ANNOTATION], formatted_rows_expr)
            secondary_variants = hl.agg.filter(ch_ht[HAS_ALLOWED_SECONDARY_ANNOTATION], formatted_rows_expr)
        else:
            primary_variants = formatted_rows_expr
            secondary_variants = formatted_rows_expr

        ch_ht = ch_ht.group_by('gene_ids').aggregate(v1=primary_variants, v2=secondary_variants)
        ch_ht = ch_ht.explode(ch_ht.v1)
        ch_ht = ch_ht.explode(ch_ht.v2)
        ch_ht = ch_ht.filter(ch_ht.v1[VARIANT_KEY_FIELD] != ch_ht.v2[VARIANT_KEY_FIELD])

        # Filter variant pairs for family and genotype
        ch_ht = ch_ht.annotate(valid_families=hl.enumerate(ch_ht.v1.comp_het_family_entries).map(
            lambda x: self._is_valid_comp_het_family(x[1], ch_ht.v2.comp_het_family_entries[x[0]])
        ))
        ch_ht = ch_ht.filter(ch_ht.valid_families.any(lambda x: x))

        # Format pairs as lists and de-duplicate
        ch_ht = ch_ht.key_by(**{
            VARIANT_KEY_FIELD: hl.str(':').join(hl.sorted([ch_ht.v1[VARIANT_KEY_FIELD], ch_ht.v2[VARIANT_KEY_FIELD]]))
        })
        ch_ht = ch_ht.distinct()
        ch_ht = ch_ht.select(**{GROUPED_VARIANTS_FIELD: hl.array([ch_ht.v1, ch_ht.v2]).map(lambda v: v.annotate(
            gene_id=ch_ht.gene_ids,
            family_entries=hl.enumerate(ch_ht.valid_families).filter(
                lambda x: x[1]).map(lambda x: v.comp_het_family_entries[x[0]]),
        ))})

        return ch_ht

    @classmethod
    def _gene_ids_expr(cls, ht):
        return hl.set(ht[cls.TRANSCRIPTS_FIELD].map(lambda t: t.gene_id))

    def _is_valid_comp_het_family(self, entries_1, entries_2):
        return hl.is_defined(entries_1) & hl.is_defined(entries_2) & hl.enumerate(entries_1).all(lambda x: hl.any([
            (x[1].affected_id != UNAFFECTED_ID),
            self.GENOTYPE_QUERY_MAP[REF_REF](x[1].GT),
            self.GENOTYPE_QUERY_MAP[REF_REF](entries_2[x[0]].GT),
        ]))

    def _format_comp_het_results(self, ch_ht, annotation_fields):
        formatted_grouped_variants = ch_ht[GROUPED_VARIANTS_FIELD].map(
            lambda v: self._format_results(v, annotation_fields).annotate(**{VARIANT_KEY_FIELD: v[VARIANT_KEY_FIELD]})
        )
        ch_ht = ch_ht.annotate(**{GROUPED_VARIANTS_FIELD: hl.sorted(formatted_grouped_variants, key=lambda x: x._sort)})
        return ch_ht.annotate(_sort=ch_ht[GROUPED_VARIANTS_FIELD][0]._sort)

    def _format_results(self, ht, annotation_fields):
        annotations = {k: v(ht) for k, v in annotation_fields.items()}
        annotations.update({
            '_sort': self._sort_order(ht),
            'genomeVersion': self._genome_version.replace('GRCh', ''),
        })
        results = ht.annotate(**annotations)
        return results.select(*self.CORE_FIELDS, *list(annotations.keys()))

    def search(self):
        ch_ht = None
        annotation_fields = self.annotation_fields()
        if self._comp_het_ht:
            ch_ht = self._format_comp_het_results(self._comp_het_ht, annotation_fields)

        if self._ht:
            ht = self._format_results(self._ht, annotation_fields)
            if ch_ht:
                ht = ht.join(ch_ht, 'outer')
                ht = ht.transmute(_sort=hl.or_else(ht._sort, ht._sort_1))
        else:
            ht = ch_ht

        (total_results, collected) = ht.aggregate((hl.agg.count(), hl.agg.take(ht.row, self._num_results, ordering=ht._sort)))
        logger.info(f'Total hits: {total_results}. Fetched: {self._num_results}')

        if self._comp_het_ht:
            collected = [row.get(GROUPED_VARIANTS_FIELD) or row.drop(GROUPED_VARIANTS_FIELD) for row in collected]
        return collected, total_results

    def _sort_order(self, ht):
        sort_expressions = self._get_sort_expressions(ht, XPOS)
        if self._sort != XPOS:
            sort_expressions = self._get_sort_expressions(ht, self._sort) + sort_expressions
        return sort_expressions

    def _get_sort_expressions(self, ht, sort):
        if sort in self.SORTS:
            return self.SORTS[sort](ht)

        if sort in self.PREDICTION_FIELDS_CONFIG:
            prediction_path = self.PREDICTION_FIELDS_CONFIG[sort]
            return [-hl.float64(ht[prediction_path.source][prediction_path.field])]

        if sort == 'in_omim':
            return self._omim_sort(ht, hl.set(set(self._sort_metadata)))

        if self._sort_metadata:
            return self._gene_rank_sort(ht, hl.dict(self._sort_metadata))

        sort_field = next((field for field, config in self.POPULATIONS.items() if config.get('sort') == sort), None)
        if sort_field:
            return [hl.float64(self.population_expression(ht, sort_field).af)]

        return []

    @classmethod
    def _omim_sort(cls, r, omim_gene_set):
        return [-cls._gene_ids_expr(r).intersection(omim_gene_set).size()]

    @classmethod
    def _gene_rank_sort(cls, r, gene_ranks):
        return [hl.min(cls._gene_ids_expr(r).map(gene_ranks.get))]


class VariantHailTableQuery(BaseHailTableQuery):

    DATA_TYPE = VARIANT_DATASET

    TRANSCRIPTS_FIELD = 'sorted_transcript_consequences'
    TRANSCRIPT_CONSEQUENCE_FIELD = 'consequence_term'
    GENOTYPE_FIELDS = {f.lower(): f for f in ['DP', 'GQ', 'AB']}
    QUALITY_FILTER_FORMAT = {
        'AB': QualityFilterFormat(override=lambda gt: ~gt.GT.is_het(), scale=100),
    }
    POPULATIONS = {
        'seqr': {'hom': 'hom', 'hemi': None, 'het': None, 'sort': 'callset_af'},
        'topmed': {'hemi': None},
        'exac': {
            'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi',
            'het': 'AC_Het',
        },
        'gnomad_exomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None, 'sort': 'gnomad_exomes'},
        GNOMAD_GENOMES_FIELD: {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None, 'sort': 'gnomad'},
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
    PATHOGENICITY_FILTERS = {
        CLINVAR_KEY: ('pathogenicity', CLINVAR_PATH_RANGES),
        HGMD_KEY: ('class', HGMD_PATH_RANGES),
    }

    GLOBALS = BaseHailTableQuery.GLOBALS + ['versions']
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid']
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'mainTranscriptId': lambda r: r.sorted_transcript_consequences.first().transcript_id,
        'selectedMainTranscriptId': lambda r: hl.or_missing(
            r.selected_transcript != r.sorted_transcript_consequences.first(), r.selected_transcript.transcript_id,
        ),
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)
    ENUM_ANNOTATION_FIELDS = {
        'clinvar': {'annotate_value': lambda value, enum, ht_globals: {
            'conflictingPathogenicities': VariantHailTableQuery._format_enum(
                value, 'conflictingPathogenicities', enum, enum_keys=['pathogenicity']),
            'version': ht_globals['versions'].clinvar,
        }},
        'screen': {
            'response_key': 'screenRegionType',
            'format_value': lambda value: value.region_types.first(),
        },
        TRANSCRIPTS_FIELD: {
            **BaseHailTableQuery.ENUM_ANNOTATION_FIELDS['transcripts'],
            'annotate_value': lambda transcript, *args: {'major_consequence': transcript.consequence_terms.first()},
            'drop_fields': ['consequence_terms'],
        }
    }

    SORTS = {
        'protein_consequence': lambda r: [
            hl.min(r.sorted_transcript_consequences.flatmap(lambda t: t.consequence_term_ids)),
            hl.min(r.selected_transcript.consequence_term_ids),
        ],
        PATHOGENICTY_SORT_KEY: lambda r: [hl.or_else(r.clinvar.pathogenicity_id, ABSENT_PATH_SORT_OFFSET)],
    }
    SORTS[PATHOGENICTY_HGMD_SORT_KEY] = lambda r: VariantHailTableQuery.SORTS[PATHOGENICTY_SORT_KEY](r) + [r.hgmd.class_id]
    SORTS.update(BaseHailTableQuery.SORTS)

    @staticmethod
    def _selected_main_transcript_expr(ht):
        gene_id = getattr(ht, 'gene_id', None)
        if gene_id is not None:
            gene_transcripts = ht.sorted_transcript_consequences.filter(lambda t: t.gene_id == ht.gene_id)
        else:
            gene_transcripts = getattr(ht, 'gene_transcripts', None)

        allowed_transcripts = getattr(ht, 'allowed_transcripts', None)
        if hasattr(ht, HAS_ALLOWED_SECONDARY_ANNOTATION):
            allowed_transcripts = hl.if_else(
                allowed_transcripts.any(hl.is_defined), allowed_transcripts, ht.allowed_transcripts_secondary,
            ) if allowed_transcripts is not None else ht.allowed_transcripts_secondary

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
        super(VariantHailTableQuery, self).__init__(*args, **kwargs)

    def _parse_intervals(self, intervals, variant_ids, exclude_intervals=False, **kwargs):
        parsed_intervals, variant_ids = super()._parse_intervals(intervals, variant_ids, **kwargs)
        if parsed_intervals and not exclude_intervals:
            self._load_table_kwargs = {'_intervals': parsed_intervals, '_filter_intervals': True}
        return parsed_intervals, variant_ids

    def _get_family_passes_quality_filter(self, quality_filter, ht=None, pathogenicity=None, **kwargs):
        passes_quality = super(VariantHailTableQuery, self)._get_family_passes_quality_filter(quality_filter)
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
            variant_id_qs = [
                (ht.locus == hl.locus(chrom, pos, reference_genome=self._genome_version)) &
                (ht.alleles == [ref, alt])
                for chrom, pos, ref, alt in variant_ids
            ]
            variant_id_q = variant_id_qs[0]
            for q in variant_id_qs[1:]:
                variant_id_q |= q
        return ht.filter(variant_id_q)

    def _prefilter_entries_table(self, ht, parsed_intervals=None, exclude_intervals=False, **kwargs):
        if exclude_intervals and parsed_intervals:
            ht = hl.filter_intervals(ht, parsed_intervals, keep=False)
        af_ht = self._get_loaded_filter_ht(
            GNOMAD_GENOMES_FIELD, 'high_af_variants.ht', self._get_gnomad_af_prefilter, **kwargs)
        if af_ht:
            ht = ht.filter(hl.is_missing(af_ht[ht.key]))
        return ht

    def _get_gnomad_af_prefilter(self, frequencies=None, pathogenicity=None, **kwargs):
        gnomad_genomes_filter = (frequencies or {}).get(GNOMAD_GENOMES_FIELD, {})
        af_cutoff = gnomad_genomes_filter.get('af')
        if af_cutoff is None and gnomad_genomes_filter.get('ac') is not None:
            af_cutoff = PREFILTER_FREQ_CUTOFF
        if af_cutoff is None:
            return False

        if self._get_clinvar_path_filters(pathogenicity):
            af_cutoff = max(af_cutoff, PATH_FREQ_OVERRIDE_CUTOFF)

        return 'is_gt_10_percent' if af_cutoff > PREFILTER_FREQ_CUTOFF else True

    def _get_consequence_filter(self, allowed_consequence_ids, annotation_exprs):
        allowed_transcripts = self._ht.sorted_transcript_consequences.filter(
            lambda tc: tc.consequence_term_ids.any(allowed_consequence_ids.contains)
        )
        annotation_exprs['allowed_transcripts'] = allowed_transcripts
        return hl.is_defined(allowed_transcripts.first())

    def _get_annotation_override_filters(self, annotations, pathogenicity=None):
        annotation_filters = []

        for key in self.PATHOGENICITY_FILTERS.keys():
            path_terms = (pathogenicity or {}).get(key)
            if path_terms:
                annotation_filters.append(self._has_path_expr(path_terms, key))
        if annotations.get(SCREEN_KEY):
            allowed_consequences = hl.set(self._get_enum_terms_ids(SCREEN_KEY.lower(), 'region_type', annotations[SCREEN_KEY]))
            annotation_filters.append(allowed_consequences.contains(self._ht.screen.region_type_ids.first()))
        if annotations.get(SPLICE_AI_FIELD):
            score_filter, _ = self._get_in_silico_filter(SPLICE_AI_FIELD, annotations[SPLICE_AI_FIELD])
            annotation_filters.append(score_filter)

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

    def _format_results(self, ht, annotation_fields):
        ht = ht.annotate(selected_transcript=self._selected_main_transcript_expr(ht))
        return super()._format_results(ht, annotation_fields)

    @classmethod
    def _omim_sort(cls, r, omim_gene_set):
        return [
            hl.if_else(omim_gene_set.contains(r.selected_transcript.gene_id), 0, 1),
        ] + super()._omim_sort(r, omim_gene_set)

    @classmethod
    def _gene_rank_sort(cls, r, gene_ranks):
        return [gene_ranks.get(r.selected_transcript.gene_id)] + super()._gene_rank_sort(r, gene_ranks)


class SvHailTableQuery(BaseHailTableQuery):

    DATA_TYPE = 'SV_WGS'

    GENOTYPE_FIELDS = {_to_camel_case(f): f for f in ['CN', 'GQ']}
    NESTED_GENOTYPE_FIELDS = {'concordance': ['new_call', 'prev_call', 'prev_num_alt']}
    GENOTYPE_QUERY_FIELDS = {'gq_sv': 'GQ', 'gq': None}

    TRANSCRIPTS_FIELD = 'sorted_gene_consequences'
    TRANSCRIPT_CONSEQUENCE_FIELD = 'major_consequence'
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['algorithms']
    BASE_ANNOTATION_FIELDS = {
        'bothsidesSupport': lambda r: r.bothsides_support,
        'chrom': lambda r: r.start_locus.contig.replace('^chr', ''),
        'endChrom': lambda r: hl.or_missing(r.start_locus.contig != r.end_locus.contig, r.end_locus.contig.replace('^chr', '')),
        'pos': lambda r: r.start_locus.position,
        'end': lambda r: r.end_locus.position,
        'rg37LocusEnd': lambda r: r.rg37_locus_end,
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)
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

    SORTS = {
        'protein_consequence': lambda r: [hl.min(r.sorted_gene_consequences.map(lambda g: g.major_consequence_id))],
        'size': lambda r: [hl.if_else(
            r.start_locus.contig == r.end_locus.contig, r.start_locus.position - r.end_locus.position, -50,
        )],
    }
    SORTS.update(BaseHailTableQuery.SORTS)

    def _parse_intervals(self, intervals, variant_ids, variant_keys=None, **kwargs):
        parsed_intervals, _ = super()._parse_intervals(intervals, variant_ids=None, **kwargs)
        return parsed_intervals, variant_keys

    def _filter_variant_ids(self, ht, variant_ids):
        variant_ids_set = hl.set(variant_ids)
        return ht.filter(variant_ids_set.contains(ht.variant_id))

    def _filter_annotated_table(self, parsed_intervals=None, exclude_intervals=False, **kwargs):
        if parsed_intervals:
            interval_filter = hl.array(parsed_intervals).any(lambda interval: hl.if_else(
                self._ht.start_locus.contig == self._ht.end_locus.contig,
                interval.overlaps(hl.interval(self._ht.start_locus, self._ht.end_locus)),
                interval.contains(self._ht.start_locus) | interval.contains(self._ht.end_locus),
            ))
            if exclude_intervals:
                interval_filter = ~interval_filter
            self._ht = self._ht.filter(interval_filter)

        return super()._filter_annotated_table(**kwargs)

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return x_interval.contains(ht.start_locus)

    def _get_family_passes_quality_filter(self, quality_filter, annotations=None, **kwargs):
        passes_quality = super()._get_family_passes_quality_filter(quality_filter)
        if not annotations.get(NEW_SV_FIELD):
            return passes_quality

        entries_has_new_call = lambda entries: entries.any(lambda x: x.concordance.new_call)
        if passes_quality is None:
            return entries_has_new_call

        return lambda entries: entries_has_new_call(entries) & passes_quality(entries)

    def _get_allowed_consequences_annotations(self, annotations, annotation_filters, is_secondary=False):
        if is_secondary:
            # SV search can specify secondary SV types, as well as secondary consequences
            annotation_filters = self._get_annotation_override_filters(annotations)
        return super()._get_allowed_consequences_annotations(annotations, annotation_filters)

    def _get_consequence_filter(self, allowed_consequence_ids, annotation_exprs):
        return self._ht.sorted_gene_consequences.any(
            lambda gc: allowed_consequence_ids.contains(gc.major_consequence_id)
        )

    def _get_annotation_override_filters(self, annotations, **kwargs):
        annotation_filters = []
        if annotations.get(STRUCTURAL_ANNOTATION_FIELD):
            allowed_type_ids = self._get_enum_terms_ids('sv_type', None, annotations[STRUCTURAL_ANNOTATION_FIELD])
            if allowed_type_ids:
                annotation_filters.append(hl.set(allowed_type_ids).contains(self._ht.sv_type_id))

        return annotation_filters

    def _additional_annotation_fields(self):
        sv_type_enum = self._enums['sv_type']
        insertion_type_id = sv_type_enum.index('INS')
        get_end_chrom = self.BASE_ANNOTATION_FIELDS['endChrom']
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


QUERY_CLASS_MAP = {cls.DATA_TYPE: cls for cls in [VariantHailTableQuery, SvHailTableQuery]}
