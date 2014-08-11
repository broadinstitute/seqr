from django.conf import settings
from django.core.management import BaseCommand
from xbrowse_server import mall
from xbrowse_server.mall import get_reference


class Command(BaseCommand):
    def handle(self, *args, **options):
        get_reference().load()
        mall.get_annotator().load()