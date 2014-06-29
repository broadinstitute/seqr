from django.conf import settings
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        settings.REFERENCE.load()
        settings.ANNOTATOR.load()