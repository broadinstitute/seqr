from hail_search.queries.base import BaseHailTableQuery, PredictionPath
from hail_search.queries.snv_indel import SnvIndelHailTableQuery
from hail_search.constants import GENOME_VERSION_GRCh38


class OntSnvIndelHailTableQuery(SnvIndelHailTableQuery):

    DATA_TYPE = 'ONT_SNV_INDEL'

    GENOME_VERSIONS = BaseHailTableQuery.GENOME_VERSIONS
    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS

    PREDICTION_FIELDS_CONFIG = {
        **SnvIndelHailTableQuery.PREDICTION_FIELDS_CONFIG,
        **SnvIndelHailTableQuery.GENOME_BUILD_PREDICTION_FIELDS_CONFIG[GENOME_VERSION_GRCh38],
        'fathmm': PredictionPath('dbnsfp', 'fathmm_MKL_coding_pred'),
        'polyphen': PredictionPath('dbnsfp', 'Polyphen2_HVAR_pred'),
        'sift': PredictionPath('dbnsfp', 'SIFT_pred'),
    }
    GENOME_BUILD_PREDICTION_FIELDS_CONFIG = {}

    def _get_loaded_filter_ht(self, *args, **kwargs):
        return None
