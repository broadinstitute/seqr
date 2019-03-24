import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import PrimateAI

logger = logging.getLogger(__name__)


class PrimateAIReferenceDataHandler(ReferenceDataHandler):

    model_cls = PrimateAI
    url = "http://storage.googleapis.com/seqr-reference-data/primate_ai/Gene_metrics_clinvar_pcnt.cleaned_v0.2.txt"

    @staticmethod
    def parse_record(record):
        yield {
            'gene_symbol': record['genesymbol'],
            'percentile_25': float(record['pcnt25']),
            'percentile_75': float(record['pcnt75']),
        }


class Command(GeneCommand):
    reference_data_handler = PrimateAIReferenceDataHandler
