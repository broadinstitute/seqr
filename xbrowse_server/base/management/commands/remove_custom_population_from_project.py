from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation
from optparse import make_option
import sys

class Command(BaseCommand):


    def add_arguments(self, parser):
        #parser.add_argument('--all-projects', dest="all_projects", action="store_true")
        parser.add_argument('project_id')
        parser.add_argument('custom_population_id')

    def handle(self, *args, **options):
        for custom_refpop in ReferencePopulation.objects.all():
            print(custom_refpop.slug)
        
        if "all_projects" in options and options["all_projects"]:
            projects = Project.objects.all()            
            population_slug = args[0]
            print("Removing population %s from all %s projects" % (population_slug, len(projects)))
            r = raw_input("Continue? [Y/n] ")
            if r != "Y":
                sys.exit("Existing..")
        else:
            projects = [Project.objects.get(project_id=options["project_id"])]
            population_slug = options["custom_population_id"]

        for project in projects:
            population = ReferencePopulation.objects.get(slug=population_slug)
            print("Removing population " + population_slug + " from project "  + str(project))
            project.private_reference_populations.remove(population)
            project.save()

