from optparse import make_option
import os

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project, VCFFile


class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('project_id')
        parser.add_argument('vcf_path')
        parser.add_argument('--all', action='store_true', dest='clear_all', default=False)

    def handle(self, *args, **options):

        project_id = options['project_id']
        project = Project.objects.get(project_id=project_id)

        if options.get('clear_all'):
            for individual in project.individual_set.all():
                individual.vcf_files.clear()
        else:
            vcf_file_path = os.path.abspath(options['vcf_path'])
            vcf_file = VCFFile.objects.get(file_path=vcf_file_path)
            print("Removing %s from project %s" % (vcf_file_path, project_id))
            for individual in project.individual_set.all():
                individual.vcf_files.remove(vcf_file)
        print("Done")
