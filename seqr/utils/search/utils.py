from datetime import timedelta

from seqr.models import Sample
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.constants import XPOS_SORT_KEY
from seqr.utils.search.elasticsearch.constants import MAX_VARIANTS
from seqr.utils.search.elasticsearch.es_gene_agg_search import EsGeneAggSearch
from seqr.utils.search.elasticsearch.es_search import EsSearch
from seqr.utils.search.elasticsearch.es_utils import ping_elasticsearch, delete_es_index, get_elasticsearch_status, \
    ES_EXCEPTION_ERROR_MAP, ES_EXCEPTION_MESSAGE_MAP, ES_ERROR_LOG_EXCEPTIONS
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_xpos


class InvalidSearchException(Exception):
    pass


SEARCH_EXCEPTION_ERROR_MAP = {
    InvalidSearchException: 400,
}
SEARCH_EXCEPTION_ERROR_MAP.update(ES_EXCEPTION_ERROR_MAP)

SEARCH_EXCEPTION_MESSAGE_MAP = {}
SEARCH_EXCEPTION_MESSAGE_MAP.update(ES_EXCEPTION_MESSAGE_MAP)

ERROR_LOG_EXCEPTIONS = set()
ERROR_LOG_EXCEPTIONS.update(ES_ERROR_LOG_EXCEPTIONS)


def ping_search_backend():
    ping_elasticsearch()


def get_search_backend_status():
    return get_elasticsearch_status()


def delete_search_backend_data(data_id):
    return delete_es_index(data_id)


def get_single_variant(families, variant_id, return_all_queried_families=False, user=None):
    variants = EsSearch(
        families, return_all_queried_families=return_all_queried_families, user=user,
    ).filter_by_variant_ids([variant_id]).search(num_results=1)
    if not variants:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return variants[0]


def get_variants_for_variant_ids(families, variant_ids, dataset_type=None, user=None):
    variants = EsSearch(families, user=user).filter_by_variant_ids(variant_ids)
    if dataset_type:
        variants = variants.update_dataset_type(dataset_type)
    return variants.search(num_results=len(variant_ids))


def query_variants(search_model, es_search_cls=EsSearch, sort=XPOS_SORT_KEY, skip_genotype_filter=False, load_all=False, user=None, page=1, num_results=100):
    cache_key = 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)
    previous_search_results = safe_redis_get_json(cache_key) or {}
    total_results = previous_search_results.get('total_results')

    previously_loaded_results, search_kwargs = es_search_cls.process_previous_results(previous_search_results, load_all=load_all, page=page, num_results=num_results)
    if previously_loaded_results is not None:
        return previously_loaded_results, previous_search_results.get('total_results')
    page = search_kwargs.get('page', page)
    num_results = search_kwargs.get('num_results', num_results)

    if load_all and total_results and int(total_results) >= int(MAX_VARIANTS):
        raise InvalidSearchException('Too many variants to load. Please refine your search and try again')

    search = search_model.variant_search.search

    rs_ids = None
    variant_ids = None
    genes, intervals, invalid_items = parse_locus_list_items(search.get('locus', {}))
    if invalid_items:
        raise InvalidSearchException('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))
    if not (genes or intervals):
        rs_ids, variant_ids, invalid_items = _parse_variant_items(search.get('locus', {}))
        if invalid_items:
            raise InvalidSearchException('Invalid variants: {}'.format(', '.join(invalid_items)))
        if rs_ids and variant_ids:
            raise InvalidSearchException('Invalid variant notation: found both variant IDs and rsIDs')

    es_search = es_search_cls(
        search_model.families.all(),
        previous_search_results=previous_search_results,
        user=user,
        sort=sort,
    )

    es_search.filter_variants(
        inheritance=search.get('inheritance'), frequencies=search.get('freqs'), pathogenicity=search.get('pathogenicity'),
        annotations=search.get('annotations'), annotations_secondary=search.get('annotations_secondary'),
        in_silico=search.get('in_silico'), quality_filter=search.get('qualityFilter'),
        custom_query=search.get('customQuery'), locus=search.get('locus'),
        genes=genes, intervals=intervals, rs_ids=rs_ids, variant_ids=variant_ids,
        skip_genotype_filter=skip_genotype_filter,
    )

    if variant_ids:
        num_results = len(variant_ids)

    variant_results = es_search.search(page=page, num_results=num_results)

    safe_redis_set_json(cache_key, es_search.previous_search_results, expire=timedelta(weeks=2))

    return variant_results, es_search.previous_search_results.get('total_results')


def get_variant_query_gene_counts(search_model, user):
    gene_counts, _ = query_variants(search_model, es_search_cls=EsGeneAggSearch, sort=None, user=user)
    return gene_counts


def _parse_variant_items(search_json):
    raw_items = search_json.get('rawVariantItems')
    if not raw_items:
        return None, None, None

    invalid_items = []
    variant_ids = []
    rs_ids = []
    for item in raw_items.replace(',', ' ').split():
        if item.startswith('rs'):
            rs_ids.append(item)
        else:
            try:
                chrom, pos, _, _ = EsSearch.parse_variant_id(item)
                get_xpos(chrom, pos)
                variant_ids.append(item.lstrip('chr'))
            except (KeyError, ValueError):
                invalid_items.append(item)

    return rs_ids, variant_ids, invalid_items
