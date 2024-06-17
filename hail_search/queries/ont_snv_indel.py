from aiohttp.web import HTTPBadRequest

from hail_search.queries.base import BaseHailTableQuery
from hail_search.queries.snv_indel import SnvIndelHailTableQuery
from hail_search.queries.snv_indel_37 import SnvIndelHailTableQuery37


class OntSnvIndelHailTableQuery(SnvIndelHailTableQuery):

    DATA_TYPE = 'ONT_SNV_INDEL'

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS

    def _get_loaded_filter_ht(self, *args, **kwargs):
        return None

    def _add_project_lookup_data(self, *args, **kwargs):
        raise HTTPBadRequest(reason='Variant lookup is not supported for ONT data')

    @staticmethod
    def _get_allowed_transcripts_filter(allowed_consequence_ids):
        return SnvIndelHailTableQuery37._get_allowed_transcripts_filter(allowed_consequence_ids)
