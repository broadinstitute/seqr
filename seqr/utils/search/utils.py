from collections import defaultdict
from datetime import timedelta

from seqr.models import Sample, Project
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.constants import XPOS_SORT_KEY, PRIORITIZED_GENE_SORT
from seqr.utils.search.elasticsearch.constants import MAX_VARIANTS
from seqr.utils.search.elasticsearch.es_utils import ping_elasticsearch, delete_es_index, get_elasticsearch_status, \
    get_es_variants, get_es_variants_for_variant_ids, process_es_previously_loaded_results, process_es_previously_loaded_gene_aggs, \
    es_backend_enabled, ES_EXCEPTION_ERROR_MAP, ES_EXCEPTION_MESSAGE_MAP, ES_ERROR_LOG_EXCEPTIONS
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


def _no_backend_error(*args, **kwargs):
    raise InvalidSearchException('Elasticsearch backend is disabled')


def backend_specific_call(es_func, other_func=_no_backend_error):
    if es_backend_enabled():
        return es_func
    else:
        return other_func


def ping_search_backend():
    backend_specific_call(ping_elasticsearch)()


def get_search_backend_status():
    return backend_specific_call(get_elasticsearch_status)()


def _get_filtered_search_samples(search_filter, active_only=True):
    samples = Sample.objects.filter(elasticsearch_index__isnull=False, **search_filter)
    if active_only:
        samples = samples.filter(is_active=True)
    return samples


def get_search_samples(projects, active_only=True):
    return _get_filtered_search_samples({'individual__family__project__in': projects}, active_only=active_only)


def delete_search_backend_data(data_id):
    active_samples = Sample.objects.filter(is_active=True, elasticsearch_index=data_id)
    if active_samples:
        projects = set(active_samples.values_list('individual__family__project__name', flat=True))
        raise InvalidSearchException(f'"{data_id}" is still used by: {", ".join(projects)}')

    return backend_specific_call(delete_es_index)(data_id)


def get_single_variant(families, variant_id, return_all_queried_families=False, user=None):
    variants = backend_specific_call(get_es_variants_for_variant_ids)(
        *_get_families_search_data(families), [variant_id], user, return_all_queried_families=return_all_queried_families,
    )
    if not variants:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return variants[0]


def get_variants_for_variant_ids(families, variant_ids, dataset_type=None, user=None):
    return backend_specific_call(get_es_variants_for_variant_ids)(
        *_get_families_search_data(families), variant_ids, user, dataset_type=dataset_type,
    )


def _get_search_cache_key(search_model, sort=None):
    return 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)


def _get_cached_search_results(search_model, sort=None):
    return safe_redis_get_json(_get_search_cache_key(search_model, sort=sort)) or {}


def query_variants(search_model, sort=XPOS_SORT_KEY, skip_genotype_filter=False, load_all=False, user=None, page=1, num_results=100):
    previous_search_results = _get_cached_search_results(search_model, sort=sort)
    total_results = previous_search_results.get('total_results')

    if load_all:
        num_results = total_results or MAX_VARIANTS
    start_index = (page - 1) * num_results
    end_index = page * num_results
    if total_results is not None:
        end_index = min(end_index, total_results)

    loaded_results = previous_search_results.get('all_results') or []
    if len(loaded_results) >= end_index:
        return loaded_results[start_index:end_index], total_results

    previously_loaded_results = backend_specific_call(
        process_es_previously_loaded_results,
        lambda *args: None,  # Other backends need no additional parsing
    )(previous_search_results, start_index, end_index)
    if previously_loaded_results is not None:
        return previously_loaded_results, total_results

    if load_all and total_results and int(total_results) >= int(MAX_VARIANTS):
        raise InvalidSearchException('Too many variants to load. Please refine your search and try again')

    return _query_variants(
        search_model, user, previous_search_results, sort=sort, page=page, num_results=num_results,
        skip_genotype_filter=skip_genotype_filter)


def _query_variants(search_model, user, previous_search_results, sort=None, num_results=100, **kwargs):
    search = search_model.variant_search.search

    rs_ids = None
    variant_ids = None
    parsed_variant_ids = None
    genes, intervals, invalid_items = parse_locus_list_items(search.get('locus', {}))
    if invalid_items:
        raise InvalidSearchException('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))
    if not (genes or intervals):
        rs_ids, variant_ids, parsed_variant_ids, invalid_items = _parse_variant_items(search.get('locus', {}))
        if invalid_items:
            raise InvalidSearchException('Invalid variants: {}'.format(', '.join(invalid_items)))
        if rs_ids and variant_ids:
            raise InvalidSearchException('Invalid variant notation: found both variant IDs and rsIDs')

    if variant_ids:
        num_results = len(variant_ids)

    parsed_search = {
        'parsedLocus': {
            'genes': genes, 'intervals': intervals, 'rs_ids': rs_ids, 'variant_ids': variant_ids,
            'parsed_variant_ids': parsed_variant_ids,
        },
    }
    parsed_search.update(search)

    families = search_model.families.all()
    _validate_sort(sort, families)
    samples, genome_version = _get_families_search_data(families)

    variant_results = backend_specific_call(get_es_variants)(
        samples, parsed_search, user, previous_search_results, genome_version,
        sort=sort, num_results=num_results, **kwargs,
    )

    cache_key = _get_search_cache_key(search_model, sort=sort)
    safe_redis_set_json(cache_key, previous_search_results, expire=timedelta(weeks=2))

    return variant_results, previous_search_results.get('total_results')


def get_variant_query_gene_counts(search_model, user):
    previous_search_results = _get_cached_search_results(search_model)
    if previous_search_results.get('gene_aggs'):
        return previous_search_results['gene_aggs']

    if len(previous_search_results.get('all_results', [])) == previous_search_results.get('total_results'):
        return _get_gene_aggs_for_cached_variants(previous_search_results)

    previously_loaded_results = backend_specific_call(
        process_es_previously_loaded_gene_aggs,
        lambda *args: None,  # Other backends need no additional parsing
    )(previous_search_results)
    if previously_loaded_results is not None:
        return previously_loaded_results

    gene_counts, _ = _query_variants(search_model, user, previous_search_results, gene_agg=True)
    return gene_counts


def _get_gene_aggs_for_cached_variants(previous_search_results):
    gene_aggs = defaultdict(lambda: {'total': 0, 'families': defaultdict(int)})
    for var in previous_search_results['all_results']:
        gene_id = next((
            gene_id for gene_id, transcripts in var['transcripts'].items()
            if any(t['transcriptId'] == var['mainTranscriptId'] for t in transcripts)
        ), None) if var['mainTranscriptId'] else None
        if gene_id:
            gene_aggs[gene_id]['total'] += 1
            for family_guid in var['familyGuids']:
                gene_aggs[gene_id]['families'][family_guid] += 1
    return gene_aggs


def _parse_variant_items(search_json):
    raw_items = search_json.get('rawVariantItems')
    if not raw_items:
        return None, None, None, None

    invalid_items = []
    variant_ids = []
    parsed_variant_ids = []
    rs_ids = []
    for item in raw_items.replace(',', ' ').split():
        if item.startswith('rs'):
            rs_ids.append(item)
        else:
            try:
                variant_id = item.lstrip('chr')
                chrom, pos, ref, alt = variant_id.split('-')
                pos = int(pos)
                get_xpos(chrom, pos)
                variant_ids.append(variant_id)
                parsed_variant_ids.append((chrom, pos, ref, alt))
            except (KeyError, ValueError):
                invalid_items.append(item)

    return rs_ids, variant_ids, parsed_variant_ids, invalid_items


def _validate_sort(sort, families):
    if sort == PRIORITIZED_GENE_SORT and len(families) > 1:
        raise InvalidSearchException('Phenotype sort is only supported for single-family search.')


def _get_families_search_data(families):
    samples = _get_filtered_search_samples({'individual__family__in': families})
    if len(samples) < 1:
        raise InvalidSearchException('No search data found for families {}'.format(
            ', '.join([f.family_id for f in families])))

    projects = Project.objects.filter(family__individual__sample__in=samples).values_list('genome_version', 'name')
    project_versions = defaultdict(set)
    for genome_version, project_name in projects:
        project_versions[genome_version].add(project_name)

    if len(project_versions) > 1:
        summary = '; '.join(
            [f"{build} - {', '.join(sorted(projects))}" for build, projects in project_versions.items()])
        raise InvalidSearchException(
            f'Searching across multiple genome builds is not supported. Remove projects with differing genome builds from search: {summary}')

    return samples, next(iter(project_versions.keys()))
