import hail as hl

from hail_search.constants import HGMD_KEY, HGMD_PATH_RANGES, \
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
        **MitoHailTableQuery.PATHOGENICITY_FILTERS,
        HGMD_KEY: ('class', HGMD_PATH_RANGES),
    }

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
        PATHOGENICTY_HGMD_SORT_KEY: lambda r: MitoHailTableQuery.SORTS[PATHOGENICTY_SORT_KEY](r) + [r.hgmd.class_id],
    }

    def _prefilter_entries_table(self, ht, *args, **kwargs):
        ht = super()._prefilter_entries_table(ht, *args, **kwargs)
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

    def _get_annotation_override_filters(self, annotations, *args, **kwargs):
        annotation_filters = super()._get_annotation_override_filters(annotations, *args, **kwargs)

        if annotations.get(SCREEN_KEY):
            allowed_consequences = hl.set(self._get_enum_terms_ids(SCREEN_KEY.lower(), 'region_type', annotations[SCREEN_KEY]))
            annotation_filters.append(allowed_consequences.contains(self._ht.screen.region_type_ids.first()))
        if annotations.get(SPLICE_AI_FIELD):
            score_filter, _ = self._get_in_silico_filter(SPLICE_AI_FIELD, annotations[SPLICE_AI_FIELD])
            annotation_filters.append(score_filter)

        return annotation_filters
