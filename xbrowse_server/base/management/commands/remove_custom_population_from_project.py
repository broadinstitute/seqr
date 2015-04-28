from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--some-option'),
    )

    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        population_slug = args[1]
        population = ReferencePopulation.objects.get(slug=population_slug)
        project.private_reference_populations.remove(population)