import gzip
import sys
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual
from xbrowse.parsers import vcf_stuff, fam_stuff
from xbrowse_server.phenotips.utilities import add_individuals_to_phenotips


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('--vcf', dest='vcf',
                            help='A VCF file to gather patient information from.' )
        parser.add_argument('--ped', dest='ped',
                            help='A PED file to gather patient information from (PREFERRED due to richer information set).' )
        parser.add_argument('--all', dest='all', action="store_true", 
                            help='A PED file to gather patient information from (PREFERRED due to richer information set).' )

    def handle(self, *args, **options):
        """
        Handles populating Phenotips.
        Currently favors PED file for richer set of information (vs VCF) to create patients
        """

        if len(args) == 0 or options['vcf'] is None and options['ped'] is None and options['all'] is None:
            print('\n\nAdds a series of patients to Phenotips.\n')
            print('Please enter a project id (first positional argument) followed by either a PED file (--ped), a VCF file (--vcf), or --all ('
                  'if you just want to create PhenoTips patients for the individuals that already exist in the project)')
            print('For example: python manage.py add_individuals_to_phenotips  myProjectId --ped myPed.ped\n')
            sys.exit()

        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        if options.get('vcf') and not os.path.exists(options.get('vcf')):
            print '\n\nError: the VCF file you entered does not exist or is invalid\n\n'
            sys.exit()
        if options.get('ped') and not os.path.exists(options.get('ped')):
            print '\n\nError: the PED file you entered does not exist or is invalid\n\n'
            sys.exit()

        indiv_id_list = None
        if options.get('vcf'):
            vcf_path = options.get('vcf')
            if vcf_path.endswith('.gz'):
                vcf = gzip.open(vcf_path)
            else:
                vcf = open(vcf_path)
            indiv_id_list = vcf_stuff.get_ids_from_vcf(vcf)
            add_individuals_to_phenotips(project_id, indiv_id_list)
        elif options.get('ped'):
            fam_file = open(options.get('ped'))
            individuals = fam_stuff.get_individuals_from_fam_file(fam_file)
            indiv_id_list = [ind.indiv_id for ind in individuals]

        elif options.get("all"):
            indiv_id_list = [ind.indiv_id for ind in Individual.objects.filter(project=project)]

        # if no vcf or ped file was specified, add all individuals in this projects
        print("Creating phenotips records for new individuals.")
        add_individuals_to_phenotips(project_id, indiv_id_list)
        print("Done.")
