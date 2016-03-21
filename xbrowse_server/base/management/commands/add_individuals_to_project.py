from optparse import make_option
import gzip
import sys
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff


class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

        parser.add_argument('--sample-list',
                    dest='sample-list',
                    default=False,
                    help='A sample list to gather patient information from.')
        parser.add_argument('--vcf',
                    dest='vcf',
                    help='A VCF file to gather patient information from.'
                    )
        parser.add_argument('--ped',
                    dest='ped',
                    help='A PED file to gather patient information from (PREFERRED due to richer information set).'
                    )


    def handle(self, *args, **options):

        if len(args)==0 or options['vcf'] is None and options['ped'] is None:
          print '\n\nPlease enter a VCF file (--vcf), OR IDEALLY A PED file (--ped), and a project ID (first positional argument).'
          print 'For example: python manage.py add_individuals_to_project  myProjectId --ped myPed.ped\n'
          print 'If you also wish to create patients in phenotips, please use the --create_phenotips_patients\n'
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
            sample_management.add_indiv_ids_to_project(project, indiv_id_list)


        if options.get('ped'):
            fam_file = open(options.get('ped'))
            individual_details = sample_management.update_project_from_fam(project, fam_file)
            for j in individual_details:
                print("Adding %s: %s" % (j['indiv_id'], j))

    #given a list of individuals add them to phenotips
    def __add_individuals_to_phenotips(self,individuals):
      '''given a list of individuals add them to phenotips '''
      for individual in  individuals:
        print individual
        
    
