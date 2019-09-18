from django.core.management.base import BaseCommand
from django.db.models import Max
from collections import defaultdict

from seqr.models import Sample


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--project')

    def handle(self, *args, **options):
        all_samples = Sample.objects.filter(
            dataset_type=Sample.DATASET_TYPE_READ_ALIGNMENTS,
            sample_status=Sample.SAMPLE_STATUS_LOADED,
        )
        if options['project']:
            all_samples.filter(individual__family__project__guid=options['project'])
        all_samples.prefetch_related('individual').prefetch_related('individual__family__project')

        sample_individual_max_loaded_date = {
            agg['individual__guid']: agg['max_loaded_date'] for agg in
            all_samples.values('individual__guid').annotate(max_loaded_date=Max('loaded_date'))
        }

        samples = [s for s in all_samples if s.loaded_date == sample_individual_max_loaded_date[s.individual.guid] and
                   s.dataset_file_path.endswith('.bam') and not s.dataset_file_path.startswith('gs://')]

        project_bams = defaultdict(list)
        for sample in samples:
            project_bams[sample.individual.family.project.name].append(sample.dataset_file_path)

        for project in sorted(project_bams.keys()):
            print('{}: {} bams'.format(project, len(project_bams[project])))

        if options['project']:
            for bam_path in project_bams.values()[0]:
                print(bam_path)
