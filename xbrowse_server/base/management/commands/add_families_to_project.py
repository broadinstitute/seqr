from optparse import make_option

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project
from xbrowse_server import sample_management


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--fam-file')
        parser.add_argument('project_id')

    def handle(self, *args, **options):

        project = Project.objects.get(project_id=options.get('project_id'))
        fam_file = open(options.get('fam_file'))
        sample_management.update_project_from_fam(project, fam_file)
