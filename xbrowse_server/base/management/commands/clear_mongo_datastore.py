from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        datastore = settings.DATASTORE
        datastore._clear_all()