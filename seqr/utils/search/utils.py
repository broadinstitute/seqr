from collections import defaultdict
from datetime import timedelta
import elasticsearch
import elasticsearch_dsl

from settings import ELASTICSEARCH_SERVICE_HOSTNAME, ELASTICSEARCH_SERVICE_PORT, ELASTICSEARCH_CREDENTIALS, ELASTICSEARCH_PROTOCOL, ES_SSL_CONTEXT
from seqr.models import Sample
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.elasticsearch.constants import XPOS_SORT_KEY, MAX_VARIANTS
from seqr.utils.search.elasticsearch.es_gene_agg_search import EsGeneAggSearch
from seqr.utils.search.elasticsearch.es_search import EsSearch
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_xpos, get_chrom_pos
from seqr.views.utils.json_utils import  _to_camel_case


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


def ping_search_backend():
    if not get_es_client(timeout=3, max_retries=0).ping():
        raise ValueError('No response from elasticsearch ping')


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


def delete_es_index(index):
    client = get_es_client()
    client.indices.delete(index)
    updated_indices, _ = _get_es_indices(client)
    return updated_indices


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


SAMPLE_FIELDS_LIST = ['samples', 'samples_num_alt_1']
VCF_FILE_EXTENSIONS = ('.vcf', '.vcf.gz', '.vcf.bgz')
#  support .bgz instead of requiring .vcf.bgz due to issues with DSP delivery of large callsets
DATASET_FILE_EXTENSIONS = VCF_FILE_EXTENSIONS[:-1] + ('.bgz', '.bed', '.mt')

SEQR_DATSETS_GS_PATH = 'gs://seqr-datasets/v02'


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


def get_single_es_variant(families, variant_id, return_all_queried_families=False, user=None):
    variants = EsSearch(
        families, return_all_queried_families=return_all_queried_families, user=user,
    ).filter_by_variant_ids([variant_id]).search(num_results=1)
    if not variants:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return variants[0]


def get_es_variants_for_variant_ids(families, variant_ids, dataset_type=None, user=None):
    variants = EsSearch(families, user=user).filter_by_variant_ids(variant_ids)
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


def get_es_variants(search_model, es_search_cls=EsSearch, sort=XPOS_SORT_KEY, skip_genotype_filter=False, load_all=False, user=None, page=1, num_results=100):
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
