from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        settings.POPULATION_DATASTORE._clear_all()
