from django.core.management.base import BaseCommand
from xbrowse_server import sample_management
from optparse import make_option


class Command(BaseCommand):

    def handle(self, *args, **options):
        project_id = args[0]
        sample_management.delete_project(project_id)