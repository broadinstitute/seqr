from collections import OrderedDict
import hail as hl

from hail_search.constants import CLINVAR_KEY, CLINVAR_MITO_KEY, HGMD_KEY, HGMD_PATH_RANGES, \
    GNOMAD_GENOMES_FIELD, PREFILTER_FREQ_CUTOFF, PATH_FREQ_OVERRIDE_CUTOFF, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    SCREEN_KEY, SPLICE_AI_FIELD
from hail_search.queries.base import PredictionPath, QualityFilterFormat
from hail_search.queries.mito import MitoHailTableQuery


class SnvIndelHailTableQuery(MitoHailTableQuery):

    DATA_TYPE = 'SNV_INDEL'

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
    PREDICTION_FIELDS_CONFIG_ALL_BUILDS = {
        'cadd': PredictionPath('cadd', 'PHRED'),
        'eigen': PredictionPath('eigen', 'Eigen_phred'),
        'mpc': PredictionPath('mpc', 'MPC'),
        'primate_ai': PredictionPath('primate_ai', 'score'),
        SPLICE_AI_FIELD: PredictionPath(SPLICE_AI_FIELD, 'delta_score'),
        'splice_ai_consequence': PredictionPath(SPLICE_AI_FIELD, 'splice_consequence'),
        'mut_taster': PredictionPath('dbnsfp', 'MutationTaster_pred'),
        'polyphen': PredictionPath('dbnsfp', 'Polyphen2_HVAR_score'),
        'revel': PredictionPath('dbnsfp', 'REVEL_score'),
        'sift': PredictionPath('dbnsfp', 'SIFT_score'),
    }
    PREDICTION_FIELDS_CONFIG_38 = {
        'fathmm': PredictionPath('dbnsfp', 'fathmm_MKL_coding_score'),
        'mut_pred': PredictionPath('dbnsfp', 'MutPred_score'),
        'vest': PredictionPath('dbnsfp', 'VEST4_score'),
        'gnomad_noncoding': PredictionPath('gnomad_non_coding_constraint', 'z_score'),
    }
    PREDICTION_FIELDS_CONFIG = {
        **PREDICTION_FIELDS_CONFIG_ALL_BUILDS,
        **PREDICTION_FIELDS_CONFIG_38
    }
    PATHOGENICITY_FILTERS = {
        **MitoHailTableQuery.PATHOGENICITY_FILTERS,
        HGMD_KEY: ('class', HGMD_PATH_RANGES),
    }
    PATHOGENICITY_FIELD_MAP = {}
    ANNOTATION_OVERRIDE_FIELDS = [SPLICE_AI_FIELD, SCREEN_KEY]

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
    ENUM_ANNOTATION_FIELDS[CLINVAR_KEY] = ENUM_ANNOTATION_FIELDS.pop(CLINVAR_MITO_KEY)

    SORTS = {
        **MitoHailTableQuery.SORTS,
        PATHOGENICTY_SORT_KEY: lambda r: [MitoHailTableQuery.CLINVAR_SORT(CLINVAR_KEY, r)],
        PATHOGENICTY_HGMD_SORT_KEY: lambda r: [MitoHailTableQuery.CLINVAR_SORT(CLINVAR_KEY, r), r.hgmd.class_id],
    }

    FREQUENCY_PREFILTER_FIELDS = OrderedDict([
        (True, PREFILTER_FREQ_CUTOFF),
        ('is_gt_3_percent', 0.03),
        ('is_gt_5_percent', 0.05),
        ('is_gt_10_percent', 0.1),
    ])

    def _prefilter_entries_table(self, ht, *args, **kwargs):
        ht = super()._prefilter_entries_table(ht, *args, **kwargs)
        if 'variant_ht' not in self._load_table_kwargs and not self._load_table_kwargs.get('_filter_intervals'):
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

        af_cutoff_field = self._get_af_prefilter_field(af_cutoff)
        if af_cutoff_field is None:
            return False

        af_filter = True if af_cutoff_field is True else lambda ht: ht[af_cutoff_field]

        if af_cutoff < PATH_FREQ_OVERRIDE_CUTOFF:
            clinvar_path_ht = self._get_loaded_clinvar_prefilter_ht(pathogenicity)
            if clinvar_path_ht is not False:
                path_cutoff_field = self._get_af_prefilter_field(PATH_FREQ_OVERRIDE_CUTOFF)
                non_clinvar_filter = lambda ht: hl.is_missing(clinvar_path_ht[ht.key])
                if af_filter is not True:
                    non_clinvar_filter = lambda ht: non_clinvar_filter(ht) & af_filter(ht)
                af_filter = lambda ht: ht[path_cutoff_field] | non_clinvar_filter(ht)

        return af_filter

    def _get_af_prefilter_field(self, af_cutoff):
        return next((field for field, cutoff in self.FREQUENCY_PREFILTER_FIELDS.items() if af_cutoff <= cutoff), None)

    def _get_annotation_override_filters(self, ht, annotation_overrides):
        annotation_filters = super()._get_annotation_override_filters(ht, annotation_overrides)

        if annotation_overrides.get(SCREEN_KEY):
            allowed_consequences = hl.set(self._get_enum_terms_ids(SCREEN_KEY.lower(), 'region_type', annotation_overrides[SCREEN_KEY]))
            annotation_filters.append(allowed_consequences.contains(ht.screen.region_type_ids.first()))
        if annotation_overrides.get(SPLICE_AI_FIELD):
            score_filter, _ = self._get_in_silico_filter(ht, SPLICE_AI_FIELD, annotation_overrides[SPLICE_AI_FIELD])
            annotation_filters.append(score_filter)

        return annotation_filters
