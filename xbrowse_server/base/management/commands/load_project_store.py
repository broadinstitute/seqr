from django.core.management.base import BaseCommand
from xbrowse_server import xbrowse_controls


class Command(BaseCommand):
    def handle(self, *args, **options):
        project_id = args[0]
        xbrowse_controls.reload_project_datastore(project_id)