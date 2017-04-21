from django.core.management.base import BaseCommand
from xbrowse_server import xbrowse_controls


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('-s', '--start-from-chrom', help="start loading from this chromosome")

    def handle(self, *args, **options):
        project_id = args[0]
        print("Loading project datastore: %s" % project_id)
        xbrowse_controls.load_project_datastore(project_id, start_from_chrom=options['start_from_chrom'])
