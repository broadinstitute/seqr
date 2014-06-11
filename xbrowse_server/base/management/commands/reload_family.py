from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.models import Project, Family, Individual

from xbrowse import fam_stuff

import os

import tasks

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--project-id'),
        make_option('--family-id'),
        make_option('--no-async', action="store_true", dest='no_async'),
    )

    def handle(self, *args, **options):

        if not options.get('project_id'):
            raise Exception

        if 'project_id' in options and not options.get('family_id'):
            project = Project.objects.get(project_id=options.get('project_id'))
            if options.get('no_async'):
                tasks.reload_project_variants(project.project_id)
            else:
                tasks.reload_project_variants.delay(project.project_id)

        if 'project_id' in options and options.get('family_id'):
            if options.get('no_async'):
                tasks.reload_family_variants(options.get('project_id'), options.get('family_id'))
            else:
                tasks.reload_family_variants.delay(options.get('project_id'), options.get('family_id'))

