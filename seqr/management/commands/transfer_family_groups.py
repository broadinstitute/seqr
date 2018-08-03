import collections
import logging
from tqdm import tqdm

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import FamilyGroup
from xbrowse_server.base.model_utils import _create_seqr_model, find_matching_seqr_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer family groups to the new seqr schema'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """For each xbrowse_server.base.models.FamilyGroup, create a corresponding seqr.models.AnalysisGroup
        """
        counters = collections.defaultdict(int)
        errors = []
        for source_group in tqdm(FamilyGroup.objects.filter(seqr_analysis_group__isnull=True), unit=" family groups"):
            counters['FamilyGroups processed'] += 1
            analysis_group = _create_seqr_model(
                source_group,
                name=source_group.name,
                description=source_group.description,
                project=source_group.project,
            )

            if analysis_group:
                analysis_group.families.add(*[find_matching_seqr_model(family) for family in source_group.families.all()])
                counters['AnalysisGroups created'] += 1
            else:
                counters['Errors'] += 1
                errors.append('Error: unable to transfer "{}" (Project: "{}")'.format(source_group.name, source_group.project.project_name))

        logger.info("Done")
        logger.info("Stats: ")
        for k, v in counters.items():
            logger.info("  %s: %s" % (k, v))
        for error in errors:
            logger.info(error)
