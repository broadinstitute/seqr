from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from xbrowse_server.base.models import Project


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+')

    def handle(self, *args, **options):

        project = Project.objects.get(project_id=args[0])
        level = args[1]
        if level not in ['manager', 'collaborator']:
            print "Invalid level"
            return
        for username in args[2:]:
            user = User.objects.get(username=username)
            if level == 'manager': 
                project.set_as_manager(user)
            elif level == 'collaborator': 
                project.set_as_collaborator(user)
