from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        from xbrowse_server import mall
        mall.get_custom_population_store().load()
