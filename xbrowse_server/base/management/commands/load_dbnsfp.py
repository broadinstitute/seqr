from django.core.management import BaseCommand
from django.conf import settings
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator

class Command(BaseCommand):
    def handle(self, *args, **options):
        _custom_annotator = CustomAnnotator(settings.CUSTOM_ANNOTATOR_SETTINGS)
        _custom_annotator.load()

