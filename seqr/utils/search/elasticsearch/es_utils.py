from collections import defaultdict
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as EsConnectionError, TransportError
from urllib3.connectionpool import connection_from_url

from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.constants import VCF_FILE_EXTENSIONS, XPOS_SORT_KEY
from seqr.utils.search.elasticsearch.es_gene_agg_search import EsGeneAggSearch
from seqr.utils.search.elasticsearch.es_search import EsSearch, get_compound_het_page
from settings import ELASTICSEARCH_SERVICE_HOSTNAME, ELASTICSEARCH_SERVICE_PORT, ELASTICSEARCH_CREDENTIALS, \
    ELASTICSEARCH_PROTOCOL, ES_SSL_CONTEXT, KIBANA_SERVER


class InvalidIndexException(Exception):
    pass


ES_EXCEPTION_ERROR_MAP = {
    InvalidIndexException: 400,
    EsConnectionError: 504,
    TransportError: lambda e: int(e.status_code) if e.status_code != 'N/A' else 400,
}
ES_EXCEPTION_MESSAGE_MAP = {
    EsConnectionError: str,
    TransportError: lambda e: '{}: {} - {} - {}'.format(e.__class__.__name__, e.status_code, repr(e.error), _get_transport_error_type(e.info)),
}
ES_ERROR_LOG_EXCEPTIONS = {InvalidIndexException}

MAX_VARIANTS_FETCH = 1000


def _get_transport_error_type(error):
    error_type = 'no detail'
    if isinstance(error, dict):
        root_cause = error.get('root_cause')
        error_info = error.get('error')
        if (not root_cause) and isinstance(error_info, dict):
            root_cause = error_info.get('root_cause')

        if root_cause:
            error_type = root_cause[0].get('type') or root_cause[0].get('reason')
        elif error_info and not isinstance(error_info, dict):
            error_type = repr(error_info)
    return error_type


def es_backend_enabled():
    return bool(ELASTICSEARCH_SERVICE_HOSTNAME)


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
    return Elasticsearch(**client_kwargs, **kwargs)


def ping_elasticsearch():
    if not get_es_client(timeout=3, max_retries=0).ping():
        raise ValueError('No response from elasticsearch ping')


def ping_kibana():
    resp = connection_from_url('http://{}'.format(KIBANA_SERVER)).urlopen('HEAD', '/status', timeout=3, retries=3)
    if resp.status >= 400:
        raise ValueError('Kibana Error {}: {}'.format(resp.status, resp.reason))


SAMPLE_FIELDS_LIST = ['samples', 'samples_num_alt_1']
#  support .bgz instead of requiring .vcf.bgz due to issues with DSP delivery of large callsets
DATASET_FILE_EXTENSIONS = VCF_FILE_EXTENSIONS[:-1] + ('.bgz', '.bed', '.mt')


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


def get_es_variants_for_variant_ids(samples, genome_version, variant_ids, user):
    variant_ids = sorted(set(variant_ids))
    variants = EsSearch(
        samples, genome_version, user=user, sort=XPOS_SORT_KEY,
    ).filter_by_variant_ids(variant_ids)
    return variants.search(num_results=len(variant_ids))


def get_es_variants(samples, search, user, previous_search_results, genome_version, sort=None, page=None, num_results=None,
                    gene_agg=False, skip_genotype_filter=False):
    es_search_cls = EsGeneAggSearch if gene_agg else EsSearch

    es_search = es_search_cls(
        samples,
        genome_version,
        previous_search_results=previous_search_results,
        user=user,
        sort=sort,
        skipped_samples=search.get('skipped_samples'),
    )

    es_search.filter_variants(
        inheritance_mode=search.get('inheritance_mode'), inheritance_filter=search.get('inheritance_filter'),
        frequencies=search.get('freqs'), pathogenicity=search.get('pathogenicity'),
        annotations=search.get('annotations'), annotations_secondary=search.get('annotations_secondary'),
        in_silico=search.get('in_silico'), quality_filter=search.get('qualityFilter'),
        custom_query=search.get('customQuery'), locus=search.get('locus'), skip_genotype_filter=skip_genotype_filter,
        dataset_type=search.get('dataset_type'), secondary_dataset_type=search.get('secondary_dataset_type'),
        genes=search.get('genes'), intervals=search.get('intervals'), rs_ids=search.get('rs_ids'),
        variant_ids=search.get('variant_ids'), exclude_locations=search.get('exclude_locations'),
    )

    return es_search.search(page=page, num_results=num_results)


def process_es_previously_loaded_results(previous_search_results, start_index, end_index):
    grouped_results = previous_search_results.get('grouped_results')
    results = None
    if grouped_results:
        results = get_compound_het_page(grouped_results, start_index, end_index)

    return results


def process_es_previously_loaded_gene_aggs(previous_search_results):
    total_results = previous_search_results.get('total_results')
    if total_results is None or 'all_results' in previous_search_results or 'grouped_results' not in previous_search_results:
        return None

    loaded = sum(counts.get('loaded', 0) for counts in previous_search_results.get('loaded_variant_counts', {}).values())
    if loaded != total_results:
        return None

    gene_aggs = defaultdict(lambda: {'total': 0, 'families': defaultdict(int)})

    for group in previous_search_results['grouped_results']:
        variants = next(iter(group.values()))
        gene_id = next(iter(group))
        if not gene_id or gene_id == 'null':
            gene_id = next((
                gene_id for gene_id, transcripts in variants[0]['transcripts'].items()
                if any(t['transcriptId'] == variants[0]['mainTranscriptId'] for t in transcripts)
            ), None) if variants[0]['mainTranscriptId'] else None
        if gene_id:
            gene_aggs[gene_id]['total'] += len(variants)
            for family_guid in variants[0]['familyGuids']:
                gene_aggs[gene_id]['families'][family_guid] += len(variants)
    return gene_aggs

