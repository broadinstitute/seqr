from django.core.management.base import BaseCommand
from django.db.models import F
import logging

from clickhouse_search.models import KEY_LOOKUP_CLASS_MAP
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import SavedVariant, Sample
from seqr.utils.search.utils import parse_variant_id

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        num_updated = SavedVariant.objects.filter(
            genotypes={}, saved_variant_json__genotypes__isnull=False,
        ).exclude(saved_variant_json__genotypes={}).update(genotypes=F('saved_variant_json__genotypes'))
        logger.info(f'Updated genotypes for {num_updated} variants')

        variant_ids = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh38,
        ).values_list('variant_id', flat=True).distinct()
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

        no_key_ids = self._set_variant_keys(ids_by_dataset_type[Sample.DATASET_TYPE_MITO_CALLS], Sample.DATASET_TYPE_MITO_CALLS)

        self._set_variant_keys(
            ids_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS] + list(no_key_ids), Sample.DATASET_TYPE_VARIANT_CALLS,
        )

        no_keys_svs = self._set_variant_keys(
            ids_by_dataset_type[Sample.DATASET_TYPE_SV_CALLS], f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}',
        )
        self._set_variant_keys(no_keys_svs, f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}')

        variant_ids_37 = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh37,
        ).values_list('variant_id', flat=True).distinct()
        self._set_variant_keys(variant_ids_37, Sample.DATASET_TYPE_VARIANT_CALLS, genome_version=GENOME_VERSION_GRCh37)

        logger.info('Done')

    @staticmethod
    def _set_variant_keys(variants_ids, dataset_type, genome_version=GENOME_VERSION_GRCh38):
        key_lookup_class = KEY_LOOKUP_CLASS_MAP[genome_version][dataset_type]
        variant_key_map = dict(
            key_lookup_class.objects.filter(variant_id__in=variants_ids).values_list('variant_id', 'key')
        )
        saved_variants = SavedVariant.objects.filter(
            family__project__genome_version=genome_version, variant_id__in=variant_key_map,
        )
        for variant in saved_variants:
            variant.key = variant_key_map[variant.variant_id]
        num_updated = SavedVariant.objects.bulk_update(saved_variants, ['key'])
        logger.info(f'Updated keys for {num_updated} {dataset_type} (GRCh{genome_version}) variants')

        no_key = set(variants_ids) - set(variant_key_map.keys())
        if no_key:
            logger.info(f'No key found for {len(no_key)} variants')
        return no_key
