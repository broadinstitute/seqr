from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import F
import logging
import re

from clickhouse_search.search import get_clickhouse_key_lookup
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import SavedVariant, Sample
from seqr.utils.file_utils import file_iter
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
        'cohort_2911.chrX.final_cleanup_CPX_chrX_20': 'cohort_2911.chrX.final_cleanup_CPX_chrX_19',
    },
    'WES': {
        'R4_variant_7334_DUP_08162023': 'R4_variant_7334_DUP',
        'prefix_112949_DEL': 'suffix_210553_DEL',
        'prefix_131670_DUP': 'suffix_251025_DUP',
        'suffix_19443_DEL_2': 'suffix_20030_DEL',
        'prefix_184342_DEL': 'suffix_194439_DEL',
        'prefix_255018_DEL': 'suffix_155939_DEL',
        'prefix_188042_DUP': 'suffix_107531_DUP',
        'suffix_104367_DUP_2': 'suffix_107531_DUP',
        'prefix_59865_DEL': 'suffix_124465_DEL',
        'suffix_120814_DEL_2': 'suffix_124465_DEL',
        'prefix_152595_DEL': 'suffix_286580_DEL',
        'suffix_277504_DEL_2': 'suffix_286581_DEL',
        'prefix_185630_DEL': 'suffix_217490_DEL',
        'suffix_210888_DEL_2': 'suffix_217490_DEL',
        'prefix_126071_DUP': 'suffix_48694_DUP',
        'suffix_47226_DUP_2': 'suffix_48694_DUP',
        'prefix_177696_DUP': 'suffix_23_DUP',
        'prefix_33049_DEL': 'suffix_123373_DEL',
        'suffix_119753_DEL_2': 'suffix_123373_DEL',
        'prefix_6968_DUP': 'suffix_8158_DUP',
        'prefix_111128_DEL': 'suffix_124250_DEL',
        'prefix_265455_DEL': 'suffix_124250_DEL',
        'prefix_133233_DEL': 'suffix_149757_DEL',
        'suffix_145373_DEL_2': 'suffix_149757_DEL',
        'prefix_104962_DEL': 'suffix_262703_DEL',
        'prefix_230669_DUP': 'suffix_37212_DUP',
        'prefix_195634_DUP': 'suffix_337680_DUP',
        'suffix_326904_DUP_2': 'suffix_337680_DUP',
        'prefix_252896_DUP': 'suffix_154760_DUP',
        'prefix_252895_DUP': 'suffix_150484_DUP',
        'prefix_192808_DUP': 'suffix_182662_DUP',
        'prefix_31312_DUP': 'suffix_343278_DUP',
        'suffix_332369_DUP_2': 'suffix_343278_DUP',
        'prefix_201559_DEL': 'suffix_228780_DEL',
        'prefix_173086_DEL': 'suffix_195404_DEL',
        'prefix_230567_DEL': 'suffix_261336_DEL',
        'prefix_25206_DEL': 'suffix_27995_DEL',
        'prefix_72517_DEL': 'suffix_27995_DEL',
        'prefix_194936_DUP': 'suffix_220746_DUP',
        'prefix_117065_DEL': 'suffix_131048_DEL',
        'suffix_127235_DEL_2': 'suffix_131048_DEL',
        'prefix_168621_DEL': 'suffix_336993_DEL',
        'prefix_297236_DEL': 'suffix_336993_DEL',
        'prefix_198998_DUP': 'suffix_225862_DUP',
        'prefix_239300_DUP': 'suffix_271302_DUP',
        'prefix_236836_DEL': 'suffix_268435_DEL',
        'prefix_31131_DUP': 'suffix_34872_DUP',
        'prefix_238314_DEL': 'suffix_336979_DEL',
        'prefix_75798_DUP': 'suffix_84697_DUP',
        'prefix_261715_DEL': 'suffix_337689_DEL',
        'prefix_183989_DEL': 'suffix_4946_DEL',
        'prefix_26448_DEL': 'suffix_43066_DEL',
        'suffix_41786_DEL_2': 'suffix_43066_DEL',
        'prefix_103176_DEL': 'suffix_114811_DEL',
        'suffix_111479_DEL_2': 'suffix_114811_DEL',
        'prefix_120528_DEL': 'suffix_135375_DEL',
        'prefix_296302_DEL': 'suffix_335637_DEL',
        'prefix_108274_DEL': 'suffix_121089_DEL',
        'prefix_46615_DEL': 'suffix_118481_DEL',
        'prefix_185022_DUP': 'suffix_12708_DUP',
        'suffix_12284_DUP_2': 'suffix_12708_DUP',
        'prefix_252585_DUP': 'suffix_309117_DUP',
        'suffix_299264_DUP_2': 'suffix_309117_DUP',
        'prefix_80031_DUP': 'suffix_241944_DUP',
        'suffix_234357_DUP_2': 'suffix_241944_DUP',
        'prefix_117179_DEL': 'suffix_131305_DEL',
        'prefix_71499_DUP': 'suffix_330986_DUP',
        'suffix_320433_DUP_2': 'suffix_330986_DUP',
        'prefix_24788_DUP': 'suffix_336670_DUP',
        'suffix_325911_DUP_2': 'suffix_336670_DUP',
        'prefix_192365_DUP': 'suffix_139090_DUP',
        'prefix_255360_DUP': 'suffix_337082_DUP',
        'prefix_237614_DEL': 'suffix_269379_DEL',
        'prefix_284003_DEL': 'suffix_321174_DEL',
        'suffix_12426_DEL_2': 'suffix_12852_DEL',
        'prefix_9852_DEL': 'suffix_12852_DEL',
        'suffix_50042_DEL_2': 'suffix_51609_DEL',
        'prefix_223675_DEL': 'suffix_51609_DEL',
        'prefix_175156_DEL': 'suffix_54122_DEL',
        'suffix_52499_DEL_2': 'suffix_54122_DEL',
        'prefix_3138_DEL': 'suffix_109381_DEL',
        'suffix_106163_DEL_2': 'suffix_109381_DEL',
        'prefix_255276_DEL': 'suffix_93464_DEL',
        'prefix_152594_DEL': 'suffix_286542_DEL',
        'prefix_77396_DEL': 'suffix_287070_DEL',
        'prefix_152599_DEL': 'suffix_287163_DEL',
        'prefix_152600_DEL': 'suffix_287381_DEL',
        'prefix_108317_DEL': 'suffix_161791_DEL',
        'prefix_201562_DEL': 'suffix_168210_DEL',
        'suffix_163193_DEL_2': 'suffix_168210_DEL',
        'prefix_246635_DEL': 'suffix_92687_DEL',
        'suffix_89974_DEL_2': 'suffix_92687_DEL',
        'prefix_246642_DEL': 'suffix_93299_DEL',
        'suffix_90573_DEL_2': 'suffix_93299_DEL',
        'prefix_246674_DUP': 'suffix_126676_DUP',
        'suffix_122983_DUP_2': 'suffix_126676_DUP',
        'prefix_199389_DEL': 'suffix_94004_DEL',
        'prefix_3593_DEL': 'suffix_27094_DEL',
        'prefix_100725_DEL': 'suffix_336955_DEL',
        'prefix_297227_DEL': 'suffix_336980_DEL',
        'prefix_179648_DEL': 'suffix_202719_DEL',
        'prefix_143182_DEL': 'suffix_100756_DEL',
        'prefix_34890_DEL': 'suffix_38919_DEL',
        'prefix_36703_DEL': 'suffix_39815_DEL',
        'prefix_164553_DEL': 'suffix_185929_DEL',
        'prefix_132206_DEL': 'suffix_282692_DEL',
        'suffix_273714_DEL_2': 'suffix_282692_DEL',
        'prefix_144442_DEL': 'suffix_282716_DEL',
        'suffix_273738_DEL_2': 'suffix_282716_DEL',
        'suffix_273732_DEL_2': 'suffix_282710_DEL',
        'prefix_6326_DEL': 'suffix_282710_DEL',
        'prefix_178200_DEL': 'suffix_118870_DEL',
        'suffix_115409_DEL_2': 'suffix_118870_DEL',
        'prefix_254507_DUP': 'suffix_283948_DUP',
        'prefix_254510_DUP': 'suffix_39298_DUP',
        'prefix_13260_DEL': 'suffix_38202_DEL',
        'suffix_37073_DEL_2': 'suffix_38202_DEL',
        'prefix_278497_DEL': 'suffix_338533_DEL',
        'suffix_327734_DEL_2': 'suffix_338533_DEL',
        'prefix_242131_DEL': 'suffix_176483_DEL',
        'suffix_171236_DEL_2': 'suffix_176483_DEL',
        'suffix_32210_DEL_2': 'suffix_33192_DEL',
        'prefix_37286_DEL': 'suffix_33192_DEL',
        'prefix_113302_DUP': 'suffix_236396_DUP',
        'suffix_228996_DUP_2': 'suffix_236396_DUP',
        'prefix_154396_DEL': 'suffix_174270_DEL',
        'prefix_71769_DEL': 'suffix_227830_DEL',
        'suffix_220764_DEL_2': 'suffix_227830_DEL',
        'prefix_44455_DEL': 'suffix_50096_DEL',
        'prefix_135473_DEL': 'suffix_152259_DEL',
        'prefix_83881_DUP': 'suffix_93771_DUP',
        'prefix_185180_DEL': 'suffix_190807_DEL',
        'prefix_230340_DEL': 'suffix_217490_DEL',
        'prefix_98781_DUP': 'suffix_118080_DUP',
        'suffix_333515_DEL_2': 'suffix_344457_DEL',
        'prefix_50567_DEL': 'suffix_344457_DEL',
        'suffix_243997_DEL_2': 'suffix_251931_DEL',
        'prefix_185688_DEL': 'suffix_251931_DEL',
        'prefix_185697_DEL': 'suffix_252985_DEL',
        'suffix_245019_DEL_2': 'suffix_252985_DEL',
        'prefix_185700_DEL': 'suffix_253165_DEL',
        'suffix_245194_DEL_2': 'suffix_253165_DEL',
    },
}
SV_DROPPED_IDS = {
    'cluster_6_last_call_cnv_17479_DUP', 'cluster_1_last_call_cnv_30127_DEL', 'cluster_19_COHORT_cnv_23176_DEL',
    'phase2_DEL_chrX_1149',
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
        num_known_dropped = len(SV_DROPPED_IDS.intersection(variant_ids))
        missing_with_search_data, num_missing = cls._query_missing_variants(
            list(set(variant_ids) - SV_DROPPED_IDS), ['family__individual__sample__sample_type', 'family__project__guid'],
        )
        num_data = len(missing_with_search_data)
        # The CMG_gCNV project was an old project created before SV data was widely available, and keeping it up to date is less crucial
        valid_project_data = [variant for variant in missing_with_search_data if variant[4] != 'R0486_cmg_gcnv']
        logger.info(
            f'{num_missing + num_known_dropped} variants have no key, {num_known_dropped} of which are known to have dropped out of the callset, {num_missing - num_data} of which have no search data, {num_data - len(valid_project_data)} of which are in a skippable project.'
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
            elif re.match(r'.*_(DEL|DUP)_\d+', variant_id):
                update_variants_by_sample_type[sample_type][variant_id] = variant_id.rsplit('_', 1)[0]
            else:
                missing_by_sample_type[sample_type].append(variant[:3])

        for sample_type, variant_id_updates in update_variants_by_sample_type.items():
            logger.info(f'Mapping reloaded SV_{sample_type} IDs to latest version')
            failed_mapping = cls._set_variant_keys(
                list(variant_id_updates.values()), f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}',
                genome_version=GENOME_VERSION_GRCh38, variant_id_updates=variant_id_updates,
            )
            if failed_mapping:
                logger.info(f'{len(failed_mapping)} variants failed ID mapping: {list(failed_mapping)[:10]}...')

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
