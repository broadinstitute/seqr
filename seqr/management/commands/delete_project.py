from django.core.management.base import BaseCommand, CommandError
from seqr.models import Project
from django.core.exceptions import ObjectDoesNotExist

from seqr.views.apis.project_api import delete_project


class Command(BaseCommand):
    help = 'Delete project.'

    def add_arguments(self, parser):
        parser.add_argument('project_id', help="Project id")

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        print("Deleting project: %s" % project_id)
        try:
            project = Project.objects.get(guid=project_id)
        except ObjectDoesNotExist:
            raise CommandError("Project %s not found." % project_id)

        delete_project(project)

        print("Deleted %s" % project_id)


