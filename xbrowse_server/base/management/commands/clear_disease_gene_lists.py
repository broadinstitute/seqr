from django.core.management.base import BaseCommand
from xbrowse_server.gene_lists.models import GeneList


class Command(BaseCommand):
    def handle(self, *args, **options):
        for gene_list in GeneList.objects.all():
            gene_list.delete()