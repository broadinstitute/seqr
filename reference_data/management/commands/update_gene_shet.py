import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneShet

logger = logging.getLogger(__name__)


class ShetReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneShet
    url = 'https://zenodo.org/record/7939768/files/s_het_estimates.genebayes.tsv'

    @staticmethod
    def parse_record(record):
        yield {
            'gene_id': record['ensg'],
            'post_mean': float(record['post_mean']),
        }


class Command(GeneCommand):
    reference_data_handler = ShetReferenceDataHandler
