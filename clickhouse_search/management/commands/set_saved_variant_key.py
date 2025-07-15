from django.core.management.base import BaseCommand
from django.db.models import F
import logging

from seqr.models import SavedVariant, Sample
from seqr.utils.search.utils import parse_variant_id

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        num_updated = SavedVariant.objects.filter(
            genotypes={}, saved_variant_json__genotypes__isnull=False,
        ).update(genotypes=F('saved_variant_json__genotypes'))
        logger.info(f'Updated genotypes for {num_updated} variants')

        variant_ids = SavedVariant.objects.filter(key__isnull=True).values_list('variant_id', flat=True, distinct=True)
        ids_by_dataset_type = {
            Sample.DATASET_TYPE_VARIANT_CALLS: [], Sample.DATASET_TYPE_MITO_CALLS: [], Sample.DATASET_TYPE_SV_CALLS: [],
        }
        for variant_id in variant_ids:
            parsed_id = parse_variant_id(variant_id)
            if parsed_id:
                is_mito = parsed_id[0].replace('chr', '').startswith('M')
                dataset_type = Sample.DATASET_TYPE_MITO_CALLS if is_mito else Sample.DATASET_TYPE_VARIANT_CALLS
            else:
                dataset_type = Sample.DATASET_TYPE_SV_CALLS
            ids_by_dataset_type[dataset_type].append(variant_id)


        logger.info('Done')
