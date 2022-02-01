from collections import defaultdict
from django.core.management.base import BaseCommand
import logging

from seqr.models import RnaSeqTpm
from seqr.views.apis.data_manager_api import load_rna_seq
from seqr.views.utils.file_utils import parse_file

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Load RNA-Seq TPM data'

    def add_arguments(self, parser):
        parser.add_argument('input_file')
        parser.add_argument('mapping_file')
        parser.add_argument('--ignore-extra-samples', action='store_true')

    def handle(self, *args, **options):

        sample_id_to_individual_id = {}
        sample_id_to_tissue_type = {}
        individual_samples = defaultdict(list)
        with open(options['mapping_file']) as f:
            mapping_file = parse_file(options['mapping_file'], f)
            header = mapping_file[0]
            header_indices = {col: i for i, col in enumerate(header)}
            missing_cols = ', '.join([col for col in ['sample_id', 'imputed tissue', 'indiv (seqr)'] if col not in header_indices])
            if missing_cols:
                raise ValueError(f'Invalid file: missing column(s) {missing_cols}')
            for row in mapping_file[1:]:
                sample_id = row[header_indices['sample_id']]
                indiv_id = row[header_indices['indiv (seqr)']]
                tissue_type = row[header_indices['imputed tissue']]
                if indiv_id:
                    sample_id_to_individual_id[sample_id] = indiv_id
                    individual_samples[indiv_id].append(sample_id)
                if tissue_type:
                    sample_id_to_tissue_type[sample_id] = tissue_type

        multi_mapped_samples = set()
        for sample_ids in individual_samples.values():
            if len(sample_ids) > 1:
                multi_mapped_samples.update(sample_ids)

        def _validate_header(header):
            if 'gene_id' not in header:
                raise ValueError('Invalid file: missing column gene_id')
            header_sample_ids = [s for s in header if s != 'gene_id' and not s.startswith('GTEX')]

            multi_samples = {s for s in header_sample_ids if s in multi_mapped_samples}
            if multi_samples:
                dup_indiviudal_samples = {}
                for sample in multi_samples:
                    indiv_id = sample_id_to_individual_id[sample]
                    if indiv_id not in dup_indiviudal_samples:
                        indiv_samples = [s for s in individual_samples[indiv_id] if s in multi_samples]
                        if len(indiv_samples) > 1:
                            dup_indiviudal_samples[indiv_id] = indiv_samples

                if dup_indiviudal_samples:
                    message = ', '.join([f'{indiv_id} ({", ".join(samples)})' for indiv_id, samples in dup_indiviudal_samples.items()])
                    raise ValueError(f'Unable to load data for the following individuals with multiple samples: {message}')

            no_tissue_samples = ', '.join([s for s in header_sample_ids if s not in sample_id_to_tissue_type])
            if no_tissue_samples:
                raise ValueError(
                    f'Unable to load data for the following samples with no tissue type: {no_tissue_samples}')


        def _parse_row(row):
            raise NotImplementedError

        load_rna_seq(
            RnaSeqTpm, options['input_file'], user=None, sample_id_to_individual_id_mapping=sample_id_to_individual_id,
            ignore_extra_samples=options['ignore_extra_samples'], parse_row=_parse_row, validate_header=_validate_header)
        #
        # for sample, data_by_gene in samples_to_load.items():
        #     models = RnaSeqOutlier.objects.bulk_create(
        #         [RnaSeqOutlier(sample=sample, **data) for data in data_by_gene.values()])
        #     logger.info(f'create {len(models)} RnaSeqOutliers for {sample.sample_id}')


