from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.project_admin import copy_project
from xbrowse_server.base.models import Project, Individual, Family, Cohort, ProjectPhenotype, IndividualPhenotype, FamilySearchFlag, ProjectGeneList
from django.core.exceptions import ObjectDoesNotExist
from xbrowse_server import sample_management

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--from'),
        make_option('--to'),
        make_option('--upsert', action='store_true', dest='upsert', default=False),
        make_option('--users', action='store_true', dest='users', default=False),
        make_option('--flags', action='store_true', dest='flags', default=False),
        make_option('--data', action='store_true', dest='data', default=False),
        make_option('--all', action='store_true', dest='all', default=False),
    )

    def handle(self, *args, **options):

        from_project = Project.objects.get(project_id=options.get('from'))
        to_project = Project.objects.get(project_id=options.get('to'))

        upsert = options.get('upsert')
        users = options.get('users')
        flags = options.get('flags')
        data = options.get('data')
        if options.get('all'):
            upsert = True
            users = True
            flags = True

        copy_project(from_project, to_project, upsert=upsert, users=users, flags=flags, data=data)
