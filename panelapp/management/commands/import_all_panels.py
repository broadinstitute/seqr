import logging

from django.core.management.base import BaseCommand

from panelapp.models import PanelAppAU, PanelAppUK
from reference_data.utils.gene_utils import get_genes_by_id_and_symbol

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source', help='Panel App Source', choices=[model.SOURCE for model in [PanelAppAU, PanelAppUK]])

    def handle(self, *args, **options):
        source = options['source']
        data_cls = next(model for model in [PanelAppAU, PanelAppUK] if model.SOURCE == source)
        gene_ids_to_gene, _ = get_genes_by_id_and_symbol()
        data_cls.update_records(gene_ids_to_gene=gene_ids_to_gene)
