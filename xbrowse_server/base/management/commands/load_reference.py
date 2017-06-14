from django.core.management import BaseCommand
from xbrowse_server import mall

class Command(BaseCommand):
    def handle(self, *args, **options):
        mall.get_annotator().load()
