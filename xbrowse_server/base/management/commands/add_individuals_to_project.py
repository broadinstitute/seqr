from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.models import Project, Family, Individual
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff
import gzip

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--samples-file'),
        make_option('--vcf-file'),
        make_option('--fam-file'),
    )

    def handle(self, *args, **options):

        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        if options.get('samples_file'):
            indiv_id_list = []
            for line in open(options.get('samples_file')):
                if line.strip() == "" or line.startswith('#'):
                    continue
                indiv_id_list.append(line.strip())

            sample_management.add_indiv_ids_to_project(project, indiv_id_list)

        if options.get('vcf_file'):
            vcf_path = options.get('vcf_file')
            if vcf_path.endswith('.gz'):
                vcf = gzip.open(vcf_path)
            else:
                vcf = open(vcf_path)
            indiv_id_list = vcf_stuff.get_ids_from_vcf(vcf)
            sample_management.add_indiv_ids_to_project(project, indiv_id_list)

        if options.get('fam_file'):
            fam_file = open(options.get('fam_file'))
            sample_management.update_project_from_fam(project, fam_file)
