from optparse import make_option
import gzip

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--sample-list'),
        make_option('--vcf'),
        make_option('--ped'),
    )

    def handle(self, *args, **options):

        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        if options.get('sample_list'):
            indiv_id_list = []
            for line in open(options.get('sample_list')):
                if line.strip() == "" or line.startswith('#'):
                    continue
                indiv_id_list.append(line.strip())

            sample_management.add_indiv_ids_to_project(project, indiv_id_list)

        if options.get('vcf'):
            vcf_path = options.get('vcf')
            if vcf_path.endswith('.gz'):
                vcf = gzip.open(vcf_path)
            else:
                vcf = open(vcf_path)
            indiv_id_list = vcf_stuff.get_ids_from_vcf(vcf)
            self.__add_individuals_to_phenotips(indiv_id_list)
            sample_management.add_indiv_ids_to_project(project, indiv_id_list)

        if options.get('ped'):
            fam_file = open(options.get('ped'))
            sample_management.update_project_from_fam(project, fam_file)


    #given a list of individuals add them to phenotips
    def __add_individuals_to_phenotips(self,individuals):
      '''given a list of individuals add them to phenotips '''
      print individuals
      