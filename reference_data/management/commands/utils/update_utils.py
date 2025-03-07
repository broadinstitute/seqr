import logging
import os
import gzip
import traceback
from django.core.management.base import BaseCommand, CommandError

from reference_data.management.commands.utils.download_utils import download_file
from reference_data.management.commands.utils.gene_utils import get_genes_by_symbol_and_id
from reference_data.models import GeneInfo, GeneMetadataModel

logger = logging.getLogger(__name__)


class ReferenceDataHandler(object):

    model_cls = GeneMetadataModel

    def __init__(self, **kwargs):
        if GeneInfo.objects.count() == 0:
            raise CommandError("GeneInfo table is empty. Run './manage.py update_gencode' before running this command.")

        gene_symbols_to_gene, gene_ids_to_gene = get_genes_by_symbol_and_id()
        self.gene_reference = {
            'gene_symbols_to_gene': gene_symbols_to_gene,
            'gene_ids_to_gene': gene_ids_to_gene,
        }

    def update_records(self):
        try:
            self.model_cls.update_records(
                self.gene_reference['gene_ids_to_gene'], self.gene_reference['gene_symbols_to_gene'],
            )
        except Exception as e:
            logger.error(str(e), extra={'traceback': traceback.format_exc()})


class GeneCommand(BaseCommand):
    reference_data_handler = ReferenceDataHandler

    def handle(self, *args, **options):
        self.reference_data_handler(**options).update_records()
