from django.core.management.base import BaseCommand
from optparse import make_option
import os
from xbrowse_server.base.models import Project, Family, VCFFile, Individual
from django.conf import settings
from xbrowse.parsers.vcf_stuff import get_ids_from_vcf_path

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--vcf-file', help='VCF File'),
        make_option('--project-id', help='Project ID slug'),
        )

    def handle(self, *args, **options):

        project = Project.objects.get(project_id=options.get('project_id'))
        vcf_file_path = os.path.abspath(options.get('vcf_file'))
        ids = get_ids_from_vcf_path(vcf_file_path)
        for indiv_id in ids:
            individual = Individual.objects.get_or_create(indiv_id=indiv_id, project=project)[0]

