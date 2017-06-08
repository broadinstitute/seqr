from django.core.management.base import BaseCommand
from xbrowse_server import sample_management


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-f', '--delete-data', help="delete data also", action='store_true')
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        project_id = args[0]

        print('delete_data: %s' % bool(options['delete_data']))
        sample_management.delete_project(project_id, delete_data=bool(options.delete_data))
