import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneCopyNumberSensitivity

logger = logging.getLogger(__name__)


class CNSensitivityReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneCopyNumberSensitivity
    url = 'https://storage.googleapis.com/seqr-reference-data/cn_sensitivity/pHI_pTS_scores.Jan21.txt'

    @staticmethod
    def parse_record(record):
        yield {
            'gene_symbol': record['#gene'],
            'pHI': float(record['pHI']),
            'pTS': float(record['pTS']),
        }


class Command(GeneCommand):
    reference_data_handler = CNSensitivityReferenceDataHandler
