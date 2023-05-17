import logging
from django.core.management.base import BaseCommand, CommandError

from seqr.models import SavedVariant
from seqr.utils.search.utils import get_single_variant

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

        if input('Are you sure you want to update {}-{}-{} to {} (y/n)? '.format(
                saved_variant.xpos, saved_variant.ref, saved_variant.alt, variant_id)) != 'y':
            raise CommandError('Error: user did not confirm')

        es_variant = get_single_variant([saved_variant.family], variant_id, return_all_queried_families=True)

        saved_variant.xpos = es_variant['xpos']
        saved_variant.ref = es_variant['ref']
        saved_variant.alt = es_variant['alt']
        saved_variant.saved_variant_json = es_variant
        saved_variant.save()

        logger.info('---Done---')
