from optparse import make_option
import gzip
import sys
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff
from xbrowse_server.phenotips.utilities import add_individuals_to_phenotips_from_ped
from xbrowse_server.phenotips.utilities import add_individuals_to_phenotips_from_vcf


class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+')
        parser.add_argument('--vcf',
                    dest='vcf',
                    help='A VCF file to gather patient information from.'
                    )
        parser.add_argument('--ped',
                    dest='ped',
                    help='A PED file to gather patient information from (PREFERRED due to richer information set).'
                    )

    def handle(self, *args, **options):
      '''
        Handles populating Phenotips.
        Currently favors PED file for richer set of information (vs VCF) to create patients
      '''
      
      if len(args)==0 or options['vcf'] is None and options['ped'] is None:
        print '\n\nAdds a series of patients to Phenotips.\n'
        print 'Please enter a VCF file (--vcf), OR IDEALLY A PED file (--ped), and a project ID (first positional argument).'
        print 'For example: python manage.py add_individuals_to_phenotips  myProjectId --ped myPed.ped\n'
        sys.exit()
        
      project_id = args[0]
      project = Project.objects.get(project_id=project_id)
      
      if options.get('vcf') and not os.path.exists(options.get('vcf')):
        print '\n\nError: the VCF file you entered does not exist or is invalid\n\n'
        sys.exit()
      if options.get('ped') and not os.path.exists(options.get('ped')):
        print '\n\nError: the PED file you entered does not exist or is invalid\n\n'
        sys.exit()
      
      indiv_id_list=None
      if options.get('vcf'):
          vcf_path = options.get('vcf')
          if vcf_path.endswith('.gz'):
              vcf = gzip.open(vcf_path)
          else:
              vcf = open(vcf_path)
          indiv_id_list = vcf_stuff.get_ids_from_vcf(vcf)

      individual_details=None
      if options.get('ped'):
          fam_file = open(options.get('ped'))
          individual_details = sample_management.update_project_from_fam(project, fam_file)

      if individual_details is not None:
        add_individuals_to_phenotips_from_ped(individual_details,project_id)
      else:
        if indiv_id_list is not None:
          add_individuals_to_phenotips_from_vcf(indiv_id_list,project_id)
        else:
          print '\n\nWARNING: No information was found in VCF to create patients with\n'
          sys.exit()

            

