from collections import defaultdict
from copy import deepcopy
from datetime import timedelta

from seqr.models import Sample, Individual, Project
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.search.constants import XPOS_SORT_KEY, PRIORITIZED_GENE_SORT, RECESSIVE, COMPOUND_HET, \
    MAX_NO_LOCATION_COMP_HET_FAMILIES, SV_ANNOTATION_TYPES, ALL_DATA_TYPES, MAX_EXPORT_VARIANTS
from seqr.utils.search.elasticsearch.constants import MAX_VARIANTS
from seqr.utils.search.elasticsearch.es_utils import ping_elasticsearch, delete_es_index, get_elasticsearch_status, \
    get_es_variants, get_es_variants_for_variant_ids, process_es_previously_loaded_results, process_es_previously_loaded_gene_aggs, \
    es_backend_enabled, ping_kibana, ES_EXCEPTION_ERROR_MAP, ES_EXCEPTION_MESSAGE_MAP, ES_ERROR_LOG_EXCEPTIONS
from seqr.utils.search.hail_search_utils import get_hail_variants, get_hail_variants_for_variant_ids, ping_hail_backend
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

DATASET_TYPES_LOOKUP = {
    data_types[0]: data_types for data_types in [
        [Sample.DATASET_TYPE_VARIANT_CALLS, Sample.DATASET_TYPE_MITO_CALLS],
        [Sample.DATASET_TYPE_SV_CALLS],
    ]
}
DATASET_TYPES_LOOKUP[ALL_DATA_TYPES] = [dt for dts in DATASET_TYPES_LOOKUP.values() for dt in dts]


def _raise_search_error(error):
    def _wrapped(*args, **kwargs):
        raise InvalidSearchException(error)
    return _wrapped


def backend_specific_call(es_func, other_func):
    if es_backend_enabled():
        return es_func
    else:
        return other_func


def ping_search_backend():
    backend_specific_call(ping_elasticsearch, ping_hail_backend)()


def ping_search_backend_admin():
    backend_specific_call(ping_kibana, lambda: True)()


def get_search_backend_status():
    return backend_specific_call(get_elasticsearch_status, _raise_search_error('Elasticsearch is disabled'))()


def _get_filtered_search_samples(search_filter, active_only=True):
    samples = Sample.objects.filter(elasticsearch_index__isnull=False, **search_filter)
    if active_only:
        samples = samples.filter(is_active=True)
    return samples


def get_search_samples(projects, active_only=True):
    return _get_filtered_search_samples({'individual__family__project__in': projects}, active_only=active_only)


def _get_families_search_data(families, dataset_type=None):
    samples = _get_filtered_search_samples({'individual__family__in': families})
    if len(samples) < 1:
        raise InvalidSearchException('No search data found for families {}'.format(
            ', '.join([f.family_id for f in families])))

    if dataset_type:
        samples = samples.filter(dataset_type__in=DATASET_TYPES_LOOKUP[dataset_type])
        if not samples:
            raise InvalidSearchException(f'Unable to search against dataset type "{dataset_type}"')

    projects = Project.objects.filter(family__individual__sample__in=samples).values_list('genome_version', 'name')
    project_versions = defaultdict(set)
    for genome_version, project_name in projects:
        project_versions[genome_version].add(project_name)

    if len(project_versions) > 1:
        summary = '; '.join(
            [f"{build} - {', '.join(sorted(projects))}" for build, projects in sorted(project_versions.items())])
        raise InvalidSearchException(
            f'Searching across multiple genome builds is not supported. Remove projects with differing genome builds from search: {summary}')

    return samples, next(iter(project_versions.keys()))


def delete_search_backend_data(data_id):
    active_samples = Sample.objects.filter(is_active=True, elasticsearch_index=data_id)
    if active_samples:
        projects = set(active_samples.values_list('individual__family__project__name', flat=True))
        raise InvalidSearchException(f'"{data_id}" is still used by: {", ".join(projects)}')

    return backend_specific_call(
        delete_es_index, _raise_search_error('Deleting indices is disabled for the hail backend'),
    )(data_id)


def get_single_variant(families, variant_id, return_all_queried_families=False, user=None):
    variants = _get_variants_for_variant_ids(
        families, [variant_id], user, return_all_queried_families=return_all_queried_families,
    )
    if not variants:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return variants[0]


def get_variants_for_variant_ids(families, variant_ids, dataset_type=None, user=None):
    return _get_variants_for_variant_ids(families, variant_ids, user, dataset_type=dataset_type)


def _get_variants_for_variant_ids(families, variant_ids, user, dataset_type=None, **kwargs):
    parsed_variant_ids = {}
    for variant_id in variant_ids:
        try:
            parsed_variant_ids[variant_id] = _parse_variant_id(variant_id)
        except (KeyError, ValueError):
            parsed_variant_ids[variant_id] = None

    if dataset_type:
        parsed_variant_ids = {
            k: v for k, v in parsed_variant_ids.items()
            if (dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS and v) or
               (dataset_type != Sample.DATASET_TYPE_VARIANT_CALLS and not v)
        }
    elif all(v for v in parsed_variant_ids.values()):
        dataset_type = Sample.DATASET_TYPE_VARIANT_CALLS
    elif all(v is None for v in parsed_variant_ids.values()):
        dataset_type = Sample.DATASET_TYPE_SV_CALLS

    return backend_specific_call(get_es_variants_for_variant_ids, get_hail_variants_for_variant_ids)(
        *_get_families_search_data(families, dataset_type=dataset_type), parsed_variant_ids, user, **kwargs
    )


def _get_search_cache_key(search_model, sort=None):
    return 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)


def _get_cached_search_results(search_model, sort=None):
    return safe_redis_get_json(_get_search_cache_key(search_model, sort=sort)) or {}


def _validate_export_variant_count(total_variants):
    if total_variants > MAX_EXPORT_VARIANTS:
        raise InvalidSearchException(f'Unable to export more than {MAX_EXPORT_VARIANTS} variants ({total_variants} requested)')


def query_variants(search_model, sort=XPOS_SORT_KEY, skip_genotype_filter=False, load_all=False, user=None, page=1, num_results=100):
    previous_search_results = _get_cached_search_results(search_model, sort=sort)
    total_results = previous_search_results.get('total_results')

    if load_all:
        num_results = total_results or MAX_EXPORT_VARIANTS
        _validate_export_variant_count(num_results)
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

    if end_index > MAX_VARIANTS:
        raise InvalidSearchException(f'Unable to load more than {MAX_VARIANTS} variants ({end_index} requested)')

    variants, total_results = _query_variants(
        search_model, user, previous_search_results, sort=sort, page=page, num_results=num_results,
        skip_genotype_filter=skip_genotype_filter)

    if load_all:
        _validate_export_variant_count(total_results)

    return variants, total_results


def _query_variants(search_model, user, previous_search_results, sort=None, num_results=100, **kwargs):
    search = deepcopy(search_model.variant_search.search)

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

    dataset_type, secondary_dataset_type = _search_dataset_type(parsed_search)
    parsed_search.update({'dataset_type': dataset_type, 'secondary_dataset_type': secondary_dataset_type})
    search_dataset_type = None
    if dataset_type and dataset_type != ALL_DATA_TYPES and (secondary_dataset_type is None or secondary_dataset_type == dataset_type):
        search_dataset_type = dataset_type

    samples, genome_version = _get_families_search_data(families, dataset_type=search_dataset_type)
    if parsed_search.get('inheritance'):
        samples = _parse_inheritance(parsed_search, samples, previous_search_results)

    variant_results = backend_specific_call(get_es_variants, get_hail_variants)(
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
                parsed_variant_ids.append(_parse_variant_id(variant_id))
                variant_ids.append(variant_id)
            except (KeyError, ValueError):
                invalid_items.append(item)

    return rs_ids, variant_ids, parsed_variant_ids, invalid_items


def _parse_variant_id(variant_id):
    chrom, pos, ref, alt = variant_id.split('-')
    pos = int(pos)
    get_xpos(chrom, pos)
    return chrom, pos, ref, alt


def _validate_sort(sort, families):
    if sort == PRIORITIZED_GENE_SORT and len(families) > 1:
        raise InvalidSearchException('Phenotype sort is only supported for single-family search.')


def _search_dataset_type(search):
    if search['parsedLocus']['variant_ids']:
        return Sample.DATASET_TYPE_VARIANT_CALLS, None

    dataset_type = _annotation_dataset_type(search.get('annotations'))
    secondary_dataset_type = _annotation_dataset_type(search.get('annotations_secondary'))
    return dataset_type, secondary_dataset_type


def _annotation_dataset_type(annotations):
    if not annotations:
        return None

    annotation_types = {k for k, v in annotations.items() if v}
    if annotation_types.issubset(SV_ANNOTATION_TYPES):
        return Sample.DATASET_TYPE_SV_CALLS
    elif annotation_types.isdisjoint(SV_ANNOTATION_TYPES):
        return Sample.DATASET_TYPE_VARIANT_CALLS
    return ALL_DATA_TYPES


def _parse_inheritance(search, samples, previous_search_results):
    inheritance = search.pop('inheritance')
    inheritance_mode = inheritance.get('mode')
    inheritance_filter = inheritance.get('filter') or {}

    if inheritance_filter.get('genotype'):
        inheritance_mode = None

    search.update({'inheritance_mode': inheritance_mode, 'inheritance_filter': inheritance_filter})
    if not (inheritance_mode or inheritance_filter):
        return samples

    if not inheritance_mode and list(inheritance_filter.keys()) == ['affected']:
        raise InvalidSearchException('Inheritance must be specified if custom affected status is set')

    samples = samples.select_related('individual')
    skipped_samples = _filter_inheritance_family_samples(samples, inheritance_filter)
    if skipped_samples:
        search['skipped_samples'] = skipped_samples
        samples = samples.exclude(id__in=[s.id for s in skipped_samples])

    has_comp_het_search = inheritance_mode in {RECESSIVE, COMPOUND_HET} and not previous_search_results.get('grouped_results')
    if has_comp_het_search:
        if not search.get('annotations'):
            raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

        has_location_filter = bool(search['parsedLocus']['genes'] or search['parsedLocus']['intervals'])
        family_ids = {s.individual.family_id for s in samples.select_related('individual')}
        if not has_location_filter and len(family_ids) > MAX_NO_LOCATION_COMP_HET_FAMILIES:
            raise InvalidSearchException(
                'Location must be specified to search for compound heterozygous variants across many families')

        if search['secondary_dataset_type']:
            invalid_type = next((
                dt for dt in [search['dataset_type'], search['secondary_dataset_type']]
                if dt and dt != ALL_DATA_TYPES and samples.filter(dataset_type__in=DATASET_TYPES_LOOKUP[dt]).count() < 1
            ), None)
            if invalid_type:
                raise InvalidSearchException(
                    f'Unable to search for comp-het pairs with dataset type "{invalid_type}". This may be because inheritance based search is disabled in families with no loaded affected individuals'
                )

    return samples


def _filter_inheritance_family_samples(samples, inheritance_filter):
    family_groups = defaultdict(set)
    sample_group_field = backend_specific_call('elasticsearch_index', 'dataset_type')
    individual_affected_status = inheritance_filter.get('affected') or {}
    genotype_filter = None if inheritance_filter.get(Individual.AFFECTED_STATUS_AFFECTED) else inheritance_filter.get('genotype')
    for sample in samples:
        if genotype_filter:
            is_filtered_family = sample.individual.guid in genotype_filter
        else:
            affected_status = individual_affected_status.get(sample.individual.guid) or sample.individual.affected
            is_filtered_family = affected_status == Individual.AFFECTED_STATUS_AFFECTED

        if is_filtered_family:
            family_groups[sample.individual.family_id].add(getattr(sample, sample_group_field))

    if not family_groups:
        raise InvalidSearchException(
            'Invalid custom inheritance' if genotype_filter else
            'Inheritance based search is disabled in families with no data loaded for affected individuals'
        )

    return [
        s for s in samples if getattr(s, sample_group_field) not in family_groups[s.individual.family_id]
    ]
