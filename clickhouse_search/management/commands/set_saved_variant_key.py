from django.core.management.base import BaseCommand
from django.db.models import F
import logging

from pysam.libcvcf import defaultdict

from clickhouse_search.search import get_clickhouse_key_lookup
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import SavedVariant, Sample
from seqr.utils.file_utils import file_iter
from seqr.views.utils.file_utils import parse_file
from seqr.utils.search.utils import parse_variant_id

logger = logging.getLogger(__name__)

GCNV_CALLSET_PATH = 'gs://seqr-datasets-gcnv/GRCh38/RDG_WES_Broad_Internal/v4/CMG_gCNV_2022_annotated.ensembl.round2_3.strvctvre.tsv.gz'

SV_ID_UPDATE_MAP = {
    'WGS': {
        'CMG.phase1_CMG_DEL_chr10_2038': 'phase2_DEL_chr10_4611',
        'CMG.phase1_CMG_DEL_chr11_2963': 'phase2_DEL_chr11_5789',
        'CMG.phase1_CMG_DEL_chr13_153': 'phase2_DEL_chr13_378',
        'cohort_2911.chr1.final_cleanup_BND_chr1_1167': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_1376',
        'cohort_2911.chr1.final_cleanup_BND_chr1_1017': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_1208',
        'cohort_2911.chr1.final_cleanup_BND_chr1_2837': 'phase4_all_batches.chr1.final_cleanup_BND_chr1_3326',
        'cohort_2911.chr1.final_cleanup_DEL_chr1_12237': 'phase2_DEL_chr1_9347',
        'cohort_2911.chr1.final_cleanup_DEL_chr1_2953': 'phase2_DEL_chr1_2503',
    },
    'WES': {
        'R4_variant_7334_DUP_08162023': 'R4_variant_7334_DUP',
    },
}


class Command(BaseCommand):

    def handle(self, *args, **options):
        num_updated = SavedVariant.objects.filter(
            genotypes={}, saved_variant_json__genotypes__isnull=False,
        ).exclude(saved_variant_json__genotypes={}).update(genotypes=F('saved_variant_json__genotypes'))
        logger.info(f'Updated genotypes for {num_updated} variants')

        variant_ids = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh38,
            saved_variant_json__populations__isnull=False, # Omit manual variants
        ).values_list('variant_id', flat=True).distinct()
        ids_by_dataset_type = {
            Sample.DATASET_TYPE_VARIANT_CALLS: [], Sample.DATASET_TYPE_MITO_CALLS: [], Sample.DATASET_TYPE_SV_CALLS: [],
        }
        for variant_id in variant_ids:
            parsed_id = parse_variant_id(variant_id)
            if not parsed_id and variant_id.endswith('-'):
                # Some AnVIL data was loaded with "-" as the alt allele
                parsed_id = parse_variant_id(variant_id[:-1])
            if parsed_id:
                is_mito = parsed_id[0].replace('chr', '').startswith('M')
                dataset_type = Sample.DATASET_TYPE_MITO_CALLS if is_mito else Sample.DATASET_TYPE_VARIANT_CALLS
            else:
                dataset_type = Sample.DATASET_TYPE_SV_CALLS
            ids_by_dataset_type[dataset_type].append(variant_id)

        no_key_mito = self._set_variant_keys(ids_by_dataset_type[Sample.DATASET_TYPE_MITO_CALLS], Sample.DATASET_TYPE_MITO_CALLS)

        no_key_snv_indel = self._set_variant_keys(
            ids_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS] + list(no_key_mito), Sample.DATASET_TYPE_VARIANT_CALLS,
        )
        if no_key_snv_indel:
            self._resolve_missing_variants(no_key_snv_indel, GENOME_VERSION_GRCh38)

        no_keys_svs = self._set_variant_keys(
            ids_by_dataset_type[Sample.DATASET_TYPE_SV_CALLS], f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WGS}',
        )
        no_keys_svs = self._set_variant_keys(list(no_keys_svs), f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}')
        if no_keys_svs:
            self._resolve_reloaded_svs(no_keys_svs)

        variant_ids_37 = SavedVariant.objects.filter(
            key__isnull=True, family__project__genome_version=GENOME_VERSION_GRCh37,
        ).values_list('variant_id', flat=True).distinct()

        no_keys_37 = self._set_variant_keys(variant_ids_37, Sample.DATASET_TYPE_VARIANT_CALLS, genome_version=GENOME_VERSION_GRCh37)
        if no_keys_37:
            self._resolve_missing_variants(no_keys_37, GENOME_VERSION_GRCh37)

        logger.info('Done')

    @staticmethod
    def _set_variant_keys(variants_ids, dataset_type, genome_version=GENOME_VERSION_GRCh38, variant_id_updates=None):
        if not variants_ids:
            return
        logger.info(f'Finding keys for {len(variants_ids)} {dataset_type} (GRCh{genome_version}) variant ids')
        variant_key_map = get_clickhouse_key_lookup(genome_version, dataset_type, variants_ids)
        logger.info(f'Found {len(variant_key_map)} keys')
        if not variant_key_map:
            return set(variants_ids)

        mapped_variant_ids = variant_key_map.keys()
        if variant_id_updates:
            reverse_lookup = {v: k for k, v in variant_id_updates.items()}
            mapped_variant_ids = [reverse_lookup[vid] for vid in mapped_variant_ids]
        saved_variants = SavedVariant.objects.filter(
            family__project__genome_version=genome_version, variant_id__in=mapped_variant_ids,
        )
        for variant in saved_variants:
            if variant_id_updates:
                variant.variant_id = variant_id_updates[variant.variant_id]
            variant.key = variant_key_map[variant.variant_id]
            variant.dataset_type = dataset_type
        update_fields = ['key', 'dataset_type']
        if variant_id_updates:
            update_fields.append('variant_id')
        num_updated = SavedVariant.objects.bulk_update(saved_variants, update_fields, batch_size=10000)
        logger.info(f'Updated keys for {num_updated} {dataset_type} (GRCh{genome_version}) variants')

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
        missing_with_search_data = missing_variants.filter(family__individual__sample__is_active=True).values_list(
            'variant_id', 'family__family_id', 'guid', *variant_fields,
        ).distinct().order_by('variant_id')
        return missing_with_search_data, num_missing

    @classmethod
    def _resolve_missing_variants(cls, variant_ids, genome_version):
        missing_with_search_data, num_missing = cls._query_missing_variants(
            variant_ids, ['saved_variant_json__populations__seqr__ac'], genome_version,
        )
        num_data= len(missing_with_search_data)
        in_backend = [' - '.join(var[:3]) for var in missing_with_search_data if var[3]]
        logger.info(
            f'{num_missing} variants have no key, {num_missing - num_data} of which have no search data, {num_data - len(in_backend)} of which are absent from the hail backend.'
        )
        if in_backend:
            logger.info(f'{len(in_backend)} remaining variants: {", ".join(in_backend)}')

    @classmethod
    def _resolve_reloaded_svs(cls, variant_ids):
        missing_with_search_data, num_missing = cls._query_missing_variants(
            variant_ids, ['family__individual__sample__sample_type', 'family__project__guid'],
        )
        num_data = len(missing_with_search_data)
        # The CMG_gCNV project was an old project created before SV data was widely available, and keeping it up to date is less crucial
        valid_project_data = [variant for variant in missing_with_search_data if variant[4] != 'R0486_cmg_gcnv']
        logger.info(
            f'{num_missing} variants have no key, {num_missing - num_data} of which have no search data, {num_data - len(valid_project_data)} of which are in a skippable project.'
        )
        if not valid_project_data:
            return

        gcnv_id_map = cls._load_gcnv_id_map()
        missing_by_sample_type = defaultdict(list)
        update_variants_by_sample_type = defaultdict(dict)
        for variant in valid_project_data:
            variant_id = variant[0]
            sample_type = variant[3]
            update_id = SV_ID_UPDATE_MAP[sample_type].get(variant_id)
            if not update_id and sample_type == 'WES' :
                suffix = next((suff for suff in ['_DEL', '_DUP'] if variant_id.endswith(suff)), None)
                if suffix:
                    base_id = gcnv_id_map.get(variant_id.rsplit(suffix)[0])
                    if base_id:
                        update_id = f'{base_id}{suffix}'
            if update_id:
                update_variants_by_sample_type[sample_type][variant_id] = update_id
            else:
                missing_by_sample_type[sample_type].append(variant[:3])

        for sample_type, variant_id_updates in update_variants_by_sample_type.items():
            logger.info(f'Mapping reloaded SV_{sample_type} IDs to latest version')
            failed_mapping = cls._set_variant_keys(
                list(variant_id_updates.values()), f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}',
                genome_version=GENOME_VERSION_GRCh38, variant_id_updates=variant_id_updates,
            )
            if failed_mapping:
                logger.info(f'{len(failed_mapping)} variants failed ID mapping: {failed_mapping[:10]}...')

        for sample_type, variants in missing_by_sample_type.items():
            logger.info(f'{len(variants)} remaining SV {sample_type} variants: {variants[:10]}...')

    @staticmethod
    def _load_gcnv_id_map():
        file_content = file_iter(GCNV_CALLSET_PATH)
        header = next(file_content).split('\t')
        variant_name_idx = header.index('variant_name')
        old_id_idx = header.index('any_ovl')
        id_map = {}
        for raw_row in file_content:
            row = raw_row.split('\t')
            for old_id in row[old_id_idx].split(';'):
                id_map[old_id.strip()] = row[variant_name_idx].strip()
        return id_map
