from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q

from seqr.models import Dataset


class Command(BaseCommand):
    help = 'Print a list of datasets(s).'

    def add_arguments(self, parser):
        parser.add_argument("-a", "--analysis-type", choices=[a[0] for a in Dataset.ANALYSIS_TYPE_CHOICES])
        parser.add_argument('keyword', nargs="?")

    def handle(self, *args, **options):
        q1 = None
        if options['keyword']:
            q1 = (
                Q(guid__icontains=options['keyword']) |
                Q(source_file_path__icontains=options['keyword']) |
                Q(project__guid__icontains=options['keyword'])
                #Q(samples__sample_type__icontains=options['keyword'])
            )
        q2 = None
        if options['analysis_type']:
            q2 = Q(analysis_type=options['analysis_type'])

        if q1 and q2:
            q = q1 & q2
        elif q1:
            q = q1
        elif q2:
            q = q2
        else:
            q = None

        if q:
            datasets = Dataset.objects.filter(q)
        else:
            datasets = Dataset.objects.all()

        columns = [
            ("created_date", "%-25s"),
            ("dataset_id", "%-25s"),
            ("project", "%-20s"),
            ("sample_type", "%-15s"),
            ("sample_count", "%15s"),
            ("analysis_type", "%-15s"),
            ("is_loaded", "%-10s"),
            ("loaded_date", "%-25s"),
            ("source_file", "%-10s")
        ]
        print("\t".join([c % v for v, c in columns]))
        for d in datasets.order_by('created_date'):
            sample_type = ""
            sample_count = 0
            project_name = ""
            for s in d.samples.all():
                sample_type = s.sample_type
                sample_count += 1
                if not d.project:
                    d.project = s.individual.family.project
                    d.save()
                    project_name = d.project.name

            print("\t".join([
                c % v for c, v in zip(
                    [c[1] for c in columns],
                    map(unicode, [str(d.created_date)[:19], d.guid, project_name, sample_type, sample_count, d.analysis_type, d.is_loaded, d.loaded_date, d.source_file_path]),
                )]
            ))

