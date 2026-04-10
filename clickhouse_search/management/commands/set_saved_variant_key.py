from collections import defaultdict

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand
from django.db.models import F
import logging

from clickhouse_search.search import get_clickhouse_key_lookup
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import SavedVariant, Dataset
from seqr.utils.search.utils import parse_variant_id

logger = logging.getLogger(__name__)

BATCH_SIZE = 10000


class Command(BaseCommand):

    def handle(self, *args, **options):
        variant_ids = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh38,
            saved_variant_json__populations__isnull=False, # Omit manual variants
        ).values_list('variant_id', flat=True).distinct()
        ids_by_dataset_type = {
            Dataset.DATASET_TYPE_VARIANT_CALLS: [], Dataset.DATASET_TYPE_MITO_CALLS: [], Dataset.DATASET_TYPE_SV_CALLS: [],
        }
        for variant_id in variant_ids:
            parsed_id = parse_variant_id(variant_id)
            if not parsed_id and variant_id.endswith('-'):
                # Some AnVIL data was loaded with "-" as the alt allele
                parsed_id = parse_variant_id(variant_id[:-1])
            if parsed_id:
                is_mito = parsed_id[0].replace('chr', '').startswith('M')
                dataset_type = Dataset.DATASET_TYPE_MITO_CALLS if is_mito else Dataset.DATASET_TYPE_VARIANT_CALLS
            else:
                dataset_type = Dataset.DATASET_TYPE_SV_CALLS
            ids_by_dataset_type[dataset_type].append(variant_id)

        no_key_mito = self._set_variant_keys(ids_by_dataset_type[Dataset.DATASET_TYPE_MITO_CALLS], Dataset.DATASET_TYPE_MITO_CALLS)

        no_key_snv_indel = self._set_variant_keys(
            ids_by_dataset_type[Dataset.DATASET_TYPE_VARIANT_CALLS] + list(no_key_mito), Dataset.DATASET_TYPE_VARIANT_CALLS,
        )
        if no_key_snv_indel:
            self._resolve_missing_variants(no_key_snv_indel, GENOME_VERSION_GRCh38)

        no_keys_svs = self._set_variant_keys(
            ids_by_dataset_type[Dataset.DATASET_TYPE_SV_CALLS], f'{Dataset.DATASET_TYPE_SV_CALLS}_{Dataset.SAMPLE_TYPE_WGS}',
        )
        no_keys_svs = self._set_variant_keys(list(no_keys_svs), f'{Dataset.DATASET_TYPE_SV_CALLS}_{Dataset.SAMPLE_TYPE_WES}')
        if no_keys_svs:
            self._resolve_reloaded_svs(no_keys_svs)

        variant_ids_37 = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh37,
        ).values_list('variant_id', flat=True).distinct()

        no_keys_37 = self._set_variant_keys(variant_ids_37, Dataset.DATASET_TYPE_VARIANT_CALLS, genome_version=GENOME_VERSION_GRCh37)
        if no_keys_37:
            self._resolve_missing_variants(no_keys_37, GENOME_VERSION_GRCh37)

        num_updated = SavedVariant.objects.filter(key__isnull=False).exclude(saved_variant_json={}).update(
            saved_variant_json={},
        )
        logger.info(f'Cleared saved json for {num_updated} variants with keys')

        logger.info('Done')

    @staticmethod
    def _set_variant_keys(variants_ids, dataset_type, genome_version=GENOME_VERSION_GRCh38):
        if not variants_ids:
            return set()
        logger.info(f'Finding keys for {len(variants_ids)} {dataset_type} (GRCh{genome_version}) variant ids')
        variant_key_map = get_clickhouse_key_lookup(genome_version, dataset_type, variants_ids)
        logger.info(f'Found {len(variant_key_map)} keys')
        if not variant_key_map:
            return set(variants_ids)

        mapped_variant_ids = list(variant_key_map.keys())

        total_num_updated = 0
        for i in range(0, len(mapped_variant_ids), BATCH_SIZE):
            batch_ids = mapped_variant_ids[i:i + BATCH_SIZE]
            saved_variants = SavedVariant.objects.filter(
                family__project__genome_version=genome_version, variant_id__in=batch_ids,
            )
            for variant in saved_variants:
                variant.key = variant_key_map[variant.variant_id]
            num_updated = SavedVariant.objects.bulk_update(saved_variants, ['key'])
            logger.info(f'Updated batch of {num_updated}')
            total_num_updated += num_updated

        logger.info(f'Updated keys for {total_num_updated} {dataset_type} (GRCh{genome_version}) variants')

        no_key = set(variants_ids) - set(variant_key_map.keys())
        if no_key:
            logger.info(f'No key found for {len(no_key)} variants')
        return no_key

    @classmethod
    def _query_missing_variants(cls, variant_ids, variant_fields, genome_version=GENOME_VERSION_GRCh38):
        missing_variants = SavedVariant.objects.filter(
            variant_id__in=variant_ids, family__project__genome_version=genome_version,
        )
        num_missing = missing_variants.count()
        missing_with_data_qs = missing_variants.filter(family__individual__active_datasets__isnull=False).distinct()
        missing_with_search_data = missing_with_data_qs.values(
            'variant_id', *variant_fields,
        ).annotate(family_ids=ArrayAgg('family__family_id', distinct=True)).order_by('variant_id')
        return missing_with_search_data, num_missing

    @classmethod
    def _resolve_missing_variants(cls, variant_ids, genome_version):
        missing_with_search_data, num_missing = cls._query_missing_variants(
            variant_ids, ['saved_variant_json__populations__seqr__ac'], genome_version,
        )
        num_data= len(missing_with_search_data)
        in_backend = [
            f"{var['variant_id']} - {'; '.join(var['family_ids'])}"
            for var in missing_with_search_data if var['saved_variant_json__populations__seqr__ac']
        ]
        logger.info(
            f'{num_missing} variants have no key, {num_missing - num_data} of which have no search data, {num_data - len(in_backend)} of which are absent from the hail backend.'
        )
        if in_backend:
            logger.info(f'{len(in_backend)} remaining variants: {", ".join(in_backend)}')

    @classmethod
    def _resolve_reloaded_svs(cls, variant_ids):
        missing_with_search_data, num_missing = cls._query_missing_variants(
            list(variant_ids), ['family__individual__active_datasets__sample_type'],
        )
        logger.info(
            f'{num_missing} SV variants have no key, {num_missing - len(missing_with_search_data)} of which have no search data'
        )
        if not missing_with_search_data:
            return

        missing_by_sample_type = defaultdict(list)
        for variant in missing_with_search_data:
            variant_id = variant['variant_id']
            sample_type = variant['family__individual__active_datasets__sample_type']
            missing_by_sample_type[sample_type].append(f"{variant_id} - {'; '.join(variant['family_ids'])}" )

        for sample_type, variants in missing_by_sample_type.items():
            logger.info(f'{len(variants)} remaining SV {sample_type} variants {", ".join(variants)}')
