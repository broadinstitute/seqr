from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q

from seqr.models import Dataset


class Command(BaseCommand):
    help = 'Print a list of datasets(s).'

    def add_arguments(self, parser):
        parser.add_argument('keyword', nargs="?")

    def handle(self, *args, **options):
        if options['keyword']:
            datasets = Dataset.objects.filter(
                Q(samples__individual__family__project__guid__icontains=options['keyword']) |
                Q(individual__family__guid__icontains=options['keyword']) |
                Q(individual__guid__icontains=options['keyword']) |
                Q(samples__sample_type__icontains=options['keyword']) |
                Q(analysis_type__icontains=options['keyword'])
            )
        else:
            datasets = Dataset.objects.all()

        print("\t".join(["project", "sample_type", "sample_count", "analysis_type", "is_loaded", "loaded_date", "source_file"]))
        for d in datasets:
            project_name = ""
            sample_type = ""
            sample_count = 0
            for s in d.samples.all():
                project_name = s.individual.family.project.name
                sample_type = s.sample_type
                sample_count += 1
            print("\t".join(map(unicode, [project_name, sample_type, sample_count, d.analysis_type, d.is_loaded, d.loaded_date, d.source_file_path])))

