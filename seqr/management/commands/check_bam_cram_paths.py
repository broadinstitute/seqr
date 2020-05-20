from django.core.management.base import BaseCommand

from seqr.models import IgvSample
from seqr.views.utils.dataset_utils import validate_alignment_dataset_path


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        samples = IgvSample.objects.filter(
            individual__family__project__name__in=args,
        ).prefetch_related('individual', 'individual__family')

        failed = []
        for sample in samples:
            try:
                validate_alignment_dataset_path(sample.file_path)
            except Exception as e:
                individual_id = sample.individual.individual_id
                failed.append(individual_id)
                self.stdout.write('Error at {} (Individual: {}): {} '.format(sample.file_path, individual_id, e.message))

        self.stdout.write('---- DONE ----')
        self.stdout.write('Checked {} samples'.format(len(samples)))
        self.stdout.write('{} failed samples: {}'.format(len(failed), ', '.join(failed)))
