from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPInternalServerError
from collections import defaultdict, namedtuple
import hail as hl
import logging
import os

from hail_search.constants import AFFECTED_ID, ALT_ALT, ANNOTATION_OVERRIDE_FIELDS, ANY_AFFECTED, COMP_HET_ALT, \
    COMPOUND_HET, GENOME_VERSION_GRCh38, GROUPED_VARIANTS_FIELD, ALLOWED_TRANSCRIPTS, ALLOWED_SECONDARY_TRANSCRIPTS,  HAS_ANNOTATION_OVERRIDE, \
    HAS_ALT, HAS_REF,INHERITANCE_FILTERS, PATH_FREQ_OVERRIDE_CUTOFF, RECESSIVE, REF_ALT, REF_REF, MAX_LOAD_INTERVALS, \
    UNAFFECTED_ID, X_LINKED_RECESSIVE, XPOS, OMIM_SORT, FAMILY_GUID_FIELD, GENOTYPES_FIELD, AFFECTED_ID_MAP

HAIL_SEARCH_DATA_DIR = os.environ.get('HAIL_SEARCH_DATA_DIR', '/seqr/seqr-hail-search-data')
IN_MEMORY_DIR = os.environ.get('IN_MEMORY_DIR', HAIL_SEARCH_DATA_DIR)

# Number of filtered genes at which pre-filtering a table by gene-intervals does not improve performance
# Estimated based on behavior for several representative gene lists
MAX_GENE_INTERVALS = int(os.environ.get('MAX_GENE_INTERVALS', MAX_LOAD_INTERVALS))

# Optimal number of entry table partitions, balancing parallelization with partition overhead
# Experimentally determined based on compound het search performance:
# https://github.com/broadinstitute/seqr-private/issues/1283#issuecomment-1973392719
MAX_PARTITIONS = 12

logger = logging.getLogger(__name__)


PredictionPath = namedtuple('PredictionPath', ['source', 'field', 'format'], defaults=[lambda x: x])
QualityFilterFormat = namedtuple('QualityFilterFormat', ['scale', 'override'], defaults=[None, None])


def _to_camel_case(snake_case_str):
    converted = snake_case_str.replace('_', ' ').title().replace(' ', '')
    return converted[0].lower() + converted[1:]


class BaseHailTableQuery(object):

    DATA_TYPE = None
    KEY_FIELD = None
    LOADED_GLOBALS = None

    GENOTYPE_QUERY_MAP = {
        REF_REF: lambda gt: gt.is_hom_ref(),
        REF_ALT: lambda gt: gt.is_het(),
        COMP_HET_ALT: lambda gt: gt.is_het(),
        ALT_ALT: lambda gt: gt.is_hom_var(),
        HAS_ALT: lambda gt: gt.is_non_ref(),
        HAS_REF: lambda gt: gt.is_hom_ref() | gt.is_het_ref(),
    }
    MISSING_NUM_ALT = -1

    GENOTYPE_FIELDS = {}
    COMPUTED_GENOTYPE_FIELDS = {}
    GENOTYPE_OVERRIDE_FIELDS = {}
    GENOTYPE_QUERY_FIELDS = {}
    QUALITY_FILTER_FORMAT = {}
    POPULATIONS = {}
    POPULATION_FIELDS = {}
    POPULATION_KEYS = ['AF', 'AC', 'AN', 'Hom', 'Hemi', 'Het']
    PREDICTION_FIELDS_CONFIG = {}
    ANNOTATION_OVERRIDE_FIELDS = []
    SECONDARY_ANNOTATION_OVERRIDE_FIELDS = None

    GENOME_VERSION = GENOME_VERSION_GRCh38
    GLOBALS = ['enums']
    TRANSCRIPTS_FIELD = None
    CORE_FIELDS = [XPOS]
    BASE_ANNOTATION_FIELDS = {
        FAMILY_GUID_FIELD: lambda r: hl.set(
            r.family_entries.filter(hl.is_defined).map(lambda entries: entries.first().familyGuid)),
        'variantId': lambda r: r.variant_id,
    }
    ENUM_ANNOTATION_FIELDS = {
        'transcripts': {
            'response_key': 'transcripts',
            'empty_array': True,
            'format_array_values': lambda values, *args: values.group_by(lambda t: t.geneId),
        },
    }
    LIFTOVER_ANNOTATION_FIELDS = {
        'liftedOverGenomeVersion': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), '37'),
        'liftedOverChrom': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), r.rg37_locus.contig),
        'liftedOverPos': lambda r: hl.or_missing(hl.is_defined(r.rg37_locus), r.rg37_locus.position),
    }

    SORTS = {
        XPOS: lambda r: [r.xpos],
        'family_guid': lambda r: [
            hl.int(r.family_entries.find(hl.is_defined).first().familyGuid.first_match_in('(\d+)').first())
        ],
    }

    @classmethod
    def load_globals(cls):
        ht_path = cls._get_table_path('annotations.ht')
        try:
            ht = hl.read_table(ht_path)
        except Exception:
            return None

        ht_globals = hl.eval(ht.globals.select(*cls.GLOBALS))
        cls.LOADED_GLOBALS = {k: ht_globals[k] for k in cls.GLOBALS}
        return cls.LOADED_GLOBALS

    @classmethod
    def _format_population_config(cls, pop_config):
        base_pop_config = {field.lower(): field for field in cls.POPULATION_KEYS}
        base_pop_config.update(pop_config)
        base_pop_config.pop('sort', None)
        return base_pop_config

    def annotation_fields(self, include_genotype_overrides=True):
        annotation_fields = {
            GENOTYPES_FIELD: lambda r: r.family_entries.flatmap(lambda x: x).filter(
                lambda gt: hl.is_defined(gt.individualGuid)
            ).group_by(lambda x: x.individualGuid).map_values(lambda x: self._get_sample_genotype(
                x, r, select_fields=['individualGuid'], include_genotype_overrides=include_genotype_overrides,
            )),
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population) for population in self.POPULATIONS.keys()
            }),
            'predictions': lambda r: hl.struct(**{
                prediction: self._format_enum(r[path.source], path.field, self._enums[path.source][path.field])
                if self._enums.get(path.source, {}).get(path.field) else path.format(r[path.source][path.field])
                for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)
        annotation_fields.update(self.LIFTOVER_ANNOTATION_FIELDS)
        annotation_fields.update(self._additional_annotation_fields())

        prediction_fields = {path.source for path in self.PREDICTION_FIELDS_CONFIG.values()}
        annotation_fields.update([
            self._format_enum_response(k, enum) for k, enum in self._enums.items()
            if enum and k not in prediction_fields
        ])

        return annotation_fields

    def _get_sample_genotype(self, samples, r=None, include_genotype_overrides=False, select_fields=None, **kwargs):
        sample = samples[0]
        return self._select_genotype_for_sample(sample, r, include_genotype_overrides, select_fields)

    def _select_genotype_for_sample(self, sample, r, include_genotype_overrides, select_fields):
        return sample.select(
            'sampleId', 'sampleType', 'familyGuid', 'filters', *(select_fields or []),
            numAlt=hl.if_else(hl.is_defined(sample.GT), sample.GT.n_alt_alleles(), self.MISSING_NUM_ALT),
            **{k: sample[field] for k, field in self.GENOTYPE_FIELDS.items()},
            **{_to_camel_case(k): v(sample, k, r) for k, v in self.COMPUTED_GENOTYPE_FIELDS.items()
               if include_genotype_overrides or k not in self.GENOTYPE_OVERRIDE_FIELDS},
        )

    def _additional_annotation_fields(self):
        return {}

    def population_expression(self, r, population):
        pop_config = self._format_population_config(self.POPULATIONS[population])
        pop_field = self.POPULATION_FIELDS.get(population, population)
        return hl.struct(**{
            response_key: hl.or_else(r[pop_field][field], '' if response_key == 'id' else 0)
            for response_key, field in pop_config.items() if field is not None
        })

    def _get_enum_lookup(self, field, subfield, nested_subfield=None):
        enum_field = self._enums.get(field, {})
        if subfield:
            enum_field = enum_field.get(subfield)
        if nested_subfield:
            enum_field = enum_field.get(nested_subfield)
        if enum_field is None:
            return None
        return {v: i for i, v in enumerate(enum_field)}

    def _get_enum_terms_ids(self, field, subfield, terms, nested_subfield=None):
        if not terms:
            return set()
        enum = self._get_enum_lookup(field, subfield, nested_subfield=nested_subfield)
        return {enum[t] for t in terms if enum.get(t) is not None}

    def _format_enum_response(self, k, enum):
        enum_config = self.ENUM_ANNOTATION_FIELDS.get(k, {})
        value = lambda r: self._format_enum(r, k, enum, ht_globals=self._globals, **enum_config)
        return enum_config.get('response_key', _to_camel_case(k)), value

    @staticmethod
    def _camelcase_value(value):
        return value.rename({k: _to_camel_case(k) for k in value.keys()})

    @classmethod
    def _format_enum(cls, r, field, enum, empty_array=False, format_array_values=None, **kwargs):
        if hasattr(r, f'{field}_id'):
            return hl.array(enum)[r[f'{field}_id']]

        value = r[field]
        if hasattr(value, 'map'):
            if empty_array:
                value = hl.or_else(value, hl.empty_array(value.dtype.element_type))
            value = value.map(lambda x: cls._enum_field(field, x, enum, **kwargs, format_value=cls._camelcase_value))
            if format_array_values:
                value = format_array_values(value, r)
            return value

        return cls._enum_field(field, value, enum, **kwargs)

    @classmethod
    def _enum_field(cls, field_name, value, enum, ht_globals=None, annotate_value=None, format_value=None, drop_fields=None, enum_keys=None, include_version=False, **kwargs):
        annotations = {}
        drop = [] + (drop_fields or [])
        value_keys = value.keys()
        for field in (enum_keys or enum.keys()):
            field_enum = enum[field]
            is_nested_struct = field in value_keys
            is_array = f'{field}_ids' in value_keys

            if is_nested_struct:
                annotations[field] = cls._enum_field(field, value[field], field_enum, format_value=format_value)
            else:
                value_field = f"{field}_id{'s' if is_array else ''}"
                drop.append(value_field)
                enum_array = hl.array(field_enum)
                if is_array:
                    annotations[f'{field}s'] = value[value_field].map(lambda v: enum_array[v])
                else:
                    annotations[field] = enum_array[value[value_field]]

        if include_version:
            annotations['version'] = ht_globals['versions'][field_name]

        value = value.annotate(**annotations)
        if annotate_value:
            annotations = annotate_value(value, enum)
            value = value.annotate(**annotations)
        value = value.drop(*drop)

        if format_value:
            value = format_value(value)

        return value

    def __init__(self, sample_data, sort=XPOS, sort_metadata=None, num_results=100, inheritance_mode=None,
                 override_comp_het_alt=False, **kwargs):
        if not self.LOADED_GLOBALS:
            raise HTTPInternalServerError(reason=f'No loaded {self.DATA_TYPE} data found')

        self.unfiltered_comp_het_ht = None
        self._sort = sort
        self._sort_metadata = sort_metadata
        self._num_results = num_results
        self._override_comp_het_alt = override_comp_het_alt
        self._ht = None
        self._comp_het_ht = None
        self._inheritance_mode = inheritance_mode
        self._has_secondary_annotations = False
        self._is_multi_data_type_comp_het = False
        self.max_unaffected_samples = None
        self._n_partitions = min(MAX_PARTITIONS, (os.cpu_count() or 2)-1)
        self._load_table_kwargs = {'_n_partitions': self._n_partitions}
        self.entry_samples_by_family_guid = {}

        if sample_data:
            self._load_filtered_table(sample_data, **kwargs)

    @property
    def _has_comp_het_search(self):
        return self._inheritance_mode in {RECESSIVE, COMPOUND_HET}

    @property
    def _globals(self):
        return self.LOADED_GLOBALS

    @property
    def _enums(self):
        return self._globals['enums']

    def _load_filtered_table(self, sample_data, intervals=None, annotations=None, annotations_secondary=None, **kwargs):
        parsed_intervals = self._parse_intervals(intervals, **kwargs)
        parsed_annotations = self._parse_annotations(annotations, annotations_secondary, **kwargs)
        self.import_filtered_table(
            *self._parse_sample_data(sample_data), parsed_intervals=parsed_intervals, raw_intervals=intervals, parsed_annotations=parsed_annotations, **kwargs)

    @classmethod
    def _get_table_path(cls, path):
        return f'{cls._get_table_dir(path)}/{cls.GENOME_VERSION}/{cls.DATA_TYPE}/{path}'

    @classmethod
    def _get_table_dir(cls, path):
        return IN_MEMORY_DIR if path == 'annotations.ht' else HAIL_SEARCH_DATA_DIR

    def _read_table(self, path, drop_globals=None, skip_missing_field=None):
        table_path = self._get_table_path(path)
        if 'variant_ht' in self._load_table_kwargs:
            ht = self._query_table_annotations(self._load_table_kwargs['variant_ht'], table_path)
            if skip_missing_field and not ht.any(hl.is_defined(ht[skip_missing_field])):
                return None
            ht_globals = hl.read_table(table_path).index_globals()
            if drop_globals:
                ht_globals = ht_globals.drop(*drop_globals)
            return ht.annotate_globals(**ht_globals)
        return hl.read_table(table_path, **self._load_table_kwargs)

    @staticmethod
    def _query_table_annotations(ht, query_table_path):
        query_result = hl.query_table(query_table_path, ht.key).first().drop(*ht.key)
        return ht.annotate(**query_result)

    def _parse_sample_data(self, sample_data):
        """
        Organizes sample_data by project, sample type, and family in a nested dictionary format.
        Returns a tuple containing:
        - project_samples (defaultdict): {<project_guid>: {<sample_type>: {<family_guid>: [<sample_data>, ...]}}}
        - num_families (int): The number of unique families in the sample data.
        """
        families = set()
        project_samples = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for s in sample_data:
            families.add(s['family_guid'])
            project_samples[s['project_guid']][s['sample_type']][s['family_guid']].append(s)

        num_families = len(families)
        logger.info(f'Loading {self.DATA_TYPE} data for {num_families} families in {len(project_samples)} projects')
        return project_samples, num_families

    def _import_and_filter_multiple_project_hts(
        self, project_samples: dict, n_partitions=MAX_PARTITIONS, **kwargs
    ) -> tuple[hl.Table, hl.Table]:
        """
        In the variant lookup control flow, project_samples looks like this:
            {<project_guid>: {<sample_type>: {<family_guid>: True}, <sample_type_2>: {<family_guid_2>: True}}, <project_guid_2>: ...}
        In the variant search control flow, project_samples looks like this:
            {<project_guid>: {<sample_type>: {<family_guid>: [<sample_data>, <sample_data>, ...]}, <sample_type_2>: {<family_guid_2>: []} ...}, <project_guid_2>: ...}
        """
        entries_hts = self._load_project_hts(project_samples, n_partitions, **kwargs)
        filtered_project_hts = []
        filtered_comp_het_project_hts = []
        for ht, project_families in entries_hts:
            ht, comp_het_ht = self._filter_single_entries_table(ht, project_families, is_merged_ht=True, **kwargs)
            if ht is not None:
                filtered_project_hts.append(ht)
            if comp_het_ht is not None:
                filtered_comp_het_project_hts.append(comp_het_ht)

        return self._merge_filtered_hts(filtered_comp_het_project_hts, filtered_project_hts, n_partitions)

    def _load_project_hts(self, project_samples, n_partitions, **kwargs):
        # Need to chunk tables or else evaluating table globals throws LineTooLong exception
        # However, minimizing number of chunks minimizes number of aggregations/ evals and improves performance
        # Adapted from https://discuss.hail.is/t/importing-many-sample-specific-vcfs/2002/8
        chunk_size = 64
        all_project_hts = []
        project_hts = []
        sample_data = {}

        for project_guid, project_sample_type_data in project_samples.items():
            for sample_type, family_sample_data in project_sample_type_data.items():
                project_ht = self._read_project_data(project_guid, sample_type)
                if project_ht is None:
                    continue
                project_hts.append(project_ht)
                sample_data.update(family_sample_data)

            if len(project_hts) >= chunk_size:
                ht = self._prefilter_merged_project_hts(project_hts, n_partitions, **kwargs)
                all_project_hts.append((ht, sample_data))
                project_hts = []
                sample_data = {}

        if project_hts:
            ht = self._prefilter_merged_project_hts(project_hts, n_partitions, **kwargs)
            all_project_hts.append((ht, sample_data))
        return all_project_hts

    def import_filtered_table(self, project_samples: dict, num_families: int, **kwargs):
        if num_families == 1 or len(project_samples) == 1:
            project_guid, project_sample_type_data = list(project_samples.items())[0]
            families_ht, comp_het_families_ht = self._import_and_filter_entries_ht(
                project_guid, num_families, project_sample_type_data, **kwargs
            )
        else:
            families_ht, comp_het_families_ht = self._import_and_filter_multiple_project_hts(project_samples, **kwargs)

        if comp_het_families_ht is not None:
            self._comp_het_ht = self._query_table_annotations(comp_het_families_ht, self._get_table_path('annotations.ht'))
            self._comp_het_ht = self._filter_annotated_table(self._comp_het_ht, is_comp_het=True, **kwargs)
            self._comp_het_ht = self._filter_compound_hets()

        if families_ht is not None:
            self._ht = self._query_table_annotations(families_ht, self._get_table_path('annotations.ht'))
            self._ht = self._filter_annotated_table(self._ht, **kwargs)

    def _import_and_filter_entries_ht(
        self, project_guid: str, num_families: int, project_sample_type_data, **kwargs
    ) -> tuple[hl.Table, hl.Table]:
        sample_type = list(project_sample_type_data.keys())[0]
        ht, sample_data = self._load_family_or_project_ht(
            num_families, project_guid, project_sample_type_data, sample_type, **kwargs
        )
        return self._filter_single_entries_table(ht, sample_data, **kwargs)

    def _load_family_or_project_ht(self, num_families, project_guid, project_sample_type_data, sample_type, **kwargs):
        if num_families == 1:
            family_guid = list(project_sample_type_data[sample_type].keys())[0]
            ht, sample_data = self._load_family_ht(family_guid, sample_type, project_sample_type_data, **kwargs)
        else:
            ht, sample_data = self._load_project_ht(project_guid, sample_type, project_sample_type_data, **kwargs)
        return ht, sample_data

    def _load_family_ht(
        self, family_guid: str, sample_type: str, project_sample_type_data: dict, **kwargs
    ) -> tuple[hl.Table, dict]:
        ht = self._read_table(f'families/{sample_type}/{family_guid}.ht')
        ht = ht.transmute(family_entries=[ht.entries])
        ht = ht.annotate_globals(family_guids=[family_guid], family_samples={family_guid: ht.sample_ids})
        ht = self._prefilter_entries_table(ht, **kwargs)
        sample_data = project_sample_type_data[sample_type]
        return ht, sample_data

    def _load_project_ht(
        self, project_guid: str, sample_type: str, project_sample_type_data: dict, **kwargs
    ) -> tuple[hl.Table, dict]:
        ht = self._read_project_table(project_guid, sample_type)
        ht = self._prefilter_entries_table(ht, **kwargs)
        sample_data = project_sample_type_data[sample_type]
        return ht, sample_data

    def _read_project_table(self, project_guid: str, sample_type: str):
        return self._read_table(f'projects/{sample_type}/{project_guid}.ht')

    def _read_project_data(self, project_guid: str, sample_type: str):
        project_ht = self._read_project_table(project_guid, sample_type)
        if project_ht is not None:
            project_ht = project_ht.select_globals('sample_type', 'family_guids', 'family_samples')
        return project_ht

    def _prefilter_merged_project_hts(self, project_hts, n_partitions, **kwargs):
        ht = self._merge_project_hts(project_hts, n_partitions, include_all_globals=True)
        return self._prefilter_entries_table(ht, **kwargs)

    @classmethod
    def _merge_project_hts(cls, project_hts, n_partitions, include_all_globals=False):
        if not project_hts:
            return None
        ht = hl.Table.multi_way_zip_join(project_hts, 'project_entries', 'project_globals')
        ht = ht.repartition(n_partitions)
        project_entries = ht.project_entries
        if include_all_globals:
            project_entries = project_entries.map(cls._annotate_entry_filters)
        ht = ht.transmute(
            family_entries=hl.enumerate(project_entries).starmap(lambda i, x: hl.or_else(
                x.family_entries,
                ht.project_globals[i].family_guids.map(lambda f: hl.missing(x.family_entries.dtype.element_type)),
            )).flatmap(lambda x: x),
        )
        global_expressions = {
            'family_guids': ht.project_globals.flatmap(lambda x: x.family_guids),
        }
        if include_all_globals:
            global_expressions.update({
                'sample_types': ht.project_globals.flatmap(lambda x: x.family_guids.map(lambda _: x.sample_type)),
                'family_samples': hl.dict(ht.project_globals.flatmap(lambda x: x.family_samples.items())),
            })

        return ht.transmute_globals(**global_expressions)

    def _merge_filtered_hts(self, filtered_comp_het_project_hts, filtered_project_hts, n_partitions):
        ht = self._merge_project_hts(filtered_project_hts, n_partitions)
        comp_het_ht = self._merge_project_hts(filtered_comp_het_project_hts, n_partitions)
        return ht, comp_het_ht

    @staticmethod
    def _apply_entry_filters(ht):
        if ht is not None:
            ht = ht.filter(ht.family_entries.any(hl.is_defined)).select_globals('family_guids')
        return ht

    def _filter_single_entries_table(self, ht, project_families, inheritance_filter=None, quality_filter=None, is_merged_ht=False, **kwargs):
        ht, sorted_family_sample_data = self._add_entry_sample_families(ht, project_families, is_merged_ht)
        ht = self._filter_quality(ht, quality_filter, **kwargs)
        ht, ch_ht = self._filter_inheritance(ht, None, inheritance_filter, sorted_family_sample_data)
        ht = self._apply_entry_filters(ht)
        ch_ht = self._apply_entry_filters(ch_ht)

        return ht, ch_ht

    def _filter_quality(
        self, ht, quality_filter, annotation='family_entries', entries_ht_field='family_entries', **kwargs
    ):
        passes_quality_filter = self._get_family_passes_quality_filter(
            quality_filter, ht, **kwargs
        )
        ht_entries = ht[entries_ht_field]

        if passes_quality_filter is not None:
            return ht.annotate(**{
                annotation: ht_entries.map(
                    lambda entries: hl.or_missing(passes_quality_filter(entries), entries)
                )})

        return ht.annotate(**{annotation: ht_entries})

    def _add_entry_sample_families(self, ht, sample_data, is_merged_ht):
        """
        Annotates samples in family_entries with additional sample-level data.
        returns a tuple containing:
        - ht (hl.Table)
        - sorted_family_sample_data (list): A list of lists containing sample data for each family,
            sorted in the same order as is in family_entries. [[<sample_1>, <sample_2>]]
        """
        ht_globals = hl.eval(ht.globals)

        missing_samples = set()
        family_sample_index_data = []
        sorted_family_sample_data = []
        family_guids = sorted(sample_data.keys())
        for family_guid in family_guids:
            ht_family_samples = ht_globals.family_samples[family_guid]
            samples = sample_data[family_guid]
            if samples is True:
                samples = ht_family_samples
                get_sample_data = lambda s: {'sampleId': s}
                missing_family_samples = []
            else:
                get_sample_data = self._sample_entry_data
                missing_family_samples = [s['sample_id'] for s in samples if s['sample_id'] not in ht_family_samples]
            if missing_family_samples:
                missing_samples.update(missing_family_samples)
            else:
                family_index = ht_globals.family_guids.index(family_guid)
                family_entry_data = {
                    'sampleType': self._get_sample_type(family_index, ht_globals),
                    'familyGuid': family_guid,
                }
                formatted_samples = [{**family_entry_data, **get_sample_data(s)} for s in samples]
                sample_index_data = [(ht_family_samples.index(s['sampleId']), hl.struct(**s)) for s in formatted_samples]
                family_sample_index_data.append((family_index, sample_index_data))
                sorted_family_sample_data.append(formatted_samples)
                self.entry_samples_by_family_guid[family_guid] = [s['sampleId'] for s in formatted_samples]

        if missing_samples:
            raise HTTPBadRequest(
                reason=f'The following samples are available in seqr but missing the loaded data: {", ".join(sorted(missing_samples))}'
            )

        family_sample_index_data = hl.array(family_sample_index_data)

        ht = ht.annotate_globals(family_guids=family_guids)

        ht = ht.transmute(family_entries=family_sample_index_data.map(lambda family_tuple: family_tuple[1].map(
            lambda sample_tuple: ht.family_entries[family_tuple[0]][sample_tuple[0]].annotate(**sample_tuple[1])
        )))
        if not is_merged_ht:
            ht = self._annotate_entry_filters(ht)

        return ht, sorted_family_sample_data

    @staticmethod
    def _annotate_entry_filters(ht):
        return ht.annotate(family_entries=ht.family_entries.map(
            lambda entries: entries.map(lambda x: x.annotate(filters=ht.filters))
        ))

    @classmethod
    def _sample_entry_data(cls, sample):
        return dict(
            sampleId=sample['sample_id'],
            individualGuid=sample['individual_guid'],
            affected_id=AFFECTED_ID_MAP.get(sample['affected']),
            is_male=sample.get('is_male', False),
        )

    @classmethod
    def _get_sample_type(cls, family_index, ht_globals):
        if 'sample_types' in ht_globals:
            return ht_globals.sample_types[family_index]
        return ht_globals.sample_type

    def _filter_inheritance(
        self, ht, comp_het_ht, inheritance_filter, sorted_family_sample_data,
        annotation='family_entries', entries_ht_field='family_entries', **kwargs
    ):
        any_valid_entry = lambda x: self.GENOTYPE_QUERY_MAP[HAS_ALT](x.GT)

        is_any_affected = self._inheritance_mode == ANY_AFFECTED
        if is_any_affected:
            prev_any_valid_entry = any_valid_entry
            any_valid_entry = lambda x: prev_any_valid_entry(x) & (x.affected_id == AFFECTED_ID)

        ht = ht.annotate(**{
            entries_ht_field: ht[entries_ht_field].map(
                lambda entries: hl.or_missing(entries.any(any_valid_entry), entries)
            )})

        if self._has_comp_het_search:
            comp_het_ht = self._annotate_families_inheritance(
                comp_het_ht if comp_het_ht is not None else ht, COMPOUND_HET, inheritance_filter,
                sorted_family_sample_data, annotation, entries_ht_field, **kwargs
            )

        if is_any_affected or not (inheritance_filter or self._inheritance_mode):
            # No sample-specific inheritance filtering needed
            sorted_family_sample_data = []

        ht = None if self._inheritance_mode == COMPOUND_HET else self._annotate_families_inheritance(
            ht, self._inheritance_mode, inheritance_filter, sorted_family_sample_data,
            annotation, entries_ht_field, **kwargs
        )

        return ht, comp_het_ht

    def _annotate_families_inheritance(
        self, ht, inheritance_mode, inheritance_filter, sorted_family_sample_data,
        annotation, entries_ht_field, family_passes_inheritance_filter = None
    ):
        if not family_passes_inheritance_filter:
            family_passes_inheritance_filter = self._get_family_passes_inheritance_filter

        entry_indices_by_gt = self._get_entry_indices_by_gt_map(
            inheritance_filter, inheritance_mode, sorted_family_sample_data
        )

        for genotype, entry_indices in entry_indices_by_gt.items():
            if not entry_indices:
                continue
            entry_indices = hl.dict(entry_indices)
            ht = ht.annotate(**{
                annotation: hl.enumerate(ht[entries_ht_field]).starmap(
                    lambda family_idx, family_samples: family_passes_inheritance_filter(
                        entry_indices, family_idx, genotype, family_samples, ht, annotation
                    )
                )
            })

        return ht

    def _get_family_passes_inheritance_filter(self, entry_indices, family_idx, genotype, family_samples, *args):
        return hl.or_missing(
            ~entry_indices.contains(family_idx) | entry_indices[family_idx].all(
                lambda sample_i: self.GENOTYPE_QUERY_MAP[genotype](family_samples[sample_i].GT)
        ), family_samples)

    def _get_entry_indices_by_gt_map(self, inheritance_filter, inheritance_mode, sorted_family_sample_data):
        individual_genotype_filter = (inheritance_filter or {}).get('genotype')

        # Create a mapping of genotypes to check against a list of samples for a family
        entry_indices_by_gt = defaultdict(lambda: defaultdict(list))
        for family_index, samples in enumerate(sorted_family_sample_data):
            for sample_index, s in enumerate(samples):
                genotype = individual_genotype_filter.get(s['individualGuid']) \
                    if individual_genotype_filter else INHERITANCE_FILTERS[inheritance_mode].get(s['affected_id'])
                if inheritance_mode == X_LINKED_RECESSIVE and s['affected_id'] == UNAFFECTED_ID and s['is_male']:
                    genotype = REF_REF
                if genotype == COMP_HET_ALT and self._override_comp_het_alt:
                    genotype = HAS_ALT
                if genotype:
                    entry_indices_by_gt[genotype][family_index].append(sample_index)

        if inheritance_mode == COMPOUND_HET:
            family_unaffected_counts = [
                len(i) for i in entry_indices_by_gt[INHERITANCE_FILTERS[COMPOUND_HET][UNAFFECTED_ID]].values()
            ]
            self.max_unaffected_samples = max(family_unaffected_counts) if family_unaffected_counts else 0

        return entry_indices_by_gt

    def _get_family_passes_quality_filter(self, quality_filter, ht, **kwargs):
        quality_filter = quality_filter or {}

        affected_only = quality_filter.get('affected_only')
        passes_quality_filters = []
        for filter_k, value in quality_filter.items():
            genotype_key = filter_k.replace('min_', '')
            field = self.GENOTYPE_QUERY_FIELDS.get(genotype_key, self.GENOTYPE_FIELDS.get(genotype_key))
            if field and value:
                passes_quality_filters.append(self._get_genotype_passes_quality_field(field, value, affected_only))

        if quality_filter.get('vcf_filter'):
            passes_quality_filters.append(self._passes_vcf_filters)

        if not passes_quality_filters:
            return None

        return lambda entries: entries.all(lambda gt: hl.all([f(gt) for f in passes_quality_filters]))

    @classmethod
    def _get_genotype_passes_quality_field(cls, field, value, affected_only, **kwargs):
        field_config = cls.QUALITY_FILTER_FORMAT.get(field) or QualityFilterFormat()
        if field_config.scale:
            value = value / field_config.scale

        def passes_quality_field(gt):
            is_valid = (gt[field] >= value) | hl.is_missing(gt[field])
            if field_config.override:
                is_valid |= field_config.override(gt)
            if affected_only:
                is_valid |= gt.affected_id != AFFECTED_ID
            return is_valid

        return passes_quality_field

    @staticmethod
    def _passes_vcf_filters(gt):
        return hl.is_missing(gt.filters) | (gt.filters.length() < 1)

    def _parse_variant_keys(self, variant_keys):
        return [hl.struct(**{self.KEY_FIELD[0]: key}) for key in (variant_keys or [])]

    def _prefilter_entries_table(self, ht, **kwargs):
        return ht

    def _filter_annotated_table(self, ht, gene_ids=None, rs_ids=None, frequencies=None, in_silico=None, pathogenicity=None,
                                parsed_annotations=None, is_comp_het=False, **kwargs):
        if gene_ids:
            ht = self._filter_by_gene_ids(ht, gene_ids)

        if rs_ids:
            ht = self._filter_rs_ids(ht, rs_ids)

        ht = self._filter_by_frequency(ht, frequencies, pathogenicity)

        ht = self._filter_by_in_silico(ht, in_silico)

        return self._filter_by_annotations(ht, is_comp_het=is_comp_het, **(parsed_annotations or {}))

    def _filter_by_gene_ids(self, ht, gene_ids):
        gene_ids = hl.set(gene_ids)
        ht = ht.annotate(
            gene_transcripts=ht[self.TRANSCRIPTS_FIELD].filter(lambda t: gene_ids.contains(t.gene_id))
        )
        return ht.filter(hl.is_defined(ht.gene_transcripts.first()))

    def _filter_rs_ids(self, ht, rs_ids):
        rs_id_set = hl.set(rs_ids)
        return ht.filter(rs_id_set.contains(ht.rsid))

    def _parse_intervals(self, intervals, gene_ids=None, variant_keys=None, variant_ids=None, **kwargs):
        parsed_variant_keys = self._parse_variant_keys(variant_keys)
        if parsed_variant_keys:
            self._load_table_kwargs['variant_ht'] = hl.Table.parallelize(parsed_variant_keys).key_by(*self.KEY_FIELD)
            return intervals

        if variant_ids:
            first_chrom = variant_ids[0][0]
            if all(first_chrom == v[0] for v in variant_ids):
                positions = [pos for _, pos, _, _ in variant_ids]
                intervals = [(first_chrom, min(positions), max(positions) + 1)]
            else:
                intervals = [(chrom, pos, pos+1) for chrom, pos, _, _ in variant_ids]

        is_x_linked = self._inheritance_mode == X_LINKED_RECESSIVE
        if not (intervals or is_x_linked):
            return intervals

        raw_intervals = intervals
        if self._should_add_chr_prefix():
            intervals = [[f'chr{interval[0]}', *interval[1:]] for interval in (intervals or [])]

        if len(intervals) > MAX_GENE_INTERVALS and len(intervals) == len(gene_ids or []):
            intervals = self.cluster_intervals(sorted(intervals))

        parsed_intervals = [
            hl.eval(hl.locus_interval(*interval, reference_genome=self.GENOME_VERSION, invalid_missing=True))
            for interval in (intervals or [])
        ]
        invalid_intervals = [raw_intervals[i] for i, interval in enumerate(parsed_intervals) if interval is None]
        if invalid_intervals:
            error_interval = ', '.join([f'{chrom}:{start}-{end}' for chrom, start, end in invalid_intervals])
            raise HTTPBadRequest(reason=f'Invalid intervals: {error_interval}')

        if is_x_linked:
            reference_genome = hl.get_reference(self.GENOME_VERSION)
            parsed_intervals.append(
                hl.eval(hl.parse_locus_interval(reference_genome.x_contigs[0], reference_genome=self.GENOME_VERSION))
            )

        return parsed_intervals

    @classmethod
    def cluster_intervals(cls, intervals, distance=100000, max_intervals=MAX_GENE_INTERVALS):
        if len(intervals) <= max_intervals:
            return intervals

        merged_intervals = [intervals[0]]
        for chrom, start, end in intervals[1:]:
            prev_chrom, prev_start, prev_end = merged_intervals[-1]
            if chrom == prev_chrom and start - prev_end < distance:
                merged_intervals[-1] = [chrom, prev_start, max(prev_end, end)]
            else:
                merged_intervals.append([chrom, start, end])

        return cls.cluster_intervals(merged_intervals, distance=distance+100000, max_intervals=max_intervals)

    def _should_add_chr_prefix(self):
        return self.GENOME_VERSION == GENOME_VERSION_GRCh38

    def _filter_by_frequency(self, ht, frequencies, pathogenicity):
        frequencies = {k: v for k, v in (frequencies or {}).items() if k in self.POPULATIONS}
        if not frequencies:
            return ht

        path_override_filter = self._frequency_override_filter(ht, pathogenicity)
        filters = []
        for pop, freqs in sorted(frequencies.items()):
            pop_filters = []
            pop_expr = ht[self.POPULATION_FIELDS.get(pop, pop)]
            pop_config = self._format_population_config(self.POPULATIONS[pop])
            if freqs.get('af') is not None and freqs['af'] < 1:
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
            ht = ht.filter(hl.all(filters))
        return ht

    def _frequency_override_filter(self, ht, pathogenicity):
        return None

    def _filter_by_in_silico(self, ht, in_silico_filters):
        in_silico_filters = in_silico_filters or {}
        require_score = in_silico_filters.get('requireScore', False)
        in_silico_filters = {k: v for k, v in in_silico_filters.items() if k in self.PREDICTION_FIELDS_CONFIG and v}
        if not in_silico_filters:
            return ht

        in_silico_qs = []
        missing_qs = []
        for in_silico, value in in_silico_filters.items():
            score_filter, ht_value = self._get_in_silico_filter(ht, in_silico, value)
            in_silico_qs.append(score_filter)
            if not require_score:
                missing_qs.append(hl.is_missing(ht_value))

        if missing_qs:
            in_silico_qs.append(hl.all(missing_qs))

        return ht.filter(hl.any(in_silico_qs))

    def _get_in_silico_filter(self, ht, in_silico, value):
        score_path = self.PREDICTION_FIELDS_CONFIG[in_silico]
        enum_lookup = self._get_enum_lookup(*score_path[:2])
        if enum_lookup is not None:
            ht_value = ht[score_path.source][f'{score_path.field}_id']
            score_filter = ht_value == enum_lookup[value]
        else:
            ht_value = ht[score_path.source][score_path.field]
            score_filter = ht_value >= float(value)

        return score_filter, ht_value

    def _parse_annotations(self, annotations, annotations_secondary, **kwargs):
        annotations = annotations or {}
        allowed_consequence_ids = self._get_allowed_consequence_ids(annotations)
        annotation_overrides = self._get_annotation_override_fields(annotations, **kwargs)

        parsed_annotations = {}
        if self._has_comp_het_search and annotations_secondary:
            secondary_allowed_consequence_ids = self._get_allowed_consequence_ids(annotations_secondary)
            has_different_secondary = secondary_allowed_consequence_ids != allowed_consequence_ids
            has_data_type_primary_annotations = allowed_consequence_ids or annotation_overrides
            has_data_type_secondary_annotations = bool(secondary_allowed_consequence_ids)
            secondary_annotation_overrides = None
            if self.SECONDARY_ANNOTATION_OVERRIDE_FIELDS:
                secondary_annotation_overrides = self._get_annotation_override_fields(
                    annotations_secondary, override_fields=self.SECONDARY_ANNOTATION_OVERRIDE_FIELDS, **kwargs)
                has_data_type_secondary_annotations |= bool(secondary_annotation_overrides)
                has_different_secondary &= secondary_annotation_overrides != annotation_overrides

            if not has_data_type_primary_annotations:
                allowed_consequence_ids = secondary_allowed_consequence_ids
                annotation_overrides = secondary_annotation_overrides
                # Data type only has annotations for second hit, so there is no need for the homozygous recessive query
                self._inheritance_mode = COMPOUND_HET
            elif has_different_secondary:
                parsed_annotations.update({
                    'secondary_consequence_ids': secondary_allowed_consequence_ids,
                    'secondary_annotation_overrides': secondary_annotation_overrides,
                })
                self._has_secondary_annotations = True

            if not (has_data_type_primary_annotations and has_data_type_secondary_annotations):
                self._is_multi_data_type_comp_het = True

        parsed_annotations.update({
            'consequence_ids': allowed_consequence_ids,
            'annotation_overrides': annotation_overrides,
        })
        return parsed_annotations

    def _filter_by_annotations(self, ht, is_comp_het=False, consequence_ids=None, annotation_overrides=None,
                               secondary_consequence_ids=None, secondary_annotation_overrides=None, **kwargs):

        annotation_exprs = {}
        if consequence_ids:
            annotation_exprs[ALLOWED_TRANSCRIPTS] = self._get_allowed_transcripts(ht, consequence_ids)
            ht = ht.annotate(**annotation_exprs)
        annotation_filters = self._get_annotation_override_filters(ht, annotation_overrides or {})

        if not is_comp_het:
            if annotation_exprs:
                annotation_filters.append(self._has_allowed_transcript_filter(ht, ALLOWED_TRANSCRIPTS))
            if annotation_filters:
                ht = ht.filter(hl.any(annotation_filters))
            return ht

        if annotation_filters:
            annotation_exprs[HAS_ANNOTATION_OVERRIDE] = hl.any(annotation_filters)
        if secondary_annotation_overrides is not None:
            overrides = self._get_annotation_override_filters(ht, secondary_annotation_overrides)
            annotation_exprs[f'{HAS_ANNOTATION_OVERRIDE}_secondary'] = hl.any(overrides) if overrides else False
        secondary_allowed_transcripts_field = f'{ALLOWED_TRANSCRIPTS}_secondary'
        if secondary_consequence_ids:
            annotation_exprs[secondary_allowed_transcripts_field] = self._get_allowed_transcripts(ht, secondary_consequence_ids)

        filter_fields = list(annotation_exprs.keys())
        transcript_filter_fields = [ALLOWED_TRANSCRIPTS, secondary_allowed_transcripts_field]
        annotation_exprs.pop(ALLOWED_TRANSCRIPTS, None)
        if annotation_exprs:
            ht = ht.annotate(**annotation_exprs)

        all_filters = [
            self._has_allowed_transcript_filter(ht, field) if field in transcript_filter_fields else ht[field]
            for field in filter_fields
        ]
        return ht.filter(hl.any(all_filters))

    def _get_allowed_consequence_ids(self, annotations):
        allowed_consequences = {
            ann for field, anns in annotations.items()
            if anns and (field not in ANNOTATION_OVERRIDE_FIELDS) for ann in anns
        }
        return self._get_enum_terms_ids(self.TRANSCRIPTS_FIELD, self.TRANSCRIPT_CONSEQUENCE_FIELD, allowed_consequences)

    def _get_allowed_transcripts(self, ht, allowed_consequence_ids):
        transcript_filter = self._get_allowed_transcripts_filter(allowed_consequence_ids)
        return ht[self.TRANSCRIPTS_FIELD].filter(transcript_filter)

    @staticmethod
    def _get_allowed_transcripts_filter(allowed_consequence_ids):
        allowed_consequence_ids = hl.set(allowed_consequence_ids)
        return lambda gc: allowed_consequence_ids.contains(gc.major_consequence_id)

    def _get_annotation_override_fields(self, annotations, override_fields=None, **kwargs):
        override_fields = override_fields or self.ANNOTATION_OVERRIDE_FIELDS
        return {k: annotations[k] for k in override_fields if k in annotations}

    def _get_annotation_override_filters(self, ht, annotation_overrides):
        return []

    def _get_annotation_filters(self, ht, is_secondary=False):
        suffix = '_secondary' if is_secondary else ''
        annotation_filters = []

        allowed_transcripts_field = f'{ALLOWED_TRANSCRIPTS}{suffix}'
        if allowed_transcripts_field in ht.row:
            annotation_filters.append(self._has_allowed_transcript_filter(ht, allowed_transcripts_field))

        annotation_override_field = f'{HAS_ANNOTATION_OVERRIDE}{suffix}'
        if annotation_override_field in ht.row:
            annotation_filters.append(ht[annotation_override_field])
        elif HAS_ANNOTATION_OVERRIDE in ht.row:
            # For secondary annotations, if no secondary override is defined use the primary override
            annotation_filters.append(ht[HAS_ANNOTATION_OVERRIDE])

        return annotation_filters

    @staticmethod
    def _has_allowed_transcript_filter(ht, allowed_transcript_field):
        return hl.is_defined(ht[allowed_transcript_field].first())

    def _filter_compound_hets(self):
        # pylint: disable=pointless-string-statement
        ch_ht = self._comp_het_ht

        # Get possible pairs of variants within the same gene
        def key(v):
            ks = [v[k] for k in self.KEY_FIELD]
            return ks[0] if len(self.KEY_FIELD) == 1 else hl.tuple(ks)
        ch_ht = ch_ht.annotate(key_=key(ch_ht.row), gene_ids=self._gene_ids_expr(ch_ht))
        ch_ht = ch_ht.explode(ch_ht.gene_ids)

        # Filter allowed transcripts to the grouped gene
        transcript_annotations = {
            k: ch_ht[k].filter(lambda t: t.gene_id == ch_ht.gene_ids)
            for k in [ALLOWED_TRANSCRIPTS, ALLOWED_SECONDARY_TRANSCRIPTS] if k in ch_ht.row
        }
        if transcript_annotations:
            ch_ht = ch_ht.annotate(**transcript_annotations)

        if transcript_annotations or self._has_secondary_annotations:
            primary_filters = self._get_annotation_filters(ch_ht)
            ch_ht = ch_ht.annotate(is_primary=hl.coalesce(hl.any(primary_filters), False))
            if self._has_secondary_annotations and not self._is_multi_data_type_comp_het:
                secondary_filters = self._get_annotation_filters(ch_ht, is_secondary=True)
                is_secondary = hl.coalesce(hl.any(secondary_filters), False)
            else:
                is_secondary = ch_ht.is_primary
            ch_ht = ch_ht.annotate(is_secondary=is_secondary)
            if transcript_annotations:
                ch_ht = ch_ht.filter(ch_ht.is_primary | ch_ht.is_secondary)
        else:
            ch_ht = ch_ht.annotate(is_primary=True, is_secondary=True)
        self.unfiltered_comp_het_ht = ch_ht

        if self._is_multi_data_type_comp_het:
            # In cases where comp het pairs must have different data types, there are no single data type results
            return None

        """ Assume a table with the following data
        key_ | gene_ids | is_primary | is_secondary
        1    | A        | true       | true
        2    | A        | true       | true
        2    | B        | true       | true
        3    | A        | false      | true
        3    | B        | false      | true
        """

        variants = ch_ht.collect(_localize=False)
        variants = variants.group_by(lambda v: v.gene_ids)
        variants = variants.items().flatmap(lambda gvs:
            hl.rbind(gvs[0], gvs[1], lambda gene_id, variants:
                hl.rbind(
                    variants.filter(lambda v: v.is_primary),
                    variants.filter(lambda v: v.is_secondary),
                    lambda v1s, v2s:
                        v1s.flatmap(lambda v1:
                            v2s \
                            .filter(lambda v2: ~v2.is_primary | ~v1.is_secondary | (v1.key_ < v2.key_)) \
                            .map(lambda v2: hl.tuple([gene_id, v1, v2]))
                        )
                )
            )
        )

        """ After grouping by gene and pairing/filtering have array of tuples (gene_id, v1, v2)
        (A, 1, 2)
        (A, 1, 3)
        (A, 2, 3)
        (B, 2, 3)
        """

        variants = variants.group_by(lambda v: hl.tuple([v[1].key_, v[2].key_]))
        variants = variants.values().map(lambda v: hl.rbind(
            hl.set(v.map(lambda v: v[0])),
            lambda comp_het_gene_ids: hl.struct(
                v1=v[0][1].annotate(comp_het_gene_ids=comp_het_gene_ids),
                v2=v[0][2].annotate(comp_het_gene_ids=comp_het_gene_ids),
            )
        ))

        """ After grouping by pair have array of structs (v1, v2) annotated with comp_het_gene_ids
        v1 | v2 | v<1/2>.comp_het_gene_ids
         1 | 2  | {A}
         1 | 3  | {A}
         2 | 3  | {A, B} 
        """

        variants = self._filter_comp_het_families(variants)

        return hl.Table.parallelize(
            variants.map(lambda v: hl.struct(**{GROUPED_VARIANTS_FIELD: hl.array([v.v1, v.v2])}))
        )

    def _filter_comp_het_families(self, variants, set_secondary_annotations=True):
        return variants.map(lambda v: v.annotate(
            valid_family_indices=hl.enumerate(v.v1.family_entries).map(lambda x: x[0]).filter(
                lambda i: self._is_valid_comp_het_family(v.v1, v.v2, i)
            )
        )).filter(
            lambda v: v.valid_family_indices.any(hl.is_defined)
        ).map(lambda v: v.select(
            v1=self._annotated_comp_het_variant(v.v1, v.valid_family_indices),
            v2=self._annotated_comp_het_variant(v.v2, v.valid_family_indices, is_secondary=set_secondary_annotations),
        ))

    def _annotated_comp_het_variant(self, variant, valid_family_indices, is_secondary=False):
        if is_secondary and self._has_secondary_annotations and ALLOWED_TRANSCRIPTS in variant and ALLOWED_SECONDARY_TRANSCRIPTS in variant:
            variant = variant.annotate(**{ALLOWED_TRANSCRIPTS: variant[ALLOWED_SECONDARY_TRANSCRIPTS]})

        return variant.annotate(
            family_entries=valid_family_indices.map(lambda i: variant.family_entries[i]),
        )

    @classmethod
    def _gene_ids_expr(cls, ht):
        return hl.set(ht[cls.TRANSCRIPTS_FIELD].map(lambda t: t.gene_id))

    def _is_valid_comp_het_family(self, v1, v2, family_index):
        entries_1 = v1.family_entries[family_index]
        entries_2 = v2.family_entries[family_index]
        family_filters = [hl.is_defined(entries_1), hl.is_defined(entries_2)]
        if self.max_unaffected_samples > 0:
            family_filters.append(hl.enumerate(entries_1).all(lambda x: hl.any([
                (x[1].affected_id != UNAFFECTED_ID), *self._comp_het_entry_has_ref(x[1].GT, entries_2[x[0]].GT),
            ])))
        if self._override_comp_het_alt:
            family_filters.append(entries_1.extend(entries_2).all(lambda x: ~self.GENOTYPE_QUERY_MAP[ALT_ALT](x.GT)))
        return hl.all(family_filters)

    def _comp_het_entry_has_ref(self, gt1, gt2):
        return [self.GENOTYPE_QUERY_MAP[REF_REF](gt1), self.GENOTYPE_QUERY_MAP[REF_REF](gt2)]

    def _format_comp_het_results(self, ch_ht, annotation_fields):
        formatted_grouped_variants = hl.array([
            self._format_results(ch_ht[GROUPED_VARIANTS_FIELD][0], annotation_fields=annotation_fields),
            self._format_results(ch_ht[GROUPED_VARIANTS_FIELD][1], annotation_fields=annotation_fields),
        ])
        ch_ht = ch_ht.annotate(**{GROUPED_VARIANTS_FIELD: hl.sorted(formatted_grouped_variants, key=lambda x: x._sort)})
        return ch_ht.annotate(_sort=ch_ht[GROUPED_VARIANTS_FIELD][0]._sort)

    def _format_results(self, ht, annotation_fields=None, **kwargs):
        if annotation_fields is None:
            annotation_fields = self.annotation_fields()
        annotations = {k: v(ht) for k, v in annotation_fields.items()}
        annotations.update({
            '_sort': self._sort_order(ht),
            'genomeVersion': self.GENOME_VERSION.replace('GRCh', ''),
        })
        results = ht.annotate(**annotations)
        return results.select(*self.CORE_FIELDS, *list(annotations.keys()))

    def format_search_ht(self):
        ch_ht = None
        annotation_fields = self.annotation_fields()
        if self._comp_het_ht:
            ch_ht = self._format_comp_het_results(self._comp_het_ht, annotation_fields)

        if self._ht:
            ht = self._format_results(self._ht.key_by(), annotation_fields=annotation_fields)
            if ch_ht:
                ht = ht.union(ch_ht, unify=True)
        else:
            ht = ch_ht
        return ht

    def search(self):
        ht = self.format_search_ht()

        (total_results, collected) = ht.aggregate((hl.agg.count(), hl.agg.take(ht.row, self._num_results, ordering=ht._sort)))
        logger.info(f'Total hits: {total_results}. Fetched: {self._num_results}')

        return self._format_collected_rows(collected), total_results

    def _format_collected_rows(self, collected):
        if self._has_comp_het_search:
            return [row.get(GROUPED_VARIANTS_FIELD) or row.drop(GROUPED_VARIANTS_FIELD) for row in collected]
        return collected

    def _sort_order(self, ht):
        sort_expressions = self._get_sort_expressions(ht, XPOS)
        if self._sort != XPOS:
            sort_expressions = self._get_sort_expressions(ht, self._sort) + sort_expressions
        return sort_expressions

    @staticmethod
    def _format_prediction_sort_value(value):
        return hl.or_else(-hl.float64(value), 0)

    def _get_sort_expressions(self, ht, sort):
        if sort in self.SORTS:
            return self.SORTS[sort](ht)

        if sort in self.PREDICTION_FIELDS_CONFIG:
            prediction_path = self.PREDICTION_FIELDS_CONFIG[sort]
            return [self._format_prediction_sort_value(ht[prediction_path.source][prediction_path.field])]

        if sort == OMIM_SORT:
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

    @classmethod
    def _gene_count_selects(cls):
        return {
            'gene_ids': cls._gene_ids_expr,
            'families': cls.BASE_ANNOTATION_FIELDS[FAMILY_GUID_FIELD],
        }

    def format_gene_count_hts(self):
        hts = []
        selects = self._gene_count_selects()
        if self._comp_het_ht:
            ch_ht = self._comp_het_ht.explode(self._comp_het_ht[GROUPED_VARIANTS_FIELD])
            hts.append(ch_ht.select(**{k: v(ch_ht[GROUPED_VARIANTS_FIELD]) for k, v in selects.items()}))
        if self._ht:
            hts.append(self._ht.select(**{k: v(self._ht) for k, v in selects.items()}))
        return hts

    def gene_counts(self):
        hts = self.format_gene_count_hts()
        ht = hts[0].key_by()
        for sub_ht in hts[1:]:
            ht = ht.union(sub_ht.key_by(), unify=True)

        ht = ht.explode('gene_ids').explode('families')
        return ht.aggregate(hl.agg.group_by(
            ht.gene_ids, hl.struct(total=hl.agg.count(), families=hl.agg.counter(ht.families))
        ))

    def _filter_variant_ids(self, ht, variant_ids):
        return ht

    def lookup_variants(self, variant_ids, additional_annotations=None):
        self._parse_intervals(intervals=None, variant_ids=variant_ids, variant_keys=variant_ids)
        ht = self._read_table('annotations.ht', drop_globals=['versions'])
        ht = self._filter_variant_ids(ht, variant_ids)
        ht = ht.filter(hl.is_defined(ht[XPOS]))

        annotation_fields = {
            k: v for k, v in self.annotation_fields(include_genotype_overrides=False).items()
            if k not in {FAMILY_GUID_FIELD, GENOTYPES_FIELD}
        }
        if additional_annotations:
            annotation_fields.update(additional_annotations)
        formatted = self._format_results(ht.key_by(), annotation_fields=annotation_fields, include_genotype_overrides=False)

        return formatted.aggregate(hl.agg.take(formatted.row, len(variant_ids)))

    def _import_variant_projects_ht(self, variant_id, project_samples=None, **kwargs):
        projects_ht, _ = self._import_and_filter_multiple_project_hts(project_samples, n_partitions=1)
        return self._filter_variant_ids(projects_ht, [variant_id]).key_by()

    def _get_variant_project_data(self, variant_id, **kwargs):
        projects_ht = self._import_variant_projects_ht(variant_id, **kwargs)
        project_data = projects_ht.aggregate(hl.agg.take(projects_ht.row, 1))
        return project_data[0] if project_data else {}

    def lookup_variant(self, variant_id, **kwargs):
        variants = self.lookup_variants([variant_id], additional_annotations=self._lookup_variant_annotations())
        if not variants:
            raise HTTPNotFound()
        variant = dict(variants[0])
        variant.update(self._get_variant_project_data(variant_id, variant=variant, **kwargs))
        return variant

    @staticmethod
    def _lookup_variant_annotations():
        return {}
