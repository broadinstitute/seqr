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
        make_option('--create_phenotips_patients',
                    action='store_true',
                    dest='create_phenotips_patients',
                    default=False,
                    help='add this patient to phenotips'),
    )

    def handle(self, *args, **options):
      
        if len(args)==0 or options['vcf'] is None and options['ped'] is None:
          print '\n\nPlease enter a VCF file (--vcf), OR IDEALLY A PED file (--ped), and a project ID (first positional argument).'
          print 'For example: python manage.py add_individuals_to_project  myProjectId --ped myPed.ped\n'
          print 'If you also wish to create patients in phenotips, please use the --create_phenotips_patients\n'
          sys.exit()
          
        project_id = args[0]
        project = Project.objects.get(project_id=project_id)
        indiv_id_list=None

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
            sample_management.add_indiv_ids_to_project(project, indiv_id_list)

        individual_details=None
        if options.get('ped'):
            fam_file = open(options.get('ped'))
            individual_details = sample_management.update_project_from_fam(project, fam_file)

        #add to phenotips
        if options.get('create_phenotips_patients'):
          #Favor PED file rich information VCF file minimum information to create patients
          if individual_details is not None:
            self.__add_individuals_to_phenotips_from_ped(individual_details,project_id)
          else:
            if indiv_id_list is not None:
              self.__add_individuals_to_phenotips_from_vcf(indiv_id_list,project_id)
            else:
              print '\nno information in VCF to create patients with\n'
              sys.exit()
        else:
          print '\n----not adding these patients to local phenotips instance.----\n'
            

    #given a list of individuals add them to phenotips
    def __add_individuals_to_phenotips_from_vcf(self,individuals,project_id):
      '''given a list of individuals add them to phenotips '''
      for individual in  individuals:        
        create_patient_record(individual,project_id)
        
    #given a list of individuals add them to phenotips
    def __add_individuals_to_phenotips_from_ped(self,individual_details,project_id,):
      '''given a list of individuals add them to phenotips '''
      #for now only using gender information from the PED file.
      for individual in  individual_details:
        id=individual['indiv_id']
        if individual['gender'] == 'female':
          gender='F'
        elif individual['gender'] == 'male':
          gender='M'
        else:
          raise ValueError
        extra_details={
                       'gender':gender}
        create_patient_record(id,project_id,extra_details)

        
      