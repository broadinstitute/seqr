from aiohttp.web import HTTPBadRequest

from hail_search.constants import EXTENDED_SPLICE_KEY, UTR_ANNOTATOR_KEY
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

    def _get_allowed_consequence_ids(self, annotations):
        return super()._get_allowed_consequence_ids({
            k: v for k, v in annotations.items() if k not in {EXTENDED_SPLICE_KEY, UTR_ANNOTATOR_KEY}
        })

    @staticmethod
    def _get_allowed_transcripts_filter(allowed_consequence_ids):
        return SnvIndelHailTableQuery37._get_allowed_transcripts_filter(
            allowed_consequence_ids.get(SnvIndelHailTableQuery37.TRANSCRIPT_CONSEQUENCE_FIELD)
        )
