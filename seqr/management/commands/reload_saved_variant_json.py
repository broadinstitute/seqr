import logging
from django.core.management.base import BaseCommand
from tqdm import tqdm

from seqr.models import Project
from seqr.views.utils.variant_utils import update_project_saved_variant_json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('projects', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')

    def handle(self, *args, **options):
        """transfer project"""
        projects_to_process = options['projects']

        if projects_to_process:
            projects = Project.objects.filter(name__in=projects_to_process)
            logging.info("Processing %s projects" % len(projects))
        else:
            projects = Project.objects.filter(deprecated_project_id__isnull=False)
            logging.info("Processing all %s projects" % len(projects))

        success = {}
        error = {}
        for project in tqdm(projects, unit=" projects"):
            logger.info("Project: " + project.name)

            try:
                variants_json = update_project_saved_variant_json(project)
                success[project.name] = len(variants_json)
                logger.info('Updated {0} variants for project {1}'.format(len(variants_json), project.name))
            except Exception as e:
                logger.error('Error in project {0}: {1}'.format(project.name, e))
                error[project.name] = e

        logger.info("Done")
        logger.info("Summary: ")
        for k, v in success.items():
            if v > 0:
                logger.info("  {0}: Updated {1} variants".format(k, v))
        if len(error):
            logger.info("{0} failed projects".format(len(error)))
        for k, v in error.items():
            logger.info("  {0}: {1}".format(k, v))

