from aiohttp.web import HTTPBadRequest

from hail_search.queries.base import BaseHailTableQuery, PredictionPath
from hail_search.queries.snv_indel import SnvIndelHailTableQuery


class OntSnvIndelHailTableQuery(SnvIndelHailTableQuery):

    DATA_TYPE = 'ONT_SNV_INDEL'

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS

    def _get_loaded_filter_ht(self, *args, **kwargs):
        return None

    def _add_project_lookup_data(self, *args, **kwargs):
        raise HTTPBadRequest(reason='Variant lookup is not supported for ONT data')
