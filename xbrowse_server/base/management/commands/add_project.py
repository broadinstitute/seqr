from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
import sys

class Command(BaseCommand):

    def handle(self, *args, **options):
        project_id = args[0]
        if "." in project_id:
            sys.exit("ERROR: A '.' in the project ID is not supported")

        if Project.objects.filter(project_id=project_id).exists():
            raise Exception("Project exists :(")
        Project.objects.create(project_id=project_id)
