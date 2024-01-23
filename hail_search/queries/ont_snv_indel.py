from hail_search.queries.base import BaseHailTableQuery, PredictionPath
from hail_search.queries.snv_indel import SnvIndelHailTableQuery


class OntSnvIndelHailTableQuery(SnvIndelHailTableQuery):

    DATA_TYPE = 'ONT_SNV_INDEL'

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS

    PREDICTION_FIELDS_CONFIG = {
        **SnvIndelHailTableQuery.PREDICTION_FIELDS_CONFIG,
        'fathmm': PredictionPath('dbnsfp', 'fathmm_MKL_coding_pred'),
        'polyphen': PredictionPath('dbnsfp', 'Polyphen2_HVAR_pred'),
        'sift': PredictionPath('dbnsfp', 'SIFT_pred'),
    }

    def _get_loaded_filter_ht(self, *args, **kwargs):
        return None
