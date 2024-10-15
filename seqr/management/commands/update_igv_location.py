from django.core.management.base import BaseCommand, CommandError
import logging
from tqdm import tqdm

from seqr.models import IgvSample

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('old_prefix')
        parser.add_argument('new_prefix')

    def handle(self, *args, **options):
        old_prefix = options['old_prefix']
        new_prefix = options['new_prefix']
        igv_samples = IgvSample.objects.filter(file_path__startswith=old_prefix)
        if not igv_samples:
            raise CommandError(f'No IGV samples found with file prefix "{old_prefix}"')
        logger.info(f'Updating {len(igv_samples)} IGV samples')
        for sample in tqdm(igv_samples):
            sample.file_path = sample.file_path.replace(old_prefix, new_prefix)
        IgvSample.objects.bulk_update(igv_samples, ['file_path'], batch_size=10000)
        logger.info('Done')
