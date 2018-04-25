from django.core.management.base import BaseCommand

from xbrowse_server.base.model_utils import create_xbrowse_model
from xbrowse_server.base.models import Project
import sys
from django.utils import timezone

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("project_id")
        parser.add_argument("project_name", nargs="?")

    def handle(self, *args, **options):
        if 'project_id' not in options:
            print '\n'
            print 'Creates a project in Seqr.\n'
            print 'Please provide a project ID as an argument. Optionally, provide a more human-readable project name as a second argument. '
            print 'Example: python manage.py add_project 1kg\n'
            sys.exit()

        project_id = options['project_id']
        if "." in project_id:
            sys.exit("ERROR: A '.' in the project ID is not supported")

        if Project.objects.filter(project_id=project_id).exists():
            print '\nSorry, I am unable to create that project since it exists already\n'
            sys.exit()
        
        project_name = options.get('project_name') or project_id
        print('Creating project with id "%(project_id)s" and name "%(project_name)s"' % locals())

        try:
            create_xbrowse_model(Project, project_id=project_id, project_name=project_name, created_date=timezone.now())
        except Exception as e:
            print('\nError creating project:', e, '\n')
            sys.exit()
