from django.core.management.base import BaseCommand
import logging

from seqr.models import RnaSeqOutlier
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

        samples_to_load, _, _ = load_rna_seq_outlier(options['input_file'], mapping_file=mapping_file, ignore_extra_samples=options['ignore_extra_samples'])

        for sample, data_by_gene in samples_to_load.items():
            models = RnaSeqOutlier.objects.bulk_create(
                [RnaSeqOutlier(sample=sample, **data) for data in data_by_gene.values()])
            logger.info(f'create {len(models)} RnaSeqOutliers for {sample.sample_id}')


