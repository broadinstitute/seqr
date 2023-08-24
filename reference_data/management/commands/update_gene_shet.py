import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneShet

logger = logging.getLogger(__name__)


class ShetReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneShet
    url = 'https://storage.googleapis.com/seqr-reference-data/Shet/Shet_Zeng_2023.tsv'

    @staticmethod
    def parse_record(record):
        yield {
            'gene_id': record['ensg'],
            'shet': float(record['post_mean_shet']),
            'shet_constrained': bool(int(record['shet_constrained'])),
        }


class Command(GeneCommand):
    reference_data_handler = ShetReferenceDataHandler
