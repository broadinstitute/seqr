from django.core.management.base import BaseCommand

from reference_data.utils.gene_utils import get_genes_by_id_and_symbol
from reference_data.models import GeneMetadataModel


class ReferenceDataHandler(object):

    model_cls = GeneMetadataModel

    def __init__(self, **kwargs):
        gene_ids_to_gene, gene_symbols_to_gene = get_genes_by_id_and_symbol()
        self.gene_reference = {
            'gene_symbols_to_gene': gene_symbols_to_gene,
            'gene_ids_to_gene': gene_ids_to_gene,
        }

    def update_records(self, **kwargs):
        self.model_cls.update_records(**self.gene_reference, **kwargs)


class GeneCommand(BaseCommand):
    reference_data_handler = ReferenceDataHandler

    def handle(self, *args, **options):
        self.reference_data_handler(**options).update_records()
