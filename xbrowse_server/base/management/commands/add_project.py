from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.models import Project


class Command(BaseCommand):

    def handle(self, *args, **options):
        project_id = args[0]
        if Project.objects.filter(project_id=project_id).exists():
            raise Exception("Project exists :(")
        Project.objects.create(project_id=project_id)