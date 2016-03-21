from optparse import make_option

from django.core.management.base import BaseCommand

from xbrowse_server.base.project_admin import copy_project
from xbrowse_server.base.models import Project


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

        parser.add_argument('--from')
        parser.add_argument('--to')
        parser.add_argument('--upsert', action='store_true', dest='upsert', default=False)
        parser.add_argument('--samples', action='store_true', dest='samples', default=False)
        parser.add_argument('--project_settings', action='store_true', dest='project_settings', default=False)
        parser.add_argument('--users', action='store_true', dest='users', default=False)
        parser.add_argument('--saved_variants', action='store_true', dest='saved_variants', default=False)
        parser.add_argument('--data', action='store_true', dest='data', default=False)
        parser.add_argument('--all', action='store_true', dest='all', default=False)


    def handle(self, *args, **options):

        from_project = Project.objects.get(project_id=options.get('from'))
        to_project = Project.objects.get(project_id=options.get('to'))

        upsert = options.get('upsert')
        samples = options.get('samples')
        project_settings = options.get('project_settings')
        users = options.get('users')
        saved_variants = options.get('saved_variants')
        data = options.get('data')
        if options.get('all'):
            upsert = True
            users = True
            saved_variants = True

        copy_project(
            from_project,
            to_project,
            samples=samples,
            upsert=upsert,
            settings=project_settings,
            users=users,
            saved_variants=saved_variants,
            data=data
        )
