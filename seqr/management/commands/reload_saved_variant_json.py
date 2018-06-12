import json
import logging
from django.core.management.base import BaseCommand
from tqdm import tqdm

from seqr.models import Project, SavedVariant
from seqr.utils.model_sync_utils import retrieve_saved_variants_json

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

            saved_variants = SavedVariant.objects.filter(project=project, family__isnull=False).select_related('family')
            saved_variants_map = {(v.xpos_start, v.ref, v.alt, v.family.family_id): v for v in saved_variants}

            try:
                variants_json = retrieve_saved_variants_json(project, saved_variants_map.keys())
            except Exception as e:
                logger.error('Error in project {0}: {1}'.format(project.name, e))
                error[project.name] = e
                continue

            for var in variants_json:
                saved_variant = saved_variants_map[(var['xpos'], var['ref'], var['alt'], var['extras']['family_id'])]
                saved_variant.saved_variant_json = json.dumps(var)
                saved_variant.save()
            success[project.name] = len(variants_json)
            logger.info('Updated {0} variants for project {1}'.format(len(variants_json), project.name))

        logger.info("Done")
        logger.info("Summary: ")
        for k, v in success.items():
            if v > 0:
                logger.info("  {0}: Updated {1} variants".format(k, v))
        if len(error):
            logger.info("{0} failed projects".format(len(error)))
        for k, v in error.items():
            logger.info("  {0}: {1}".format(k, v))

