from optparse import make_option

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project
from xbrowse_server import sample_management


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

        parser.add_argument('--project-id')
        parser.add_argument('--cohort-id')
        parser.add_argument('--samples-file')

    def handle(self, *args, **options):

        for k in ['project_id', 'cohort_id', 'samples_file']:
            if k not in options:
                raise Exception

        if not Project.objects.filter(project_id=options.get('project_id')).exists():
            raise Exception

        project = Project.objects.get(project_id=options.get('project_id'))

        indiv_id_list = []
        for line in open(options.get('samples_file')):
            if line.strip() == "" or line.startswith('#'):
                continue
            indiv_id_list.append(line.strip())

        sample_management.add_indiv_ids_to_project(project, indiv_id_list)
        sample_management.add_cohort(project, options.get('cohort_id'), indiv_id_list)
