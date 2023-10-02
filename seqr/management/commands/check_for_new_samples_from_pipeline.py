from django.core.management.base import BaseCommand, CommandError
import json
import logging
import os

from seqr.models import Family, Sample
from seqr.utils.file_utils import file_iter
from reference_data.models import GENOME_VERSION_LOOKUP

logger = logging.getLogger(__name__)

DATA_TYPES = set(Sample.DATASET_TYPE_LOOKUP.keys())
DATA_TYPES.remove(Sample.DATASET_TYPE_SV_CALLS)
DATA_TYPES.update([
    f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}' for sample_type in [Sample.SAMPLE_TYPE_WES, Sample.SAMPLE_TYPE_WGS]
])


class Command(BaseCommand):
    help = 'Check for newly loaded seqr samples'

    @staticmethod
    def _load_new_samples(genome_version, data_type, version):
        version_summary = f'{genome_version}/{data_type}: {version}'
        metadata_path = f'gs://seqr-datasets/v03/{genome_version}/{data_type}/runs/{version}/metadata.json'
        metadata = json.loads(next(line for line in file_iter(metadata_path)))
        if not metadata.get('projects'):
            raise CommandError(f'Invalid metadata for {version_summary}: {version}')

        family_guids = {family for families in metadata['projects'].values() for family in families}
        families = Family.objects.filter(guid__in=family_guids)
        if len(families) < len(family_guids):
            invalid = family_guids - set(families.values_list('guid', flat=True))
            raise CommandError(f'Invalid families in run metadata {version_summary}: {", ".join(invalid)}')



    def handle(self, *args, **options):
        for genome_version in GENOME_VERSION_LOOKUP.values():
            for data_type in DATA_TYPES:
                version = os.environ.get(f'{genome_version}/{data_type}')
                if not version:
                    continue
                version_summary = f'{genome_version}/{data_type}: {version}'
                if Sample.objects.filter(data_source=version).exists():
                    logger.info(f'Data already loaded for {version_summary}')
                    continue
                logger.info(f'Loading new samples from {version_summary}')
                self._load_new_samples(genome_version, data_type, version)



