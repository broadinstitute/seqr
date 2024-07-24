import logging
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import F

from seqr.models import RnaSample
from seqr.views.utils.file_utils import parse_file
from seqr.views.utils.dataset_utils import load_rna_seq, post_process_rna_data, RNA_DATA_TYPE_CONFIGS
from seqr.views.utils.json_to_orm_utils import update_model_from_json

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
        config = RNA_DATA_TYPE_CONFIGS[data_type]
        model_cls = config['model_class']

        sample_data_by_key = defaultdict(list)

        def _save_sample_data(sample_key, row):
            sample_data_by_key[sample_key].append(row)

        possible_sample_guids_to_keys, _, _ = load_rna_seq(
            data_type, options['input_file'], _save_sample_data,
            mapping_file=mapping_file, ignore_extra_samples=options['ignore_extra_samples'])

        sample_models_by_guid = {
            s.guid: s for s in RnaSample.objects.filter(guid__in=possible_sample_guids_to_keys).annotate(sample_id=F('individual__individual_id'))
        }
        errors = []
        sample_guids = []
        for sample_guid in possible_sample_guids_to_keys:
            sample_key = possible_sample_guids_to_keys[sample_guid]
            data_rows, error = post_process_rna_data(sample_guid, sample_data_by_key[sample_key], **config.get('post_process_kwargs', {}))
            if error:
                errors.append(error)
                continue

            sample_guids.append(sample_guid)
            sample_model = sample_models_by_guid[sample_guid]
            models = model_cls.objects.bulk_create(
                [model_cls(sample_id=sample_model.id, **data) for data in data_rows], batch_size=1000)
            logger.info(f'create {len(models)} {model_cls.__name__} for {sample_model.sample_id}')
            update_model_from_json(sample_model, {'is_active': True}, user=None)

        for error in errors:
            logger.info(error)

        logger.info('DONE')
