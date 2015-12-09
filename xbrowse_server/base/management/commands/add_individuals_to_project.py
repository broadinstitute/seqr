from optparse import make_option
import gzip
import sys
from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff
from xbrowse_server.phenotips.utilities import create_patient_record

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--sample-list'),
        make_option('--vcf'),
        make_option('--ped'),
        make_option('--create_phenotips_patients'),
        make_option('--phenotips_username'),
        make_option('--phenotips_password'),
    )

    def handle(self, *args, **options):
      
        if options['vcf'] is None or options['ped'] is None or len(args)==0:
          print '\n\nPlease enter a VCF file (--vcf), a PED file (--ped), and a project ID (first positional argument)'
          print 'for example: python manage.py add_individuals_to_project  myProjectId  --vcf myVcf.vcf  --ped myPed.ped\n'
          print 'If you also wish to create patients in phenotips, please use the --create_phenotips_patients,--phenotips_username, --phenotips_password to do so. ALL of them are REQUIRED.\n'
          sys.exit()
          
        if options['create_phenotips_patients'] is not None and (options['phenotips_username'] is None or options['phenotips_password'] is None):
          print '\n\nplease note if you use the --create_phenotips_patients option, both --phenotips_username and --phenotips_password options are REQUIRED.\n\n'
          sys.exit()

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
            self.__add_individuals_to_phenotips(indiv_id_list,project_id)
            sample_management.add_indiv_ids_to_project(project, indiv_id_list)

        if options.get('ped'):
            fam_file = open(options.get('ped'))
            sample_management.update_project_from_fam(project, fam_file)


    #given a list of individuals add them to phenotips
    def __add_individuals_to_phenotips(self,individuals,project_id):
      '''given a list of individuals add them to phenotips '''
      for individual in  individuals:        
        create_patient_record(individual,project_id)

        
      