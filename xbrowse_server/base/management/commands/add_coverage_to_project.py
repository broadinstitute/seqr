import os

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):

        project_id = args[0]
        coverage_dir = args[1]

        project = Project.objects.get(project_id=project_id)
        files = os.listdir(coverage_dir)
        full_path_dir = os.path.abspath(coverage_dir)
        for individual in project.individual_set.all():
            indiv_id = individual.indiv_id
            full_path = None
            if '%s.callable.bed.gz' % indiv_id in files:
                full_path = '%s/%s.callable.bed.gz' % (full_path_dir, indiv_id)
            elif '%s.bam.bed.gz' % indiv_id in files: 
                full_path = '%s/%s.bam.bed.gz' % (full_path_dir, indiv_id)
            elif '%s.bed.gz' % indiv_id in files:
                full_path = '%s/%s.bed.gz' % (full_path_dir, indiv_id)
            if full_path: 
                individual.coverage_file = full_path
                individual.save()
