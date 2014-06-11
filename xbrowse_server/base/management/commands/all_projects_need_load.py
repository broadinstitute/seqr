from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Individual


class Command(BaseCommand):
    def handle(self, *args, **options):
        for individual in Individual.objects.all():
            individual.set_needs_reload()