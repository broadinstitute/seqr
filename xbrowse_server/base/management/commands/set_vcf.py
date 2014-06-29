from optparse import make_option
import os

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project, Individual, VCFFile
from xbrowse_server import sample_management


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--indiv-id'),
        make_option('--cohort-id'),
    )

    def handle(self, *args, **options):

        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        vcf_file_path = os.path.abspath(args[1])
        vcf_file = VCFFile.objects.get_or_create(file_path=vcf_file_path)[0]

        if options.get('indiv_id'):
            individual = Individual.objects.get(
                project=project,
                indiv_id=options.get('indiv_id')
            )
            sample_management.add_vcf_file_to_individual(individual, vcf_file)

        else:
            sample_management.add_vcf_file_to_project(project, vcf_file)
