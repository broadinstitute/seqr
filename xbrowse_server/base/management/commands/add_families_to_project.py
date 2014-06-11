from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.models import Project, Family, Individual

from xbrowse import fam_stuff
from xbrowse_server import sample_management

import os

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--project-id'),
        make_option('--fam-file'),
    )

    def handle(self, *args, **options):

        project = Project.objects.get(project_id=options.get('project_id'))
        fam_file = open(options.get('fam_file'))
        sample_management.update_project_from_fam(project, fam_file)
