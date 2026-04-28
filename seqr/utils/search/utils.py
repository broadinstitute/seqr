from collections import defaultdict
from copy import deepcopy
from datetime import timedelta

from clickhouse_search.search import get_clickhouse_variants, format_clickhouse_results, format_clickhouse_export_results, \
    get_sorted_search_results, clickhouse_variant_lookup, InvalidSearchException
from seqr.models import Sample, VariantSearchResults
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_get_wildcard_json, safe_redis_set_json
from clickhouse_search.constants import XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from seqr.utils.xpos_utils import parse_variant_id
from seqr.views.utils.permissions_utils import user_is_analyst

logger = SeqrLogger(__name__)


MAX_EXPORT_VARIANTS = 1000


def export_variants(search_model, user):
    search_results = _query_variants(search_model, user)
    total_variants = len(search_results)
    if total_variants > MAX_EXPORT_VARIANTS:
        raise InvalidSearchException(f'Unable to export more than {MAX_EXPORT_VARIANTS} variants ({total_variants} requested)')
    return format_clickhouse_export_results(search_results)


def _get_clickhouse_exclude_keys(search_hash, user):
    previous_search_model = VariantSearchResults.objects.get(search_hash=search_hash)
    results = _query_variants(previous_search_model, user)
    exclude_keys = defaultdict(list)
    exclude_key_pairs = defaultdict(list)
    for variant in results:
        if isinstance(variant, list):
            dt1= variant_dataset_type(variant[0])
            dt2 = variant_dataset_type(variant[1])
            dataset_type = dt1 if dt1 == dt2 else ','.join(sorted([dt1, dt2]))
            exclude_key_pairs[dataset_type].append(sorted([variant[0]['key'], variant[1]['key']]))
        else:
            dataset_type = variant_dataset_type(variant)
            exclude_keys[dataset_type].append(variant['key'])
    return {'exclude_keys': dict(exclude_keys), 'exclude_key_pairs': dict(exclude_key_pairs)}


def variant_dataset_type(variant):
    if not parse_variant_id(variant['variantId']):
        sample_type = Sample.SAMPLE_TYPE_WGS if 'endChrom' in variant else Sample.SAMPLE_TYPE_WES
        return f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}'
    return Sample.DATASET_TYPE_MITO_CALLS if 'mitomapPathogenic' in variant else Sample.DATASET_TYPE_VARIANT_CALLS


def get_variant_query_gene_counts(search_model, user):
    results = _query_variants(search_model, user)
    flat_variants = [
        v for variants in results for v in (variants if isinstance(variants, list) else [variants])
    ]
    gene_aggs = defaultdict(lambda: {'total': 0, 'families': defaultdict(int)})
    for var in flat_variants:
        gene_ids = var['transcripts'].keys() if 'transcripts' in var else {t['geneId'] for t in var['sortedTranscriptConsequences']}
        for gene_id in gene_ids:
            gene_aggs[gene_id]['total'] += 1
            for family_guid in var['familyGuids']:
                gene_aggs[gene_id]['families'][family_guid] += 1
    return gene_aggs
