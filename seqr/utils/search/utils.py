from collections import defaultdict
from datetime import timedelta
import elasticsearch

from seqr.models import Sample
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.constants import XPOS_SORT_KEY
from seqr.utils.search.elasticsearch.constants import MAX_VARIANTS
from seqr.utils.search.elasticsearch.es_gene_agg_search import EsGeneAggSearch
from seqr.utils.search.elasticsearch.es_search import EsSearch
from seqr.utils.search.elasticsearch.es_utils import get_es_client, get_index_metadata, InvalidIndexException, \
    ES_EXCEPTION_ERROR_MAP, ES_EXCEPTION_MESSAGE_MAP, ES_ERROR_LOG_EXCEPTIONS
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_xpos, get_chrom_pos
from seqr.views.utils.json_utils import  _to_camel_case


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
