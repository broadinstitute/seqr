import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneCopyNumberSensitivity

logger = logging.getLogger(__name__)


class CNSensitivityReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneCopyNumberSensitivity
    url = 'https://zenodo.org/record/6347673/files/Collins_rCNV_2022.dosage_sensitivity_scores.tsv.gz'

    @staticmethod
    def parse_record(record):
        yield {
            'gene_symbol': record['#gene'],
            'pHI': float(record['pHaplo']),
            'pTS': float(record['pTriplo']),
        }


class Command(GeneCommand):
    reference_data_handler = CNSensitivityReferenceDataHandler
