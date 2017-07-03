import logging

from django.core.management.base import BaseCommand, CommandError

from reference_data.models import GENOME_VERSION_CHOICES
from seqr.views.apis.project_api import create_project

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--description', help="Project description", default="")
        parser.add_argument("-g", "--genome-version", help="Genome version 37 or 38", choices=[c[0] for c in GENOME_VERSION_CHOICES], required=True)
        parser.add_argument('project_name', help="Project name")


    def handle(self, *args, **options):

        project = create_project(
            name=options.get('project_name'),
            description=options.get('description'),
            genome_version=options.get('genome_version'))

        logger.info("Created project %s" % project.guid)
