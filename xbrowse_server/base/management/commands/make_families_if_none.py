from django.core.management.base import BaseCommand
from xbrowse_server import sample_management
from xbrowse_server.base.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        project_id = args[0]
        project = Project.objects.get(project_id=project_id)
        for individual in project.get_individuals():
            if individual.family is None:
                sample_management.set_family_id_for_individual(individual, individual.indiv_id)
