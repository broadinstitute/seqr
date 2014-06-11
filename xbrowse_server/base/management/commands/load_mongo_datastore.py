from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project
import tasks

class Command(BaseCommand):
    """
    Reload all variants in the mongo datastore
    """
    def handle(self, *args, **options):
        for project in Project.objects.all():
            tasks.reload_project_variants.delay(project.project_id)