from django.core.management.base import BaseCommand
from xbrowse_server import sample_management


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        project_id = args[0]
        sample_management.delete_project(project_id)
