import logging
from collections import defaultdict
from django.core.management.base import BaseCommand

from seqr.models import RnaSeqTpm
from seqr.views.apis.data_manager_api import load_rna_seq
from seqr.views.utils.file_utils import parse_file

logger = logging.getLogger(__name__)

TISSUE_TYPE_MAP = {
    'whole_blood': 'WB',
    'fibroblasts': 'F',
    'muscle': 'M',
    'lymphocytes': 'L',
}

REVERSE_TISSUE_TYPE = {v: k for k, v in TISSUE_TYPE_MAP.items()}

GENE_ID_COL = 'gene_id'

class Command(BaseCommand):
    help = 'Load RNA-Seq TPM data'

    def add_arguments(self, parser):
        parser.add_argument('input_file')
        parser.add_argument('mapping_file')
        parser.add_argument('--ignore-extra-samples', action='store_true')

    def _parse_mapping_file(self, mapping_file_path):
        self.sample_id_to_individual_id = {}
        self.sample_id_to_tissue_type = {}
        self.individual_samples = defaultdict(list)
        with open(mapping_file_path) as f:
            mapping_file = parse_file(mapping_file_path, f)
            header = mapping_file[0]
            header_indices = {col: i for i, col in enumerate(header)}
            missing_cols = ', '.join(
                [col for col in ['sample_id', 'imputed tissue', 'indiv (seqr)'] if col not in header_indices])
            if missing_cols:
                raise ValueError(f'Invalid mapping file: missing column(s) {missing_cols}')
            for row in mapping_file[1:]:
                sample_id = row[header_indices['sample_id']]
                indiv_id = row[header_indices['indiv (seqr)']]
                tissue_type = row[header_indices['imputed tissue']]
                if indiv_id:
                    self.sample_id_to_individual_id[sample_id] = indiv_id
                    self.individual_samples[indiv_id].append(sample_id)
                if tissue_type:
                    self.sample_id_to_tissue_type[sample_id] = tissue_type

        self.multi_mapped_samples = set()
        for sample_ids in self.individual_samples.values():
            if len(sample_ids) > 1:
                self.multi_mapped_samples.update(sample_ids)

    def _validate_header(self, header):
        if GENE_ID_COL not in header:
            raise ValueError('Invalid file: missing column gene_id')
        header_sample_ids = [s for s in header if s != GENE_ID_COL and not s.startswith('GTEX')]

        multi_samples = {s for s in header_sample_ids if s in self.multi_mapped_samples}
        if multi_samples:
            dup_indiviudal_samples = {}
            for sample in multi_samples:
                indiv_id = self.sample_id_to_individual_id[sample]
                if indiv_id not in dup_indiviudal_samples:
                    indiv_samples = [s for s in self.individual_samples[indiv_id] if s in multi_samples]
                    if len(indiv_samples) > 1:
                        dup_indiviudal_samples[indiv_id] = indiv_samples

            if dup_indiviudal_samples:
                message = ', '.join(
                    [f'{indiv_id} ({", ".join(samples)})' for indiv_id, samples in dup_indiviudal_samples.items()])
                raise ValueError(f'Unable to load data for the following individuals with multiple samples: {message}')

        no_tissue_samples = ', '.join([s for s in header_sample_ids if s not in self.sample_id_to_tissue_type])
        if no_tissue_samples:
            raise ValueError(
                f'Unable to load data for the following samples with no tissue type: {no_tissue_samples}')

    @classmethod
    def _parse_row(cls, row):
        gene_id = row.pop(GENE_ID_COL)
        if any(tpm for tpm in row.values() if tpm != '0.0'):
            for sample_id, tpm in row.items():
                if not sample_id.startswith('GTEX'):
                    yield sample_id, {GENE_ID_COL: gene_id, 'tpm': tpm}

    def handle(self, *args, **options):
        self._parse_mapping_file(options['mapping_file'])

        samples_to_load, _, _ = load_rna_seq(
            RnaSeqTpm, options['input_file'], user=None, sample_id_to_individual_id_mapping=self.sample_id_to_individual_id,
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


