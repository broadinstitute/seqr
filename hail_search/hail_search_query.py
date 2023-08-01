from aiohttp.web import HTTPBadRequest
from collections import defaultdict, namedtuple
import hail as hl
import logging
import os

from hail_search.constants import AFFECTED, UNAFFECTED, AFFECTED_ID, UNAFFECTED_ID, VARIANT_DATASET, VARIANT_KEY_FIELD,\
    GNOMAD_GENOMES_FIELD, XPOS, GENOME_VERSION_GRCh38_DISPLAY

DATASETS_DIR = os.environ.get('DATASETS_DIR', '/hail_datasets')

logger = logging.getLogger(__name__)


PredictionPath = namedtuple('PredictionPath', ['source', 'field'])


def _to_camel_case(snake_case_str):
    converted = snake_case_str.replace('_', ' ').title().replace(' ', '')
    return converted[0].lower() + converted[1:]


class BaseHailTableQuery(object):

    GENOTYPE_FIELDS = {}
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

    @property
    def annotation_fields(self):
        ht_globals = {k: hl.eval(self._ht[k]) for k in self.GLOBALS}
        enums = ht_globals.pop('enums')

        annotation_fields = {
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population) for population in self.POPULATIONS.keys()
            }),
            'predictions': lambda r: hl.struct(**{
                prediction: hl.array(enums[path.source][path.field])[r[path.source][f'{path.field}_id']]
                if enums.get(path.source, {}).get(path.field) else r[path.source][path.field]
                for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
            'transcripts': lambda r: hl.or_else(
                r.sorted_transcript_consequences, hl.empty_array(r.sorted_transcript_consequences.dtype.element_type)
            ).map(
                lambda t: self._enum_field(t, enums['sorted_transcript_consequences'], **self._format_transcript_args())
            ).group_by(lambda t: t.geneId),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)

        format_enum = lambda k, enum_config: lambda r: self._enum_field(r[k], enums[k], ht_globals=ht_globals, **enum_config)
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

        self._load_filtered_table(data_type, sample_data, **kwargs)

    def _load_filtered_table(self, data_type, sample_data, **kwargs):
        self._ht = self.import_filtered_table(data_type, sample_data, **kwargs)

    def import_filtered_table(self, data_type, sample_data, **kwargs):
        tables_path = f'{DATASETS_DIR}/{self._genome_version}/{data_type}'

        family_samples = defaultdict(list)
        project_samples = defaultdict(list)
        for s in sample_data:
            family_samples[s['family_guid']].append(s)
            project_samples[s['project_guid']].append(s)

        logger.info(f'Loading {data_type} data for {len(family_samples)} families in {len(project_samples)} projects')
        if len(family_samples) == 1:
            family_guid, family_sample_data = list(family_samples.items())[0]
            family_ht = hl.read_table(f'{tables_path}/families/{family_guid}.ht')
            families_ht = self._filter_entries_table(family_ht, family_sample_data)
        else:
            filtered_project_hts = []
            exception_messages = set()
            for project_guid, project_sample_data in project_samples.items():
                project_ht = hl.read_table(f'{tables_path}/projects/{project_guid}.ht')
                try:
                    filtered_project_hts.append(self._filter_entries_table(project_ht, project_sample_data))
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
        # Add globals
        ht = ht.join(hl.read_table(annotations_ht_path).head(0).select().select_globals(*self.GLOBALS), how='left')

        ht = ht.transmute(
            genotypes=ht.family_entries.flatmap(lambda x: x).filter(
                lambda gt: hl.is_defined(gt.individualGuid)
            ).map(lambda gt: gt.select(
                'sampleId', 'individualGuid', 'familyGuid',
                numAlt=hl.if_else(hl.is_defined(gt.GT), gt.GT.n_alt_alleles(), -1),
                **{k: gt[field] for k, field in self.GENOTYPE_FIELDS.items()}
            ))
        )

        return ht

    def _filter_entries_table(self, ht, sample_data):
        ht = self._add_entry_sample_families(ht, sample_data)

        ht = ht.annotate(family_entries=ht.family_entries.map(
            lambda entries: hl.or_missing(entries.any(lambda x: x.GT.is_non_ref()), entries))
        )

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
        for sample_id, family_guid in sample_id_family_map.items():
            sample_index = sample_id_index_map[sample_id]
            family_index = family_index_map[family_guid]
            if not family_sample_indices[family_index]:
                family_sample_indices[family_index] = []
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

        return ht

    @staticmethod
    def _missing_entry(entry):
        entry_type = dict(**entry.dtype)
        return hl.struct(**{k: hl.missing(v) for k, v in entry_type.items()})

    def _format_results(self, ht):
        annotations = {k: v(ht) for k, v in self.annotation_fields.items()}
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
        'splice_ai': PredictionPath('splice_ai', 'delta_score'),
        'splice_ai_consequence': PredictionPath('splice_ai', 'splice_consequence'),
        'vest': PredictionPath('dbnsfp', 'VEST4_score'),
        'mut_taster': PredictionPath('dbnsfp', 'MutationTaster_pred'),
        'polyphen': PredictionPath('dbnsfp', 'Polyphen2_HVAR_pred'),
        'revel': PredictionPath('dbnsfp', 'REVEL_score'),
        'sift': PredictionPath('dbnsfp', 'SIFT_pred'),
    }

    GLOBALS = BaseHailTableQuery.GLOBALS + ['versions']
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid']
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),
        'mainTranscriptId': lambda r: r.sorted_transcript_consequences.first().transcript_id,
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

    def import_filtered_table(self, *args, **kwargs):
        ht = super(VariantHailTableQuery, self).import_filtered_table(*args, **kwargs)
        return ht.key_by(**{VARIANT_KEY_FIELD: ht.variant_id})

    def _format_transcript_args(self):
        args = super(VariantHailTableQuery, self)._format_transcript_args()
        args.update({
            'annotate_value': lambda transcript, *args: {'major_consequence': transcript.consequence_terms.first()},
            'drop_fields': ['consequence_terms'],
        })
        return args


QUERY_CLASS_MAP = {
    VARIANT_DATASET: VariantHailTableQuery,
}
