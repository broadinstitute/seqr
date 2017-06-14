from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        for indiv in project.get_individuals():
            print indiv.indiv_id