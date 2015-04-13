from django.conf import settings
from django.core.management import BaseCommand
from xbrowse_server import mall
from xbrowse_server.mall import get_reference
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator


class Command(BaseCommand):
    def handle(self, *args, **options):

        if settings.CUSTOM_ANNOTATOR_SETTINGS is not None:
            print("Load dbNSFP.. ")

            # note that you could use mall.get_custom_annotator() here too
            custom_annotator = CustomAnnotator(settings.CUSTOM_ANNOTATOR_SETTINGS)
            custom_annotator.load()

        get_reference().load()
        mall.get_annotator().load()

