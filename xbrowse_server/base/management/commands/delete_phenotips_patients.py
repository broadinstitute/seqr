'''
  Deletes a patient record in PhenoTips or ALL PATIENTS in a project. 
  
  Note: PhenoTips doesn't have a notion of Project. We associate "Project"
  to all patients belonging to the same user (which represents a project
  in RDAP.
'''

from optparse import make_option
from django.core.management.base import BaseCommand
from xbrowse_server.phenotips.admin_utilities import fetch_project_phenotips_patient_ids
from xbrowse_server.phenotips.admin_utilities import delete_these_phenotips_patient_ids
from xbrowse_server.phenotips.admin_utilities import delete_phenotips_patient_id
import sys


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--patient_id',
                    dest='id',
                    help='An ID of a PhenoTips patient (ex: P0000138).'
                    ),
        make_option('--as_admin',
                    dest='as_admin',
                    help='Login as Admin to PhenoTips (not recommended).'
                    ),
    )

    def handle(self, *args, **options):
      '''
        Handles deleting patients from Phenotips.
      '''
      
      if len(args)==0 and options['id'] is None:
        print '\n\nDelete patients from Phenotips.\n'
        print 'Please enter a project ID  to DELETE ALL PATIENTS BELONGING TO IT IN PHENOTIPS or a single patient ID (ex: P0000138) via the --patient_id option.'
        print
        sys.exit()
      try:
        print options['as_admin']
        project_id = args[0]
        if not options['id']:
          patient_ids = fetch_project_phenotips_patient_ids(project_id)
          print("Will delete %d patient ids: %s" % (len(patient_ids), ", ".join(patient_ids)))
          i = raw_input('Continue? [Y/n] ') 
          if i.lower() == 'y':
              delete_these_phenotips_patient_ids(project_id,patient_ids)
          else:
              print "Cancelled"
        else:
          delete_phenotips_patient_id(project_id,options['id'])
      except Exception as e:
        print e
