import json
import os

from django.core.management.base import BaseCommand, CommandError

from reference_data.models import GENOME_VERSION_LOOKUP, GENOME_VERSION_GRCh38
from seqr.models import Sample, Individual, Family
from seqr.management.commands.check_for_new_samples_from_pipeline import update_individuals_sample_qc, get_pipeline_runs
from seqr.utils.file_utils import file_iter


class Command(BaseCommand):
    help = 'Ingest sample qc data for a particular pipeline run'

    def add_arguments(self, parser):
        parser.add_argument('dataset_type', choices={Sample.DATASET_TYPE_VARIANT_CALLS})
        parser.add_argument('genome_version', choices={GENOME_VERSION_LOOKUP[GENOME_VERSION_GRCh38]})
        parser.add_argument('run_version')

    def handle(self, *args, **options):
        runs = get_pipeline_runs(**options, file_name='metadata.json')
        if not runs:
            error_msg = 'No successful runs found'
            self._raise_command_error(error_msg, options)

        run_dir, run_details = next(iter(runs.items()))
        metadata_path = os.path.join(run_dir, run_details['files'][0])
        metadata = json.loads(next(line for line in file_iter(metadata_path)))

        if 'sample_qc' not in metadata:
            error_msg = 'No sample qc results found'
            self._raise_command_error(error_msg, options)

        sample_type = metadata['sample_type']
        sample_qc = metadata['sample_qc']
        families = Family.objects.filter(guid__in=metadata['family_samples'].keys())
        individuals = Individual.objects.filter(
            family__in=families,
            individual_id__in=sample_qc.keys()
        )
        update_individuals_sample_qc(sample_type, individuals, sample_qc)

    @classmethod
    def _raise_command_error(cls, error_msg, options):
        user_args = [f'{k}={v}' for k, v in options.items()]
        raise CommandError(f'{error_msg} for {", ".join(user_args)}')
