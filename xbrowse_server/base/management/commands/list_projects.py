from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project

class Command(BaseCommand):
    """Command to generate a ped file for a given project"""

    def handle(self, *args, **options):
        projects = Project.objects.all()
        for project in projects:
            individuals = project.get_individuals()

            print("%3d families  %3d individuals  project id:   %s" % (
                len({i.get_family_id() for i in individuals} - {None,}),
                len(individuals),
                project.project_id))
