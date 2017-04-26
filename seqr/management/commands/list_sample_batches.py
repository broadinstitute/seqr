from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q

from seqr.models import SampleBatch

class Command(BaseCommand):
    help = 'Print info on sample batch(s).'

    def add_arguments(self, parser):
        parser.add_argument('sample_batch_keyword', nargs="?")

    def handle(self, *args, **options):
        if options['sample_batch_keyword']:
            sample_batches = SampleBatch.objects.filter(Q(guid__contains=options['sample_batch_keyword']) | Q(name__contains=options['sample_batch_keyword']))
        else:
            sample_batches = SampleBatch.objects.all()

        print("\t".join(["name", "description", "is_loaded", "loaded_date", "sequencing_type", "genome_build_id", "path"]))
        for d in sample_batches:
            print("\t".join(map(unicode, [d.name, d.description, d.is_loaded, d.data_loaded_date, d.sequencing_type, d.genome_build_id, d.path])))

