import logging
from django.core.management.base import BaseCommand

from seqr.models import RnaSeqTpm, Sample
from seqr.views.utils.file_utils import parse_file
from seqr.views.utils.dataset_utils import load_rna_seq_tpm

logger = logging.getLogger(__name__)

TISSUE_TYPE_MAP = {
    'whole_blood': 'WB',
    'fibroblasts': 'F',
    'muscle': 'M',
    'lymphocytes': 'L',
}

REVERSE_TISSUE_TYPE = {v: k for k, v in TISSUE_TYPE_MAP.items()}


class Command(BaseCommand):
    help = 'Load RNA-Seq TPM data'

    def add_arguments(self, parser):
        parser.add_argument('input_file', help='tsv file with TPM data')
        parser.add_argument('--mapping-file', help='optional file to map sample IDs to seqr individual IDs')
        parser.add_argument('--ignore-extra-samples', action='store_true', help='whether to suppress errors about extra samples')

    def handle(self, *args, **options):
        mapping_file = None
        if options['mapping_file']:
            with open(options['mapping_file']) as f:
                mapping_file = parse_file(options['mapping_file'], f)

        samples_to_load, _, _ = load_rna_seq_tpm(
            options['input_file'], mapping_file=mapping_file, ignore_extra_samples=options['ignore_extra_samples'])

        sample_id_map = {
            s['guid']: s for s in Sample.objects.filter(guid__in=samples_to_load).values('guid', 'id', 'sample_id')
        }
        for sample_guid, data_by_gene in samples_to_load.items():
            sample_data = sample_id_map[sample_guid]
            models = RnaSeqTpm.objects.bulk_create(
                [RnaSeqTpm(sample_id=sample_data['id'], **data) for data in data_by_gene.values()], batch_size=1000)
            logger.info(f'create {len(models)} RnaSeqTpm for {sample_data["sample_id"]}')

        logger.info('DONE')


