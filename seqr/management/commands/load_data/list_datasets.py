from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q

from seqr.models import SampleBatch


class Command(BaseCommand):
    help = 'Print a list of datasets(s).'

    def add_arguments(self, parser):
        parser.add_argument('keyword', nargs="?")

    def handle(self, *args, **options):
        if options['keyword']:
            sample_batches = SampleBatch.objects.filter(
                Q(guid__icontains=options['keyword']) |
                Q(name__icontains=options['keyword']) |
                Q(description__icontains=options['keyword']) |
                Q(sample_type__icontains=options['keyword']))
        else:
            sample_batches = SampleBatch.objects.all()

        print("\t".join(["name", "description", "sample_type", "genome_build_id", "created_date"]))
        for d in sample_batches:
            print("\t".join(map(unicode, [d.name, d.description, d.sample_type, d.data_loaded_date, d.sample_type, d.genome_build_id, d.path])))

