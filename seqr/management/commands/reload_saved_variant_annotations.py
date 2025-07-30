from django.core.management.base import BaseCommand, CommandError
from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Sample
from seqr.management.commands.check_for_new_samples_from_pipeline import reload_shared_variant_annotations
from seqr.utils.search.hail_search_utils import search_data_type
from seqr.utils.search.utils import backend_specific_call

DATA_TYPE_CHOICES = {
    search_data_type(dt, st) for dt in Sample.DATASET_TYPE_LOOKUP for st in [Sample.SAMPLE_TYPE_WGS, Sample.SAMPLE_TYPE_WES]
}


def _clickhouse_error():
    raise CommandError('Reloading variant annotations is not supported in clickhouse')


class Command(BaseCommand):
    help = 'Reload shared variant annotations for all saved variants'

    def add_arguments(self, parser):
        parser.add_argument('data_type', choices=sorted(DATA_TYPE_CHOICES))
        parser.add_argument('genome_version', choices=sorted(GENOME_VERSION_LOOKUP.values()))
        parser.add_argument('chromosomes', nargs='*', help='Chromosome(s) to reload. If not specified, defaults to all chromosomes.')

    def handle(self, *args, **options):
        backend_specific_call(lambda: True, lambda: True, _clickhouse_error)()
        reload_shared_variant_annotations(options['data_type'], options['genome_version'], chromosomes=options['chromosomes'])
