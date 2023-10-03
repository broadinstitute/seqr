from django.core.management.base import BaseCommand, CommandError
import json
import logging
import os

from seqr.models import Family, Sample
from seqr.utils.file_utils import file_iter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check for newly loaded seqr samples'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('version')

    def handle(self, *args, **options):
        path = options['path']
        version = options['version']

        if Sample.objects.filter(data_source=version).exists():
            logger.info(f'Data already loaded for {path}: {version}')
            return

        logger.info(f'Loading new samples from {path}: {version}')
        metadata_path = f'gs://seqr-datasets/v03/{path}/{data_type}/runs/{version}/metadata.json'
        metadata = json.loads(next(line for line in file_iter(metadata_path)))

        families = Family.objects.filter(guid__in=metadata['families'].keys())
        if len(families) < len(metadata['families']):
            invalid = metadata['families'].keys() - set(families.values_list('guid', flat=True))
            raise CommandError(f'Invalid families in run metadata {path}: {version} - {", ".join(invalid)}')
