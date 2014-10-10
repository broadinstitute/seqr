from optparse import make_option

from django.core.management.base import BaseCommand

from xbrowse_server.base.project_admin import copy_project
from xbrowse_server.base.models import Project


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--from'),
        make_option('--to'),
        make_option('--upsert', action='store_true', dest='upsert', default=False),
        make_option('--samples', action='store_true', dest='samples', default=False),
        make_option('--project_settings', action='store_true', dest='project_settings', default=False),
        make_option('--users', action='store_true', dest='users', default=False),
        make_option('--saved_variants', action='store_true', dest='saved_variants', default=False),
        make_option('--data', action='store_true', dest='data', default=False),
        make_option('--all', action='store_true', dest='all', default=False),
    )

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
