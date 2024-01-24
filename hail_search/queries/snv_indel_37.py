import hail as hl

from hail_search.constants import SCREEN_KEY, GENOME_VERSION_GRCh37
from hail_search.queries.snv_indel import SnvIndelHailTableQuery


class SnvIndelHailTableQuery37(SnvIndelHailTableQuery):

    GENOME_VERSION = GENOME_VERSION_GRCh37
    PREDICTION_FIELDS_CONFIG = SnvIndelHailTableQuery.PREDICTION_FIELDS_CONFIG_ALL_BUILDS
    LIFTOVER_ANNOTATION_FIELDS = {}

    def _should_add_chr_prefix(self):
        return False

    def _get_annotation_override_filters(self, annotations, *args, **kwargs):
        annotations = {k: v for k, v in annotations.items() if k != SCREEN_KEY}
        return super()._get_annotation_override_filters(annotations, *args, **kwargs)
