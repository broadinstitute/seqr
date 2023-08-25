import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneShet

logger = logging.getLogger(__name__)


class ShetReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneShet
    # The .tsv file is generated from the Google Doc at https://docs.google.com/spreadsheets/d/1enxGBWCAFBHdrRlqCj_ueleiDo9K9GWn/edit#gid=1146995171
    # by downloading with a tsv format.
    url = 'https://storage.googleapis.com/seqr-reference-data/gene_constraint/shet_Zeng(2023).xlsx%20-%20All%20scores-for%20gene%20page.tsv'

    @staticmethod
    def parse_record(record):
        yield {
            'gene_id': record['ensg'],
            'shet': float(record['post_mean (Shet)']),
        }


class Command(GeneCommand):
    reference_data_handler = ShetReferenceDataHandler
