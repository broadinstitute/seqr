from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
import sys
from xbrowse_server.phenotips.utilities import add_new_user_to_phenotips
from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project
from xbrowse_server.phenotips.utilities import get_names_for_user
from django.conf import settings

class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args)<2 or not args[0] or not args[1]:
          print '\n'
          print 'Please provide a project ID as the first argument. '
          print 'Example: python manage.py add_project 1kg\n'
          sys.exit()
        project_id = args[0]
        project_name = args[1]
        if "." in project_id:
            sys.exit("ERROR: A '.' in the project ID is not supported")

        if Project.objects.filter(project_id=project_id).exists():
            print '\nSorry, I am unable to create that project since it exists already\n'
            sys.exit()
        print 'creating project',project_id,'in xBrowse.'
        try:
          Project.objects.create(project_id=project_id)
        except Exception as e:
          print 'Error creating project in xBrowse:',e
          sys.exit()
