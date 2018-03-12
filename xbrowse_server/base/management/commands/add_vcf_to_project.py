import os

from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project, Individual, VCFFile
from xbrowse_server import sample_management


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

        parser.add_argument('--indiv-id')
        parser.add_argument('--cohort-id')
        parser.add_argument('--clear', action="store_true", help="Whether to clear any previously-added VCF paths before adding this one")
        parser.add_argument('--load', action="store_true", help="Whether to  also load the VCF data, and not just add record its path in the meta-data tables")

    def handle(self, *args, **options):

        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        vcf_file_path = os.path.abspath(args[1])
        vcf_file = VCFFile.objects.get_or_create(file_path=vcf_file_path)[0]

        if options.get('clear'):
            for individual in project.individual_set.all():
                individual.vcf_files.clear()

        if options.get('indiv_id'):
            individual = Individual.objects.get(
                project=project,
                indiv_id=options.get('indiv_id')
            )
            sample_management.add_vcf_file_to_individual(individual, vcf_file)

        else:
            sample_management.add_vcf_file_to_project(project, vcf_file)

        if options.get('load'):
            print("Loading VCF into project store")
            xbrowse_controls.load_project(project_id, vcf_files=[vcf_file_path])
            print("Loading VCF datastore")
            xbrowse_controls.load_project_datastore(project_id, vcf_files=[vcf_file_path])
