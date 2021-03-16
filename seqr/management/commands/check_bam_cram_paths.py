from django.core.management.base import BaseCommand

from seqr.models import IgvSample
from seqr.utils.file_utils import does_file_exist

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        samples = IgvSample.objects.filter(
            individual__family__project__name__in=args,
        ).prefetch_related('individual', 'individual__family')

        failed = []
        for sample in samples:
            if not does_file_exist(sample.file_path):
                individual_id = sample.individual.individual_id
                failed.append(individual_id)
                logger.info('Individual: {} file not found: {}'.format(individual_id, sample.file_path))

        logger.info('---- DONE ----')
        logger.info('Checked {} samples'.format(len(samples)))
        logger.info('{} failed samples: {}'.format(len(failed), ', '.join(failed)))
