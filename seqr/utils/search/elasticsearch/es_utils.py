from collections import defaultdict
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as EsConnectionError, TransportError
import elasticsearch_dsl
from urllib3.connectionpool import connection_from_url

from seqr.models import Sample
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.constants import VCF_FILE_EXTENSIONS, XPOS_SORT_KEY
from seqr.utils.search.elasticsearch.es_gene_agg_search import EsGeneAggSearch
from seqr.utils.search.elasticsearch.es_search import EsSearch, get_compound_het_page
from seqr.views.utils.json_utils import  _to_camel_case
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


def validate_es_index_metadata_and_get_samples(request_json, project):
    if 'elasticsearchIndex' not in request_json:
        raise ValueError('request must contain field: "elasticsearchIndex"')

    elasticsearch_index = request_json['elasticsearchIndex'].strip()
    kwargs = {
        'project': project,
        'dataset_type': request_json['datasetType'],
        'genome_version': request_json.get('genomeVersion'),
    }

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

    sample_ids = _get_es_sample_ids(elasticsearch_index, sample_field, es_client)
    sample_data = {'elasticsearch_index': elasticsearch_index}

    return sample_ids, sample_type, sample_data


def _get_es_sample_ids(elasticsearch_index, sample_field, es_client):
    s = elasticsearch_dsl.Search(using=es_client, index=elasticsearch_index)
    s = s.params(size=0)
    s.aggs.bucket('sample_ids', elasticsearch_dsl.A('terms', field=sample_field, size=10000))
    response = s.execute()
    return [agg['key'] for agg in response.aggregations.sample_ids.buckets]


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

    index_dataset_type = EsSearch.get_index_metadata_dataset_type(index_metadata)
    if index_dataset_type != dataset_type:
        raise ValueError('Index "{0}" has dataset type {1} but expects {2}'.format(
            elasticsearch_index, index_dataset_type, dataset_type
        ))


def delete_es_index(index):
    client = get_es_client()
    client.indices.delete(index)
    updated_indices, _ = _get_es_indices(client)
    return updated_indices


def get_elasticsearch_status():
    client = get_es_client()

    disk_status = {
        disk['node']: disk for disk in
        _get_es_meta(client, 'allocation', ['node', 'shards', 'disk.avail', 'disk.used', 'disk.percent'])
    }

    node_stats = {}
    for node in _get_es_meta(client, 'nodes', ['name', 'heap.percent']):
        if node['name'] in disk_status:
            disk_status[node.pop('name')].update(node)
        else:
            node_stats[node['name']] = node

    indices, seqr_index_projects = _get_es_indices(client)

    errors = ['{} does not exist and is used by project(s) {}'.format(
        index, ', '.join(['{} ({} samples)'.format(p.name, len(indivs)) for p, indivs in project_individuals.items()])
    ) for index, project_individuals in seqr_index_projects.items() if project_individuals]

    return {
        'indices': indices,
        'diskStats': list(disk_status.values()),
        'nodeStats': list(node_stats.values()),
        'errors': errors,
    }


def _get_es_meta(client, meta_type, fields, filter_rows=None):
    return [{
        _to_camel_case(field.replace('.', '_')): o[field] for field in fields
    } for o in getattr(client.cat, meta_type)(format="json", h=','.join(fields))
        if filter_rows is None or filter_rows(o)]


def _get_es_indices(client):
    indices = _get_es_meta(
        client, 'indices', ['index', 'docs.count', 'store.size', 'creation.date.string'],
        filter_rows=lambda index: all(
            not index['index'].startswith(omit_prefix) for omit_prefix in ['.', 'index_operations_log']))

    aliases = defaultdict(list)
    for alias in _get_es_meta(client, 'aliases', ['alias', 'index']):
        aliases[alias['alias']].append(alias['index'])

    index_metadata = get_index_metadata('_all', client, use_cache=False)

    active_samples = Sample.objects.filter(is_active=True, elasticsearch_index__isnull=False).select_related('individual__family__project')

    seqr_index_projects = defaultdict(lambda: defaultdict(set))
    es_projects = set()
    for sample in active_samples:
        for index_name in sample.elasticsearch_index.split(','):
            project = sample.individual.family.project
            es_projects.add(project)
            if index_name in aliases:
                for aliased_index_name in aliases[index_name]:
                    seqr_index_projects[aliased_index_name][project].add(sample.individual.guid)
            else:
                seqr_index_projects[index_name.rstrip('*')][project].add(sample.individual.guid)

    for index in indices:
        index_name = index['index']
        index.update(index_metadata[index_name])

        projects_for_index = []
        for index_prefix in list(seqr_index_projects.keys()):
            if index_name.startswith(index_prefix):
                projects_for_index += list(seqr_index_projects.pop(index_prefix).keys())
        index['projects'] = [
            {'projectGuid': project.guid, 'projectName': project.name} for project in projects_for_index]

    return indices, seqr_index_projects


def get_es_variants_for_variant_ids(samples, genome_version, variants_by_id, user, return_all_queried_families=False, **kwargs):
    variants = EsSearch(
        samples, genome_version, user=user, return_all_queried_families=return_all_queried_families, sort=XPOS_SORT_KEY,
    ).filter_by_variant_ids(list(variants_by_id.keys()))
    return variants.search(num_results=len(variants_by_id))


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
        **search.get('parsed_locus')

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
