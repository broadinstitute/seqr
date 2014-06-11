from django.core.management.base import BaseCommand
from django.conf import settings
from xbrowse_server.base.models import ReferencePopulation


class Command(BaseCommand):

    def handle(self, *args, **options):

        slug = args[0]
        file_path = args[1]

        population = {
            'slug': slug,
            'file_type': 'xbrowse_counts_file',
            'file_path': file_path,
        }
        settings.POPULATION_FREQUENCY_STORE.load_population_to_annotator(population)
        ReferencePopulation.objects.create(slug=slug)
