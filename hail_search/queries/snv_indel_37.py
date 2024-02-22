from hail_search.constants import SCREEN_KEY, GENOME_VERSION_GRCh37
from hail_search.queries.snv_indel import SnvIndelHailTableQuery


class SnvIndelHailTableQuery37(SnvIndelHailTableQuery):

    GENOME_VERSION = GENOME_VERSION_GRCh37
    PREDICTION_FIELDS_CONFIG = SnvIndelHailTableQuery.PREDICTION_FIELDS_CONFIG_ALL_BUILDS
    LIFTOVER_ANNOTATION_FIELDS = {}
    ANNOTATION_OVERRIDE_FIELDS = SnvIndelHailTableQuery.ANNOTATION_OVERRIDE_FIELDS[:-1]

    def _should_add_chr_prefix(self):
        return False
