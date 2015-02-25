from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project
from xbrowse.parsers import fam_stuff

class Command(BaseCommand):
    """Command to generate a ped file for a given project"""

    def handle(self, *args, **options):
        for project_name in args:
            project = Project.objects.get(project_id=project_name)
            individuals = project.get_individuals()
            filename = project.project_id + ".ped"
            print("Writing %s individuals to %s" % (len(individuals), filename))

            with open(filename, "w") as f:
                fam_stuff.write_individuals_to_ped_file(f, individuals)
