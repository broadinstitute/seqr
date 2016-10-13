from django.utils.text import slugify
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from xbrowse2.models import Project
from django.utils import timezone
from django.db.models.Model import DoesNotExist

class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-i', '--project-id', help="Project id", required=True)

    def handle(self, *args, **options):
        project_id = options.get('project_id')

        try:
            proj = Project.objects.get(id=slugify(project_id))
        except DoesNotExist:
            raise CommandError("Project %s not found." % project_id)

        proj.delete()

        print("Deleted %s!" % project_id)
        #proj.user_permissions.add()

