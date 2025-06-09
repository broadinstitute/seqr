from aiohttp.web import HTTPNotFound
from collections import OrderedDict
import hail as hl

from hail_search.constants import CLINVAR_KEY, HGMD_KEY, HGMD_PATH_RANGES, \
    GNOMAD_GENOMES_FIELD, PREFILTER_FREQ_CUTOFF, PATH_FREQ_OVERRIDE_CUTOFF, PATHOGENICTY_HGMD_SORT_KEY, \
    SPLICE_AI_FIELD, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38
from hail_search.queries.base import PredictionPath, QualityFilterFormat
from hail_search.queries.mito import MitoHailTableQuery


class SnvIndelHailTableQuery37(MitoHailTableQuery):

    DATA_TYPE = 'SNV_INDEL'
    GENOME_VERSION = GENOME_VERSION_GRCh37
    LIFT_GENOME_VERSION = GENOME_VERSION_GRCh38

    GENOTYPE_FIELDS = {f.lower(): f for f in ['DP', 'GQ', 'AB']}
    QUALITY_FILTER_FORMAT = {
        'AB': QualityFilterFormat(override=lambda gt: ~gt.GT.is_het(), scale=100),
    }
    POPULATIONS = {
        'seqr': {'af': None, 'an': None, 'hom': 'hom', 'hemi': None, 'het': None, 'sort': 'callset_af', 'sort_subfield': 'ac'},
        'topmed': {'hemi': None},
        'exac': {
            'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi',
            'het': 'AC_Het',
        },
        'gnomad_exomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None, 'sort': 'gnomad_exomes'},
        GNOMAD_GENOMES_FIELD: {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None, 'sort': 'gnomad'},
    }
    PREDICTION_FIELDS_CONFIG = {
        'cadd': PredictionPath('dbnsfp', 'CADD_phred'),
        'eigen': PredictionPath('eigen', 'Eigen_phred'),
        'mpc': PredictionPath('dbnsfp', 'MPC_score'),
        'primate_ai': PredictionPath('dbnsfp', 'PrimateAI_score'),
        SPLICE_AI_FIELD: PredictionPath(SPLICE_AI_FIELD, 'delta_score'),
        'splice_ai_consequence': PredictionPath(SPLICE_AI_FIELD, 'splice_consequence'),
        'mut_taster': PredictionPath('dbnsfp', 'MutationTaster_pred'),
        'polyphen': PredictionPath('dbnsfp', 'Polyphen2_HVAR_score'),
        'revel': PredictionPath('dbnsfp', 'REVEL_score'),
        'sift': PredictionPath('dbnsfp', 'SIFT_score'),
    }
    PATHOGENICITY_FILTERS = {
        **MitoHailTableQuery.PATHOGENICITY_FILTERS,
        HGMD_KEY: ('class', HGMD_PATH_RANGES),
    }
    ANNOTATION_OVERRIDE_FIELDS = [SPLICE_AI_FIELD]

    CORE_FIELDS = MitoHailTableQuery.CORE_FIELDS + ['CAID']

    LIFTOVER_ANNOTATION_FIELDS = {}
    BASE_ANNOTATION_FIELDS = {
        k: v for k, v in MitoHailTableQuery.BASE_ANNOTATION_FIELDS.items()
        if k not in MitoHailTableQuery.MITO_ANNOTATION_FIELDS
    }
    ENUM_ANNOTATION_FIELDS = {
        **MitoHailTableQuery.ENUM_ANNOTATION_FIELDS,
        'screen': {
            'response_key': 'screenRegionType',
            'format_value': lambda value: value.region_types.first(),
        },
    }

    SORTS = {
        **MitoHailTableQuery.SORTS,
        PATHOGENICTY_HGMD_SORT_KEY: lambda r: [MitoHailTableQuery.CLINVAR_SORT(CLINVAR_KEY, r), r.hgmd.class_id],
    }

    FREQUENCY_PREFILTER_FIELDS = OrderedDict([
        (True, PREFILTER_FREQ_CUTOFF),
        ('is_gt_10_percent', 0.1),
    ])

    PREFILTER_TABLES = {
        **MitoHailTableQuery.PREFILTER_TABLES,
        GNOMAD_GENOMES_FIELD: 'high_af_variants.ht',
    }

    def _prefilter_entries_table(self, ht, *args, raw_intervals=None, **kwargs):
        ht = super()._prefilter_entries_table(ht, *args, **kwargs)
        load_table_intervals = self._load_table_kwargs.get('_intervals') or []
        no_interval_prefilter = not load_table_intervals or len(raw_intervals or []) > len(load_table_intervals)
        if 'variant_ht' not in self._load_table_kwargs and no_interval_prefilter:
            af_ht = self._get_loaded_filter_ht(
                GNOMAD_GENOMES_FIELD, self._get_gnomad_af_prefilter, **kwargs)
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

        af_cutoff_field = self._get_af_prefilter_field(af_cutoff)
        if af_cutoff_field is None:
            return False

        clinvar_path_ht = False
        if af_cutoff < PATH_FREQ_OVERRIDE_CUTOFF:
            clinvar_path_ht = self._get_loaded_clinvar_prefilter_ht(pathogenicity)

        if clinvar_path_ht is not False:
            path_cutoff_field = self._get_af_prefilter_field(PATH_FREQ_OVERRIDE_CUTOFF)
            non_clinvar_filter = lambda ht: hl.is_missing(clinvar_path_ht[ht.key])
            if af_cutoff_field is not True:
                non_clinvar_var_filter = non_clinvar_filter
                non_clinvar_filter = lambda ht: non_clinvar_var_filter(ht) & self._af_prefilter(af_cutoff_field)(ht)
            af_filter = lambda ht: ht[path_cutoff_field] | non_clinvar_filter(ht)
        else:
            af_filter = self._af_prefilter(af_cutoff_field)

        return af_filter

    @staticmethod
    def _af_prefilter(af_cutoff_field):
        return True if af_cutoff_field is True else lambda ht: ht[af_cutoff_field]

    def _get_af_prefilter_field(self, af_cutoff):
        return next((field for field, cutoff in self.FREQUENCY_PREFILTER_FIELDS.items() if af_cutoff <= cutoff), None)

    def _get_annotation_override_filters(self, ht, annotation_overrides):
        annotation_filters = super()._get_annotation_override_filters(ht, annotation_overrides)

        if annotation_overrides.get(SPLICE_AI_FIELD):
            score_filter, _ = self._get_in_silico_filter(ht, SPLICE_AI_FIELD, annotation_overrides[SPLICE_AI_FIELD])
            annotation_filters.append(score_filter)

        return annotation_filters

    @staticmethod
    def _stat_has_non_ref(s):
        return (s.het_samples > 0) | (s.hom_samples > 0)

    @staticmethod
    def _lookup_variant_annotations():
        return {'liftover_locus': lambda r: r.rg38_locus}

    @classmethod
    def _get_lifted_table_path(cls, path):
        return f'{cls._get_table_dir(path)}/{cls.LIFT_GENOME_VERSION}/{cls.DATA_TYPE}/{path}'

    def _get_variant_project_data(self, variant_id, variant=None, **kwargs):
        project_data = super()._get_variant_project_data(variant_id, **kwargs)
        liftover_locus = variant.pop('liftover_locus')
        if not liftover_locus:
            return project_data
        interval = hl.eval(hl.interval(liftover_locus, liftover_locus, includes_start=True, includes_end=True))
        self._load_table_kwargs['_intervals'] = [interval]
        self._get_table_path = self._get_lifted_table_path
        try:
            lift_project_data = super()._get_variant_project_data(variant_id, **kwargs)
        except HTTPNotFound:
            return project_data
        project_data['familyGenotypes'].update(lift_project_data['familyGenotypes'])
        return project_data.annotate(liftedFamilyGuids=sorted(lift_project_data['familyGenotypes'].keys()))
