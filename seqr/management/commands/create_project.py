from django.utils.text import slugify
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from xbrowse2.models import Project
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--username', help="Username of project owner", required=True)
        parser.add_argument('-i', '--project-id', help="Project id", required=True)
        parser.add_argument('-n', '--project-name', help="Project name", required=True)
        parser.add_argument('-d', '--description', help="Project description", default="")
        parser.add_argument('-p', '--is-public', help="Whether to mark the project as public", action="store_true")

    def handle(self, *args, **options):
        username = options.get('username')
        try:
            user = User.objects.get(username=username)
        except:
            raise CommandError("Username %s not found." % username)

        project_id = options.get('project_id')
        project_name = options.get('project_name')
        description = options.get('description')
        is_public = options.get('is-public')

        proj = Project.objects.create(id=slugify(project_id),
                               name=project_name,
                               description=description,

                               created_by=user,
                               created_date=timezone.now(),
                               is_public=is_public or False,
                               version = 1)

        print("Created %s!" % project_id)
