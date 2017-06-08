from django.core.management.base import BaseCommand
from xbrowse_server.search_cache.utils import clear_results_cache

class Command(BaseCommand):

    def handle(self, *args, **options):
        clear_results_cache()
