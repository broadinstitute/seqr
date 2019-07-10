from django.core.management.base import BaseCommand
from django.db.models import Max

from seqr.models import Sample
from seqr.views.utils.dataset_utils import validate_alignment_dataset_path


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        all_samples = Sample.objects.filter(
            dataset_type=Sample.DATASET_TYPE_READ_ALIGNMENTS,
            sample_status=Sample.SAMPLE_STATUS_LOADED,
            dataset_file_path__isnull=False,
            individual__family__project__name__in=args,
        ).prefetch_related('individual', 'individual__family')
        sample_individual_max_loaded_date = {
            agg['individual__guid']: agg['max_loaded_date'] for agg in
            all_samples.values('individual__guid').annotate(max_loaded_date=Max('loaded_date'))
        }
        samples = [s for s in all_samples if s.loaded_date == sample_individual_max_loaded_date[s.individual.guid]]

        failed = []
        for sample in samples:
            try:
                validate_alignment_dataset_path(sample.dataset_file_path)
            except Exception as e:
                individual_id = sample.individual.individual_id
                failed.append(individual_id)
                print('Error at {} (Individual: {}): {} '.format(sample.dataset_file_path, individual_id, e.message))

        print('---- DONE ----')
        print('Checked {} samples'.format(len(samples)))
        print('{} failed samples: {}'.format(len(failed), ', '.join(failed)))
