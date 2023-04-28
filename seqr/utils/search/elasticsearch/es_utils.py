from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as EsConnectionError, TransportError
import elasticsearch_dsl

from seqr.models import Sample
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.constants import VCF_FILE_EXTENSIONS
from settings import ELASTICSEARCH_SERVICE_HOSTNAME, ELASTICSEARCH_SERVICE_PORT, ELASTICSEARCH_CREDENTIALS, \
    ELASTICSEARCH_PROTOCOL, ES_SSL_CONTEXT


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


def validate_index_metadata_and_get_samples(elasticsearch_index, **kwargs):
    es_client = get_es_client()

    all_index_metadata = get_index_metadata(elasticsearch_index, es_client, include_fields=True)
    if elasticsearch_index in all_index_metadata:
        index_metadata = all_index_metadata.get(elasticsearch_index)
        _validate_index_metadata(index_metadata, elasticsearch_index, **kwargs)
        sample_field = _get_samples_field(index_metadata)
        sample_type = index_metadata['sampleType']
    else:
        # Aliases return the mapping for all indices in the alias
        metadatas = list(all_index_metadata.values())
        sample_field = _get_samples_field(metadatas[0])
        sample_type = metadatas[0]['sampleType']
        for metadata in metadatas[1:]:
            _validate_index_metadata(metadata, elasticsearch_index, **kwargs)
            if sample_field != _get_samples_field(metadata):
                raise ValueError('Found mismatched sample fields for indices in alias')
            if sample_type != metadata['sampleType']:
                raise ValueError('Found mismatched sample types for indices in alias')

    s = elasticsearch_dsl.Search(using=es_client, index=elasticsearch_index)
    s = s.params(size=0)
    s.aggs.bucket('sample_ids', elasticsearch_dsl.A('terms', field=sample_field, size=10000))
    response = s.execute()
    return [agg['key'] for agg in response.aggregations.sample_ids.buckets], sample_type


def _get_samples_field(index_metadata):
    return next((field for field in SAMPLE_FIELDS_LIST if field in index_metadata['fields'].keys()))


def _validate_index_metadata(index_metadata, elasticsearch_index, project=None, genome_version=None,
                            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS):
    metadata_fields = ['genomeVersion', 'sampleType', 'sourceFilePath']
    if any(field not in (index_metadata or {}) for field in metadata_fields):
        raise ValueError("Index metadata must contain fields: {}".format(', '.join(metadata_fields)))

    sample_type = index_metadata['sampleType']
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        raise ValueError("Sample type not supported: {}".format(sample_type))

    if index_metadata['genomeVersion'] != (genome_version or project.genome_version):
        raise ValueError('Index "{0}" has genome version {1} but this project uses version {2}'.format(
            elasticsearch_index, index_metadata['genomeVersion'], project.genome_version
        ))

    dataset_path = index_metadata['sourceFilePath']
    if not dataset_path.endswith(DATASET_FILE_EXTENSIONS):
        raise ValueError("Variant call dataset path must end with {}".format(' or '.join(DATASET_FILE_EXTENSIONS)))

    if index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS) != dataset_type:
        raise ValueError('Index "{0}" has dataset type {1} but expects {2}'.format(
            elasticsearch_index, index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS), dataset_type
        ))
