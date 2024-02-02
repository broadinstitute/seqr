from django.core.management.base import BaseCommand
import logging

from seqr.models import RnaSeqOutlier, Sample
from seqr.views.utils.dataset_utils import load_rna_seq_outlier
from seqr.views.utils.file_utils import parse_file

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Load RNA-Seq Outlier data'

    def add_arguments(self, parser):
        parser.add_argument('input_file')
        parser.add_argument('--mapping-file')
        parser.add_argument('--ignore-extra-samples', action='store_true')

    def handle(self, *args, **options):
        mapping_file = None
        if options['mapping_file']:
            with open(options['mapping_file']) as f:
                mapping_file = parse_file(options['mapping_file'], f)

        sample_guids, _, _ = load_rna_seq_outlier(
            options['input_file'], self._save_sample_data, lambda *args: {}, create_models_before_save=True,
            mapping_file=mapping_file, ignore_extra_samples=options['ignore_extra_samples'])

        Sample.bulk_update(user=None, update_json={'is_active': True}, guid__in=sample_guids)

    @staticmethod
    def _save_sample_data(sample_guid, data_by_gene):
        sample = Sample.objects.get(guid=sample_guid)
        models = RnaSeqOutlier.objects.bulk_create(
            [RnaSeqOutlier(sample=sample, **data) for data in data_by_gene.values()])
        logger.info(f'create {len(models)} RnaSeqOutliers for {sample.sample_id}')



