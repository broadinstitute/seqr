from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
import sys
from django.conf import settings

class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args)<1 or not args[0]:
          print '\n\n'
          print 'Creates a project in xBrowse.\n'
          print 'Please provide a project ID as an argument. Optionally, provide a more human-readable project name as a second argument. '
          print 'Example: python manage.py add_project 1kg\n'
          sys.exit()
        project_id = args[0]
        if "." in project_id:
            sys.exit("ERROR: A '.' in the project ID is not supported")

        if Project.objects.filter(project_id=project_id).exists():
            print '\nSorry, I am unable to create that project since it exists already\n'
            sys.exit()

        project_name = None
        if len(args) > 1:
            project_name = args[1]

        print('Creating project %(project_id)s' % locals())

        try:
            Project.objects.create(project_id=project_id, project_name=project_name)
        except Exception as e:
          print('\nError creating project:', e, '\n')
          sys.exit()
