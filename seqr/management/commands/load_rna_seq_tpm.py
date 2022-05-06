import logging
from django.core.management.base import BaseCommand

from seqr.models import RnaSeqTpm
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
        parser.add_argument('input_file')
        parser.add_argument('--mapping-file')
        parser.add_argument('--ignore-extra-samples', action='store_true')

    def handle(self, *args, **options):
        mapping_file = None
        if options['mapping_file']:
            with open(options['mapping_file']) as f:
                mapping_file = parse_file(options['mapping_file'], f)

        sample_id_to_tissue_type = {}
        samples_to_load, _, _ = load_rna_seq_tpm(
            options['input_file'], sample_id_to_tissue_type, mapping_file=mapping_file,
            ignore_extra_samples=options['ignore_extra_samples'])

        invalid_tissues = {}
        for sample, data_by_gene in samples_to_load.items():
            tissue_type = TISSUE_TYPE_MAP[sample_id_to_tissue_type[sample.sample_id]]
            if not sample.tissue_type:
                sample.tissue_type = tissue_type
                sample.save()
            elif sample.tissue_type != tissue_type:
                invalid_tissues[sample] = tissue_type
                continue

            models = RnaSeqTpm.objects.bulk_create(
                [RnaSeqTpm(sample=sample, **data) for data in data_by_gene.values()], batch_size=1000)
            logger.info(f'create {len(models)} RnaSeqTpm for {sample.sample_id}')

        if invalid_tissues:
            message = ', '.join([
                f'{sample.sample_id} ({REVERSE_TISSUE_TYPE[expected_tissue]} to {REVERSE_TISSUE_TYPE[sample.tissue_type]})'
                for sample, expected_tissue in invalid_tissues.items()])
            logger.warning(f'Skipped data loading for the following {len(invalid_tissues)} samples due to mismatched tissue type: {message}')

        logger.info('DONE')


