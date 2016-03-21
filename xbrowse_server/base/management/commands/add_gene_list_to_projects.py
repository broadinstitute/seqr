from django.core.management.base import BaseCommand

from xbrowse_server.gene_lists.models import GeneList
from xbrowse_server.base.models import Project, ProjectGeneList


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        gene_list_slug = args[0]
        gene_list = GeneList.objects.get(slug=gene_list_slug)
        for project_id in args[1:]:
            project = Project.objects.get(project_id=project_id)
            ProjectGeneList.objects.create(project=project, gene_list=gene_list)