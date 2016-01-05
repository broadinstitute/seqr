from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
import sys
from xbrowse_server.phenotips.utilities import create_user_in_phenotips
from django.conf import settings

class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args)<2 or not args[0] or not args[1]:
          print '\n\n'
          print 'Adds a project to Phenotips.\n'
          print 'Please provide a project ID and a project name as the first two arguments. If project name has spaces, please remember to enclose in double quotes'
          print 'example: python manage.py 1kg "1000 Genomes Project"\n'
          sys.exit()
        project_id = args[0]
        project_name = args[1]
        if "." in project_id:
            sys.exit("ERROR: A '.' in the project ID is not supported")
        print 'Adding project to phenotips',project_id,'....'
        create_user_in_phenotips(project_id,project_name)
      

