from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.models import Project, Family, Individual
from django.core.exceptions import ObjectDoesNotExist
from xbrowse import fam_stuff

import os

import tasks


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-p', '--project-id'),
        make_option('-d', '--coverage-file-dir'),
    )

    def handle(self, *args, **options):

        project = Project.objects.get(project_id=options.get('project_id'))
        files = os.listdir(options.get('coverage_file_dir'))
        full_path_dir = os.path.abspath(options.get('coverage_file_dir'))
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
