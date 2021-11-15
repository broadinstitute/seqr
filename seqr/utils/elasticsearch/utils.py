from datetime import timedelta
import elasticsearch
from elasticsearch_dsl import Q

from settings import ELASTICSEARCH_SERVICE_HOSTNAME, ELASTICSEARCH_SERVICE_PORT, ELASTICSEARCH_CREDENTIALS, ELASTICSEARCH_PROTOCOL, ES_SSL_CONTEXT
from seqr.models import Sample
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.elasticsearch.constants import XPOS_SORT_KEY, MAX_VARIANTS
from seqr.utils.elasticsearch.es_gene_agg_search import EsGeneAggSearch
from seqr.utils.elasticsearch.es_search import EsSearch
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_xpos, get_chrom_pos


class InvalidIndexException(Exception):
    pass

class InvalidSearchException(Exception):
    pass


def get_es_client(timeout=60, **kwargs):
    client_kwargs = {
        'hosts': [{'host': ELASTICSEARCH_SERVICE_HOSTNAME, 'port': ELASTICSEARCH_SERVICE_PORT}],
        'timeout': timeout,
    }
    if ELASTICSEARCH_CREDENTIALS:
        client_kwargs['http_auth'] = ELASTICSEARCH_CREDENTIALS
    if ELASTICSEARCH_PROTOCOL:
        client_kwargs['scheme'] = ELASTICSEARCH_PROTOCOL
    if ES_SSL_CONTEXT:
        client_kwargs['ssl_context'] = ES_SSL_CONTEXT
    return elasticsearch.Elasticsearch(**client_kwargs, **kwargs)


def get_index_metadata(index_name, client, include_fields=False, use_cache=True):
    if use_cache:
        cache_key = 'index_metadata__{}'.format(index_name)
        cached_metadata = safe_redis_get_json(cache_key)
        if cached_metadata:
            return cached_metadata

    try:
        mappings = client.indices.get_mapping(index=index_name)
    except Exception as e:
        raise InvalidIndexException('{} - Error accessing index: {}'.format(
            index_name, e.error if hasattr(e, 'error') else str(e)))
    index_metadata = {}
    for index_name, mapping in mappings.items():
        variant_mapping = mapping['mappings']
        index_metadata[index_name] = variant_mapping.get('_meta', {})
        if include_fields:
            index_metadata[index_name]['fields'] = {
                field: field_props.get('type') for field, field_props in variant_mapping['properties'].items()
            }
    if use_cache and include_fields:
        # Only cache metadata with fields
        safe_redis_set_json(cache_key, index_metadata)
    return index_metadata


def get_single_es_variant(families, variant_id, return_all_queried_families=False, user=None):
    variants = EsSearch(
        families, return_all_queried_families=return_all_queried_families, user=user,
    ).filter_by_location(variant_ids=[variant_id]).search(num_results=1)
    if not variants:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return variants[0]


def get_es_variants_for_variant_ids(families, variant_ids, dataset_type=None, user=None):
    variants = EsSearch(families, user=user).filter_by_location(variant_ids=variant_ids)
    if dataset_type:
        variants = variants.update_dataset_type(dataset_type)
    return variants.search(num_results=len(variant_ids))


def get_es_variants_for_variant_tuples(families, xpos_ref_alt_tuples):
    variant_ids = []
    for xpos, ref, alt in xpos_ref_alt_tuples:
        chrom, pos = get_chrom_pos(xpos)
        if chrom == 'M':
            chrom = 'MT'
        variant_ids.append('{}-{}-{}-{}'.format(chrom, pos, ref, alt))
    return get_es_variants_for_variant_ids(families, variant_ids, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)


def get_es_variants(search_model, es_search_cls=EsSearch, sort=XPOS_SORT_KEY, skip_genotype_filter=False, load_all=False, user=None, **kwargs):
    cache_key = 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)
    previous_search_results = safe_redis_get_json(cache_key) or {}
    total_results = previous_search_results.get('total_results')

    previously_loaded_results, search_kwargs = es_search_cls.process_previous_results(previous_search_results, load_all=load_all, **kwargs)
    if previously_loaded_results is not None:
        return previously_loaded_results, previous_search_results.get('total_results')

    if load_all and total_results and int(total_results) >= int(MAX_VARIANTS):
        raise InvalidSearchException('Too many variants to load. Please refine your search and try again')

    search = search_model.variant_search.search

    genes, intervals, invalid_items = parse_locus_list_items(search.get('locus', {}))
    if invalid_items:
        raise InvalidSearchException('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))
    rs_ids, variant_ids, invalid_items = _parse_variant_items(search.get('locus', {}))
    if invalid_items:
        raise InvalidSearchException('Invalid variants: {}'.format(', '.join(invalid_items)))

    es_search = es_search_cls(
        search_model.families.all(),
        previous_search_results=previous_search_results,
        inheritance_search=search.get('inheritance'),
        user=user,
    )

    if search.get('customQuery'):
        custom_q = search['customQuery']
        if not isinstance(custom_q, list):
            custom_q = [custom_q]
        for q_dict in custom_q:
            es_search.filter(Q(q_dict))

    if sort:
        es_search.sort(sort)

    if genes or intervals or rs_ids or variant_ids:
        es_search.filter_by_location(
            genes=genes, intervals=intervals, rs_ids=rs_ids, variant_ids=variant_ids, locus=search['locus'])
        if (variant_ids or rs_ids) and not (genes or intervals) and not search['locus'].get('excludeLocations'):
            search_kwargs['num_results'] = len(variant_ids) + len(rs_ids)

    if search.get('freqs'):
        es_search.filter_by_frequency(search['freqs'], pathogenicity=search.get('pathogenicity'))

    if search.get('in_silico'):
        es_search.filter_by_in_silico(search['in_silico'])

    es_search.filter_by_annotation_and_genotype(
        search.get('inheritance'), quality_filter=search.get('qualityFilter'),
        annotations=search.get('annotations'), annotations_secondary=search.get('annotations_secondary'),
        pathogenicity=search.get('pathogenicity'), skip_genotype_filter=skip_genotype_filter)

    if hasattr(es_search, 'aggregate_by_gene'):
        es_search.aggregate_by_gene()

    variant_results = es_search.search(**search_kwargs)

    safe_redis_set_json(cache_key, es_search.previous_search_results, expire=timedelta(weeks=2))

    return variant_results, es_search.previous_search_results.get('total_results')


def get_es_variant_gene_counts(search_model, user):
    gene_counts, _ = get_es_variants(search_model, es_search_cls=EsGeneAggSearch, sort=None, user=user)
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
