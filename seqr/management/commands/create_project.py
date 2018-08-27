import logging

from django.core.management.base import BaseCommand

from seqr.management.commands.add_individuals import add_individuals_from_pedigree_file
from seqr.views.apis.project_api import create_project

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--description', help="project description")
        parser.add_argument('-p', '--pedigree-file', help="pedigree file")
        parser.add_argument('project_name', help="Project name")

    def handle(self, *args, **options):

        project = create_project(
            name=options.get('project_name'),
            description=options.get('description'))

        if options.get('pedigree_file'):
            add_individuals_from_pedigree_file(project, options.get('pedigree_file'))