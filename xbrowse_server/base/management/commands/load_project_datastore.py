import django.core.management.base 
from xbrowse_server import xbrowse_controls

class Command(django.core.management.base.BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('project_id', nargs='+')

    def handle(self, *args, **options):
        for project_id in options["project_id"]:
            xbrowse_controls.load_project_datastore(project_id)
