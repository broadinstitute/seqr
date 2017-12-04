import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from reference_data.models import GENOME_VERSION_CHOICES
from seqr.models import ElasticsearchDataset
from seqr.views.apis.dataset_api import create_dataset, create_elasticsearch_dataset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create a new dataset.'

    def add_arguments(self, parser):
        parser.add_argument('-p', '--project-id')
        parser.add_argument('-t', '--analysis-type', default=ElasticsearchDataset.ANALYSIS_TYPE_VARIANT_CALLS, choices=[t[0] for t in ElasticsearchDataset.ANALYSIS_TYPE_CHOICES])
        parser.add_argument('-H', '--elasticsearch-host', required=True)
        parser.add_argument('-i', '--elasticsearch-index', required=True)
        parser.add_argument('-s', '--source-file', required=True)

    def handle(self, *args, **options):

        dataset = create_elasticsearch_dataset(
            analysis_type=options["analysis_type"],
            elasticsearch_host=options["elasticsearch_host"],
            elasticsearch_index=options["elasticsearch_index"],
            source_file=options["source_file"],
            is_loaded=True,
            loaded_date=timezone.now(),
        )

        logger.info("Created dataset %s" % dataset.guid)
