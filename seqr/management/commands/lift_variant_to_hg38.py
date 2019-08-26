import logging
import json
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db.models.query_utils import Q
from pyliftover.liftover import LiftOver

from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Project, SavedVariant, Sample
from seqr.model_utils import update_xbrowse_vcfffiles
from seqr.views.apis.dataset_api import _update_samples
from seqr.views.utils.dataset_utils import match_sample_ids_to_sample_records, validate_index_metadata, \
    get_elasticsearch_index_samples
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants
from seqr.views.utils.variant_utils import reset_cached_search_results
from seqr.utils.es_utils import get_single_es_variant
from seqr.utils.xpos_utils import get_xpos

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('saved_variant_guid')
        parser.add_argument('variant_id')

    def handle(self, *args, **options):
        """transfer project"""
        saved_variant_guid = options['saved_variant_guid']
        variant_id = options['variant_id']

        saved_variant = SavedVariant.objects.get(guid=saved_variant_guid)

        if raw_input('Are you sure you want to update {}-{}-{} to {} (y/n)? '.format(
                saved_variant.xpos_start, saved_variant.ref, saved_variant.alt, variant_id)) != 'y':
            raise CommandError('Error: user did not confirm')

        es_variant = get_single_es_variant([saved_variant.family], variant_id)

        saved_variant.xpos_start = es_variant['xpos']
        saved_variant.ref = es_variant['ref']
        saved_variant.alt = es_variant['alt']
        saved_variant.saved_variant_json = json.dumps(es_variant)
        saved_variant.save()

        logger.info('---Done---')
