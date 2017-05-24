from django.core.management.base import BaseCommand, CommandError
from xbrowse_server.base.models import Project
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Delete project.'

    def add_arguments(self, parser):
        parser.add_argument('project_id', help="Project id")

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        print("Deleting project: %s" % project_id)
        try:
            proj = Project.objects.get(project_id=project_id)
        except ObjectDoesNotExist:
            raise CommandError("Project %s not found." % project_id)

        proj.delete()

        print("Deleted %s!" % project_id)


