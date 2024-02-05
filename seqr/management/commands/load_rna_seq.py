import logging
from django.core.management.base import BaseCommand

from seqr.models import Sample
from seqr.views.utils.file_utils import parse_file
from seqr.views.utils.dataset_utils import load_rna_seq, RNA_DATA_TYPE_CONFIGS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load RNA-Seq data'

    def add_arguments(self, parser):
        parser.add_argument('data_type', help='RNA data type', choices=sorted(RNA_DATA_TYPE_CONFIGS.keys()))
        parser.add_argument('input_file', help='tsv file with RNA data')
        parser.add_argument('--mapping-file', help='optional file to map sample IDs to seqr individual IDs')
        parser.add_argument('--ignore-extra-samples', action='store_true', help='whether to suppress errors about extra samples')

    def handle(self, *args, **options):
        mapping_file = None
        if options['mapping_file']:
            with open(options['mapping_file']) as f:
                mapping_file = parse_file(options['mapping_file'], f)

        data_type = options['data_type']
        self.model_cls = RNA_DATA_TYPE_CONFIGS[data_type]['model_class']

        sample_guids, _, _ = load_rna_seq(
            data_type, options['input_file'], self._save_sample_data, lambda *args: {}, create_models_before_save=True,
            mapping_file=mapping_file, ignore_extra_samples=options['ignore_extra_samples'])

        Sample.bulk_update(user=None, update_json={'is_active': True}, guid__in=sample_guids)

        logger.info('DONE')

    def _save_sample_data(self, sample_guid, data_by_gene):
        sample = Sample.objects.get(guid=sample_guid)
        models = self.model_cls.objects.bulk_create(
            [self.model_cls(sample=sample, **data) for data in data_by_gene.values()], batch_size=1000)
        logger.info(f'create {len(models)} RnaSeqTpm for {sample.sample_id}')
