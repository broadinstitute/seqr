import logging
from django.core.management.base import BaseCommand

from seqr.models import RnaSeqTpm
from seqr.views.utils.file_utils import parse_file
from seqr.views.apis.data_manager_api import load_rna_seq, load_mapping_file_content

from seqr.management.commands.load_rna_seq_tpm import TISSUE_TYPE_MAP, REVERSE_TISSUE_TYPE, GENE_ID_COL

logger = logging.getLogger(__name__)

SAMPLE_ID_COL = 'sample_id'
TPM_COL = 'TPM'
TISSUE_COL = 'tissue'
HEADER_COLS = [SAMPLE_ID_COL, GENE_ID_COL, TPM_COL, TISSUE_COL]

class Command(BaseCommand):
    help = 'Load RNA-Seq TPM data'

    def add_arguments(self, parser):
        parser.add_argument('input_file')
        parser.add_argument('--mapping-file')
        parser.add_argument('--ignore-extra-samples', action='store_true')

    def _validate_header(self, header):
        missing_cols = [col for col in HEADER_COLS if col not in header]
        if missing_cols:
            raise ValueError(f'Invalid file: missing columns {", ".join(missing_cols)}')

    def _parse_row(self, row):
        sample_id = row[SAMPLE_ID_COL]
        if row[TPM_COL] != '0.0' and not sample_id.startswith('GTEX'):
            prev_tissue = self.sample_id_to_tissue_type.get(sample_id)
            tissue = row[TISSUE_COL]
            if not tissue:
                raise ValueError(f'Sample {sample_id} has no tissue type')
            if prev_tissue and prev_tissue != tissue:
                raise ValueError(f'Mismatched tissue types for sample {sample_id}: {prev_tissue}, {tissue}')
            self.sample_id_to_tissue_type[sample_id] = tissue

            yield sample_id, {GENE_ID_COL: row[GENE_ID_COL], 'tpm': row[TPM_COL]}

    def handle(self, *args, **options):
        self.sample_id_to_tissue_type = {}

        sample_id_to_individual_id_mapping = None
        if options['mapping_file']:
            with open(options['mapping_file']) as f:
                mapping_file = parse_file(options['mapping_file'], f)
                sample_id_to_individual_id_mapping = load_mapping_file_content(mapping_file)

        samples_to_load, _, _ = load_rna_seq(
            RnaSeqTpm, options['input_file'], user=None, sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
            ignore_extra_samples=options['ignore_extra_samples'], parse_row=self._parse_row, validate_header=self._validate_header)

        invalid_tissues = {}
        for sample, data_by_gene in samples_to_load.items():
            tissue_type = TISSUE_TYPE_MAP[self.sample_id_to_tissue_type[sample.sample_id]]
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


