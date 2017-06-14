from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation
from optparse import make_option
import sys

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('--all-projects', dest="all_projects", action="store_true")

    def handle(self, *args, **options):
        if options["all_projects"]:
            projects = Project.objects.all()
            print("Adding population %s to all %s projects" % (args[1], len(projects)))
            r = raw_input("Continue? [Y/n] ")
            if r != "Y":
                sys.exit("Existing..")
        else:
            projects = [Project.objects.get(project_id=args[0])]
            
        population_slug = args[1]
        for project in projects:
            population = ReferencePopulation.objects.get(slug=population_slug)
            print("Adding population " + population_slug + " to project "  + str(project))
            project.private_reference_populations.add(population)

