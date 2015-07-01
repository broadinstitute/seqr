from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--some-option'),
    )

    def handle(self, *args, **options):
        if len(args) != 2:
            import sys
            sys.exit("Usage: " + sys.argv[0] + " " + sys.argv[1] + " [project_id] [custom-reference-population slug]")
        project = Project.objects.get(project_id=args[0])
        population_slug = args[1]
        population = ReferencePopulation.objects.get(slug=population_slug)
        project.private_reference_populations.remove(population)
