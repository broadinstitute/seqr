import logging
import traceback
from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gene_utils import get_genes_by_symbol_and_id
from reference_data.models import GeneMetadataModel

logger = logging.getLogger(__name__)


class ReferenceDataHandler(object):

    model_cls = GeneMetadataModel

    def __init__(self, **kwargs):
        # TODO need to be db IDs
        gene_symbols_to_gene, gene_ids_to_gene = get_genes_by_symbol_and_id()
        self.gene_reference = {
            'gene_symbols_to_gene': gene_symbols_to_gene,
            'gene_ids_to_gene': gene_ids_to_gene,
        }

    def update_records(self, **kwargs):
        try:
            self.model_cls.update_records(
                self.gene_reference['gene_ids_to_gene'], self.gene_reference['gene_symbols_to_gene'], **kwargs,
            )
        except Exception as e:
            logger.error(str(e), extra={'traceback': traceback.format_exc()})


class GeneCommand(BaseCommand):
    reference_data_handler = ReferenceDataHandler

    def handle(self, *args, **options):
        self.reference_data_handler(**options).update_records()
