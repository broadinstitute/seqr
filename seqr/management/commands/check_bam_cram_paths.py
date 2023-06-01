from django.core.management.base import BaseCommand

import collections
import logging
import tqdm

from seqr.models import IgvSample
from seqr.utils import communication_utils
from seqr.utils.file_utils import does_file_exist
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

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
        logger.info('checking bam/cram paths')

        samples = (IgvSample.objects.filter(
            individual__family__project__name__in=args
        ) if args else IgvSample.objects.all()).filter(
            file_path__startswith='gs://'
        ).order_by('id').prefetch_related('individual', 'individual__family__project')

        missing_counter = collections.defaultdict(int)
        guids_of_samples_with_missing_file = set()
        project_name_to_missing_paths = collections.defaultdict(list)
        for sample in tqdm.tqdm(samples, unit=" samples"):
            if not does_file_exist(sample.file_path):
                individual_id = sample.individual.individual_id
                project_name = sample.individual.family.project.name
                missing_counter[project_name] += 1
                project_name_to_missing_paths[project_name].append((individual_id, sample.file_path))
                logger.info('Individual: {}  file not found: {}'.format(individual_id, sample.file_path))
                if not options.get('dry_run'):
                    guids_of_samples_with_missing_file.add(sample.guid)

        if len(guids_of_samples_with_missing_file) > 0:
            IgvSample.bulk_delete(user=None, guid__in=guids_of_samples_with_missing_file)

        logger.info('---- DONE ----')
        logger.info('Checked {} samples'.format(len(samples)))
        if missing_counter:
            logger.info('{} files not found:'.format(sum(missing_counter.values())))
            for project_name, c in sorted(missing_counter.items(), key=lambda t: -t[1]):
                logger.info('   {} in {}'.format(c, project_name))

            # post to slack
            if not options.get('dry_run'):
                slack_message = 'Found and removed {} broken bam/cram path(s)\n'.format(sum(missing_counter.values()))
                for project_name, missing_paths_list in project_name_to_missing_paths.items():
                    slack_message += "\nIn project {}:\n".format(project_name)
                    slack_message += "\n".join([
                        "  {}   {}".format(individual_id, path) for individual_id, path in missing_paths_list
                    ])
                communication_utils.safe_post_to_slack(SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, slack_message)
