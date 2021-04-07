from django.core.management.base import BaseCommand

from seqr.models import IgvSample
from seqr.utils.file_utils import does_file_exist

import collections
import logging
import tqdm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Checks all gs:// bam or cram paths and, if a file no longer exists, deletes the path from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d',
            '--dry-run',
            action="store_true",
            help='Only print missing paths without updating the database',
        )
        parser.add_argument('args', nargs='*', help='only check paths in these project name(s)')

    def handle(self, *args, **options):
        samples = (IgvSample.objects.filter(
            individual__family__project__name__in=args
        ) if args else IgvSample.objects.all()).filter(
            file_path__startswith='gs://'
        ).prefetch_related('individual', 'individual__family__project')

        missing_counter = collections.defaultdict(int)
        guids_of_samples_with_missing_file = set()
        for sample in tqdm.tqdm(samples, unit=" samples"):
            if not does_file_exist(sample.file_path):
                individual_id = sample.individual.individual_id
                project = sample.individual.family.project.name
                missing_counter[project] += 1
                logger.info('Individual: {}  file not found: {}'.format(individual_id, sample.file_path))
                if not options.get('dry_run'):
                    guids_of_samples_with_missing_file.add(sample.guid)

        if len(guids_of_samples_with_missing_file) > 0:
            IgvSample.bulk_update(user=None, update_json={'file_path': ''}, guid__in=guids_of_samples_with_missing_file)

        logger.info('---- DONE ----')
        logger.info('Checked {} samples'.format(len(samples)))
        if missing_counter:
            logger.info('{} files not found:'.format(sum(missing_counter.values())))
            for project_name, c in sorted(missing_counter.items(), key=lambda t: -t[1]):
                logger.info('   {} in {}'.format(c, project_name))
