from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project

from xbrowse_server.mall import get_mall, get_project_datastore

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+', help="project_id")

    def handle(self, *args, **options):
        for project_id in args:
            print("Deleting data from mongodb for project: " + project_id)
            p = Project.objects.get(project_id = project_id)
            get_mall(p).variant_store.delete_project(project_id)
            get_project_datastore(p).delete_project_store(project_id)
            print("Done")
