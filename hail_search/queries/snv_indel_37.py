from collections import OrderedDict

from hail_search.constants import GENOME_VERSION_GRCh37, PREFILTER_FREQ_CUTOFF
from hail_search.queries.snv_indel import SnvIndelHailTableQuery


class SnvIndelHailTableQuery37(SnvIndelHailTableQuery):

    GENOME_VERSION = GENOME_VERSION_GRCh37
    PREDICTION_FIELDS_CONFIG = SnvIndelHailTableQuery.PREDICTION_FIELDS_CONFIG_ALL_BUILDS
    LIFTOVER_ANNOTATION_FIELDS = {}
    ANNOTATION_OVERRIDE_FIELDS = SnvIndelHailTableQuery.ANNOTATION_OVERRIDE_FIELDS[:-1]
    FREQUENCY_PREFILTER_FIELDS = OrderedDict([
        (True, PREFILTER_FREQ_CUTOFF),
        ('is_gt_10_percent', 0.1),
    ])

    def _should_add_chr_prefix(self):
        return False
