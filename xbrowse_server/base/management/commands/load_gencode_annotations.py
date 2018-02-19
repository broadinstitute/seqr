from django.core.management import BaseCommand
from xbrowse_server.mall import get_reference


class Command(BaseCommand):
    def handle(self, *args, **options):
        get_reference()._load_genes()
        get_reference()._load_additional_gene_info()
