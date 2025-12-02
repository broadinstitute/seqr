from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
from django.db.models import Count
from pyliftover.liftover import LiftOver

from clickhouse_search.search import get_clickhouse_variants, format_clickhouse_results, \
    get_clickhouse_cache_results, clickhouse_variant_lookup, get_clickhouse_variant_by_id
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual, Project, VariantSearchResults
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_get_wildcard_json, safe_redis_set_json
from seqr.utils.search.constants import XPOS_SORT_KEY, PRIORITIZED_GENE_SORT, RECESSIVE, COMPOUND_HET, \
    MAX_NO_LOCATION_COMP_HET_FAMILIES, SV_ANNOTATION_TYPES, ALL_DATA_TYPES, MAX_EXPORT_VARIANTS, X_LINKED_RECESSIVE, \
    MAX_VARIANTS
from seqr.utils.search.elasticsearch.es_utils import ping_elasticsearch, \
    get_es_variants, get_es_variants_for_variant_ids, process_es_previously_loaded_results, process_es_previously_loaded_gene_aggs, \
    es_backend_enabled, ping_kibana, ES_EXCEPTION_ERROR_MAP, ES_EXCEPTION_MESSAGE_MAP, ES_ERROR_LOG_EXCEPTIONS
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_xpos, format_chrom

logger = SeqrLogger(__name__)

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
        [Sample.DATASET_TYPE_MITO_CALLS],
        [Sample.DATASET_TYPE_SV_CALLS],
    ]
}
DATASET_TYPES_LOOKUP[ALL_DATA_TYPES] = [dt for dts in DATASET_TYPES_LOOKUP.values() for dt in dts]
DATASET_TYPE_SNP_INDEL_ONLY = f'{Sample.DATASET_TYPE_VARIANT_CALLS}_only'
DATASET_TYPES_LOOKUP[DATASET_TYPE_SNP_INDEL_ONLY] = [Sample.DATASET_TYPE_VARIANT_CALLS]
DATASET_TYPE_NO_MITO = f'{Sample.DATASET_TYPE_MITO_CALLS}_missing'
DATASET_TYPES_LOOKUP[DATASET_TYPE_NO_MITO] = [Sample.DATASET_TYPE_VARIANT_CALLS, Sample.DATASET_TYPE_SV_CALLS]


def es_only(func):
    def _wrapped(*args, **kwargs):
        if not es_backend_enabled():
            raise ValueError(f'{func.__name__} is disabled without the elasticsearch backend')
        return func(*args, **kwargs)
    return _wrapped


def clickhouse_only(func):
    def _wrapped(*args, **kwargs):
        if es_backend_enabled():
            raise ValueError(f'{func.__name__} is disabled without the clickhouse backend')
        return func(*args, **kwargs)
    return _wrapped


def backend_specific_call(es_func, clickhouse_func):
    if es_backend_enabled():
        return es_func
    else:
        return clickhouse_func


def ping_search_backend():
    # Clickhouse backend does not need special uptime testing, will be checked with the other database connection pings
    backend_specific_call(ping_elasticsearch, lambda: None)()


def ping_search_backend_admin():
    backend_specific_call(ping_kibana, lambda: True)()


def _get_filtered_search_samples(search_filter, active_only=True):
    samples = Sample.objects.filter(**search_filter)
    if active_only:
        samples = samples.filter(is_active=True)
    return samples


def get_search_samples(projects, active_only=True):
    return _get_filtered_search_samples({'individual__family__project__in': projects}, active_only=active_only)


def _get_families_search_data(families, dataset_type, sample_filter=None):
    samples = _get_filtered_search_samples(sample_filter or {'individual__family__in': families})
    if len(samples) < 1:
        raise InvalidSearchException('No search data found for families {}'.format(
            ', '.join([f.family_id for f in families])))

    if dataset_type:
        samples = samples.filter(dataset_type__in=DATASET_TYPES_LOOKUP[dataset_type])
        if not samples:
            raise InvalidSearchException(f'Unable to search against dataset type "{dataset_type}"')

    return samples


def _get_search_genome_version(families):
    projects = Project.objects.filter(family__in=families).values_list('genome_version', 'name').distinct()
    project_versions = defaultdict(set)
    for genome_version, project_name in projects:
        project_versions[genome_version].add(project_name)

    if len(project_versions) > 1:
        summary = '; '.join(
            [f"{build} - {', '.join(sorted(projects))}" for build, projects in sorted(project_versions.items())])
        raise InvalidSearchException(
            f'Searching across multiple genome builds is not supported. Remove projects with differing genome builds from search: {summary}')

    return next(iter(project_versions.keys()))


def get_single_variant(family, variant_id, user=None):
    parsed_variant_id = parse_variant_id(variant_id)
    dataset_type = _variant_ids_dataset_type([parsed_variant_id])
    samples = _get_families_search_data([family], dataset_type, sample_filter={'individual__family_id': family.id})
    variant = backend_specific_call(
        _get_es_variant_by_id,
        _get_clickhouse_variant_by_id,
    )(parsed_variant_id, variant_id, samples, family.project.genome_version, dataset_type=dataset_type, user=user)
    if not variant:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return variant


def _get_es_variant_by_id(parsed_variant_id, variant_id, samples, genome_version, user=None, **kwargs):
    variants = get_es_variants_for_variant_ids(samples, genome_version, [variant_id], user)
    return variants[0] if variants else None


def _get_clickhouse_variant_by_id(parsed_variant_id, variant_id, samples, genome_version, dataset_type=None, **kwargs):
    return get_clickhouse_variant_by_id(
        parsed_variant_id or variant_id, samples, genome_version, DATASET_TYPES_LOOKUP[dataset_type][0],
    )


@clickhouse_only
def variant_lookup(user, variant_id, genome_version, sample_type=None, affected_only=False, hom_only=False):
    cache_key = f'variant_lookup_results__{variant_id}__{genome_version}'
    variants = safe_redis_get_json(cache_key)
    if variants:
        return variants

    parsed_variant_id = parse_variant_id(variant_id)
    dataset_type = DATASET_TYPES_LOOKUP[_variant_ids_dataset_type([parsed_variant_id])][0]
    _validate_dataset_type_genome_version(dataset_type, sample_type, genome_version)

    variants = clickhouse_variant_lookup(user, parsed_variant_id or variant_id, dataset_type, sample_type, genome_version, affected_only, hom_only)

    safe_redis_set_json(cache_key, variants, expire=timedelta(weeks=2))
    return variants


def _validate_dataset_type_genome_version(dataset_type, sample_type, genome_version):
    if genome_version == GENOME_VERSION_GRCh37 and dataset_type != Sample.DATASET_TYPE_VARIANT_CALLS:
        raise InvalidSearchException(f'{dataset_type} variants are not available for GRCh37')
    if dataset_type == Sample.DATASET_TYPE_SV_CALLS and not sample_type:
        raise InvalidSearchException('Sample type must be specified to look up a structural variant')


def _get_search_cache_key(search_model, sort=None):
    return 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)


def _get_any_sort_cached_results(search_model):
    cache_key = _get_search_cache_key(search_model, sort='*')
    return safe_redis_get_wildcard_json(cache_key)


def _get_cached_search_results(search_model, sort=None):
    cache_key = _get_search_cache_key(search_model, sort=sort)
    return safe_redis_get_json(cache_key) or {}


def _validate_export_variant_count(total_variants):
    if total_variants > MAX_EXPORT_VARIANTS:
        raise InvalidSearchException(f'Unable to export more than {MAX_EXPORT_VARIANTS} variants ({total_variants} requested)')


def _get_elasticsearch_previous_search_results(search_model, sort, page, num_results, load_all, **kwargs):
    previous_search_results = _get_cached_search_results(search_model, sort=sort)
    start_index, end_index, num_results = _get_result_range(page, num_results, previous_search_results.get('total_results'), load_all)

    cached_page = None
    loaded_results = previous_search_results.get('all_results') or []
    if len(loaded_results) >= end_index:
        cached_page = loaded_results[start_index:end_index]

    if not cached_page:
        cached_page = process_es_previously_loaded_results(previous_search_results, start_index, end_index)

    return previous_search_results, cached_page, num_results


def _get_clickhouse_previous_search_results(search_model, sort, page, num_results, load_all, genome_version=None):
    previous_search_results = _get_cached_search_results(search_model, sort=sort)
    if not previous_search_results:
        unsorted_results = _get_any_sort_cached_results(search_model)
        if unsorted_results:
            previous_search_results = get_clickhouse_cache_results(
                unsorted_results['all_results'], sort, family_guid=search_model.families.first().guid,
            )
            cache_key = _get_search_cache_key(search_model, sort=sort)
            safe_redis_set_json(cache_key, previous_search_results, expire=timedelta(weeks=2))

    start_index, end_index, num_results = _get_result_range(page, num_results, previous_search_results.get('total_results'), load_all)
    cached_page = None
    loaded_results = previous_search_results.get('all_results') or []
    if len(loaded_results) >= end_index:
        cached_page = format_clickhouse_results(loaded_results[start_index:end_index], genome_version)

    return previous_search_results, cached_page, num_results


def _get_result_range(page, num_results, total_results, load_all):
    if load_all:
        num_results = total_results or MAX_EXPORT_VARIANTS
        _validate_export_variant_count(num_results)
    start_index = (page - 1) * num_results
    end_index = page * num_results
    if total_results is not None:
        end_index = min(end_index, total_results)

    if end_index > MAX_VARIANTS:
        raise InvalidSearchException(f'Unable to load more than {MAX_VARIANTS} variants ({end_index} requested)')

    return start_index, end_index, num_results


def query_variants(search_model, sort=XPOS_SORT_KEY, skip_genotype_filter=False, load_all=False, user=None, page=1, num_results=100):
    genome_version = _get_search_genome_version(search_model.families.all())
    previous_search_results, cached_page, num_results = backend_specific_call(
        _get_elasticsearch_previous_search_results,
        _get_clickhouse_previous_search_results,
    )(search_model, sort, page, num_results, load_all, genome_version=genome_version)
    if cached_page is not None:
        return cached_page, previous_search_results.get('total_results')

    variants, total_results = _query_variants(
        search_model, user, previous_search_results, genome_version, sort=sort, page=page, num_results=num_results,
        skip_genotype_filter=skip_genotype_filter)

    if load_all:
        _validate_export_variant_count(total_results)

    return variants, total_results


def _query_variants(search_model, user, previous_search_results, genome_version, sort=None, num_results=100, **kwargs):
    search = deepcopy(search_model.variant_search.search)

    families = search_model.families.all()
    _validate_sort(sort, families)

    locus = search.pop('locus', None) or {}
    exclude = search.get('exclude', None) or {}
    exclude_locations = bool(exclude.get('rawItems'))
    if locus and exclude_locations:
        raise InvalidSearchException('Cannot specify both Location and Excluded Genes/Intervals')

    variant_ids = None
    parsed_search = {**search}
    genes, intervals, invalid_items = parse_locus_list_items(locus or exclude, genome_version=genome_version, additional_model_fields=['id'])
    if invalid_items:
        raise InvalidSearchException('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))
    parsed_search.update({'genes': genes, 'intervals': intervals, 'exclude_locations': exclude_locations})
    if not (genes or intervals):
        rs_ids, variant_ids, parsed_variant_ids, invalid_items = _parse_variant_items(locus)
        if invalid_items:
            raise InvalidSearchException('Invalid variants: {}'.format(', '.join(invalid_items)))
        if rs_ids and variant_ids:
            raise InvalidSearchException('Invalid variant notation: found both variant IDs and rsIDs')
        parsed_search.update({'rs_ids': rs_ids, 'variant_ids': variant_ids, 'parsed_variant_ids': parsed_variant_ids})

    if variant_ids:
        num_results = len(variant_ids)

    exclude.pop('rawItems', None)
    if exclude.get('clinvar') and (search.get('pathogenicity') or {}).get('clinvar'):
        duplicates = set(search['pathogenicity']['clinvar']).intersection(exclude['clinvar'])
        if duplicates:
            raise InvalidSearchException(f'ClinVar pathogenicity {", ".join(sorted(duplicates))} is both included and excluded')

    exclude.pop('previousSearch', None)
    exclude_previous_hash = exclude.pop('previousSearchHash', None)
    if exclude_previous_hash:
        parsed_search.update(backend_specific_call(
            lambda *args: {}, _get_clickhouse_exclude_keys,
        )(exclude_previous_hash, user, genome_version))

    for annotation_key in ['annotations', 'annotations_secondary']:
        if parsed_search.get(annotation_key):
            parsed_search[annotation_key] = {k: v for k, v in parsed_search[annotation_key].items() if v}

    dataset_type, secondary_dataset_type, lookup_dataset_type = _search_dataset_type(parsed_search, genome_version)
    parsed_search.update({'dataset_type': None if dataset_type == DATASET_TYPE_NO_MITO else dataset_type, 'secondary_dataset_type': secondary_dataset_type})
    search_dataset_type = None
    if dataset_type and dataset_type != ALL_DATA_TYPES:
        if secondary_dataset_type is None or secondary_dataset_type == dataset_type:
            search_dataset_type = lookup_dataset_type or dataset_type
        elif dataset_type == Sample.DATASET_TYPE_SV_CALLS:
            search_dataset_type = DATASET_TYPE_NO_MITO

    samples = _get_families_search_data(families, dataset_type=search_dataset_type)
    if parsed_search.get('inheritance'):
        samples = _parse_inheritance(parsed_search, samples)

    _validate_search(parsed_search, samples, previous_search_results)

    variant_results = backend_specific_call(get_es_variants, get_clickhouse_variants)(
        samples, parsed_search, user, previous_search_results, genome_version,
        sort=sort, num_results=num_results, **kwargs,
    )

    cache_key = _get_search_cache_key(search_model, sort=sort)
    safe_redis_set_json(cache_key, previous_search_results, expire=timedelta(weeks=2))

    return variant_results, previous_search_results.get('total_results')


def _get_clickhouse_exclude_keys(search_hash, user, genome_version):
    previous_search_model = VariantSearchResults.objects.get(search_hash=search_hash)
    cached_results = _get_any_sort_cached_results(previous_search_model)
    if not cached_results:
        cached_results = {}
        _query_variants(previous_search_model, user, cached_results, genome_version)
    results = cached_results['all_results']
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
    return backend_specific_call(
        _get_es_variant_query_gene_counts,
        _get_clickhouse_variant_query_gene_counts,
    )(search_model, user)


def _get_es_variant_query_gene_counts(search_model, user):
    previous_search_results = _get_cached_search_results(search_model)
    if previous_search_results.get('gene_aggs'):
        return previous_search_results['gene_aggs']

    if len(previous_search_results.get('all_results', [])) == previous_search_results.get('total_results'):
        return _get_gene_aggs_for_cached_variants(
            previous_search_results['all_results'],
            lambda v: next((
                [gene_id] for gene_id, transcripts in v['transcripts'].items()
                if any(t['transcriptId'] == v['mainTranscriptId'] for t in transcripts)
            ), []) if v['mainTranscriptId'] else [],
        )

    previously_loaded_results = process_es_previously_loaded_gene_aggs(previous_search_results)
    if previously_loaded_results is not None:
        return previously_loaded_results

    genome_version = _get_search_genome_version(search_model.families.all())
    gene_counts, _ = _query_variants(search_model, user, previous_search_results, genome_version, gene_agg=True)
    return gene_counts


def _get_clickhouse_variant_query_gene_counts(search_model, user):
    previous_search_results = _get_any_sort_cached_results(search_model) or {}
    if len(previous_search_results.get('all_results', [])) != previous_search_results.get('total_results'):
        genome_version = _get_search_genome_version(search_model.families.all())
        _query_variants(search_model, user, previous_search_results, genome_version)

    return _get_gene_aggs_for_cached_variants([
        v for variants in previous_search_results['all_results'] for v in (variants if isinstance(variants, list) else [variants])
    ], lambda v: v['transcripts'].keys() if 'transcripts' in v else {t['geneId'] for t in v['sortedTranscriptConsequences']})


def _get_gene_aggs_for_cached_variants(variants, get_variant_genes):
    gene_aggs = defaultdict(lambda: {'total': 0, 'families': defaultdict(int)})
    for var in variants:
        gene_ids = get_variant_genes(var)
        for gene_id in gene_ids:
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
            variant_id = item.lstrip('chr')
            parsed_variant_id = parse_variant_id(variant_id)
            if parsed_variant_id:
                parsed_variant_ids.append(parsed_variant_id)
                variant_ids.append(variant_id)
            else:
                invalid_items.append(item)

    return rs_ids, variant_ids, parsed_variant_ids, invalid_items


def parse_variant_id(variant_id):
    try:
        return _parse_valid_variant_id(variant_id)
    except (KeyError, ValueError):
        return None


def _parse_valid_variant_id(variant_id):
    chrom, pos, ref, alt = variant_id.split('-')
    chrom = format_chrom(chrom)
    pos = int(pos)
    get_xpos(chrom, pos)
    return chrom, pos, ref, alt


def _validate_sort(sort, families):
    if sort == PRIORITIZED_GENE_SORT and len(families) > 1:
        raise InvalidSearchException('Phenotype sort is only supported for single-family search.')


def _search_dataset_type(search, genome_version):
    parsed_variant_ids = search.get('parsed_variant_ids')
    rsids = search.get('rs_ids')
    if parsed_variant_ids or rsids:
        lookup_dataset_type = Sample.DATASET_TYPE_VARIANT_CALLS if rsids else _variant_ids_dataset_type(parsed_variant_ids)
        return Sample.DATASET_TYPE_VARIANT_CALLS, None, lookup_dataset_type

    chroms = [gene[f'chromGrch{genome_version}'] for gene in (search.get('genes') or {}).values()] + [
        interval['chrom'] for interval in (search.get('intervals') or [])
    ] if not search.get('exclude_locations') else None
    dataset_type = _annotation_dataset_type(search.get('annotations'), chroms, pathogenicity=search.get('pathogenicity'), exclude_svs=search.pop('exclude_svs', False))
    secondary_dataset_type = _annotation_dataset_type(search['annotations_secondary'], chroms) if search.get('annotations_secondary') else None

    return dataset_type, secondary_dataset_type, None


def _variant_ids_dataset_type(all_variant_ids):
    variant_ids = [v for v in all_variant_ids if v]
    any_sv = len(variant_ids) < len(all_variant_ids)
    if len(variant_ids) == 0:
        return Sample.DATASET_TYPE_SV_CALLS
    return  _chromosome_filter_dataset_type([vid[0] for vid in variant_ids], any_sv)

def _chromosome_filter_dataset_type(chroms, any_sv):
    has_mito = [chrom for chrom in chroms if chrom.replace('chr', '').startswith('M')]
    if len(has_mito) == len(chroms):
        return Sample.DATASET_TYPE_MITO_CALLS
    elif not has_mito:
        return DATASET_TYPE_NO_MITO if any_sv else DATASET_TYPE_SNP_INDEL_ONLY
    return ALL_DATA_TYPES if any_sv else Sample.DATASET_TYPE_VARIANT_CALLS


def _annotation_dataset_type(annotations, chroms, pathogenicity=None, exclude_svs=False):
    if not (annotations or chroms):
        return Sample.DATASET_TYPE_VARIANT_CALLS if (pathogenicity or exclude_svs) else None

    annotation_types = set((annotations or {}).keys())
    if annotations and annotation_types.issubset(SV_ANNOTATION_TYPES) and not pathogenicity:
        return Sample.DATASET_TYPE_SV_CALLS

    no_svs = exclude_svs or (annotations and annotation_types.isdisjoint(SV_ANNOTATION_TYPES))
    if chroms:
        return _chromosome_filter_dataset_type(chroms, any_sv=not no_svs)
    elif no_svs:
        return Sample.DATASET_TYPE_VARIANT_CALLS
    return ALL_DATA_TYPES


def _parse_inheritance(search, samples):
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

    if inheritance_mode == X_LINKED_RECESSIVE:
        samples = samples.exclude(dataset_type=Sample.DATASET_TYPE_MITO_CALLS)

    samples = samples.select_related('individual')
    skipped_samples = _filter_inheritance_family_samples(samples, inheritance_filter)
    if skipped_samples:
        search['skipped_samples'] = skipped_samples
        samples = samples.exclude(id__in=[s.id for s in skipped_samples])

    return samples


def _validate_search(search, samples, previous_search_results):
    has_comp_het_search = search.get('inheritance_mode') in {RECESSIVE, COMPOUND_HET} and not previous_search_results.get('grouped_results')
    has_location_filter = any(search.get(field) for field in ['genes', 'intervals', 'variant_ids'])
    if has_comp_het_search:
        if not search.get('annotations'):
            raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

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

    if not has_location_filter:
        backend_specific_call(lambda *args: None, _validate_no_location_search)(samples)


MAX_FAMILY_COUNTS = {Sample.SAMPLE_TYPE_WES: 200, Sample.SAMPLE_TYPE_WGS: 35}


def _validate_no_location_search(samples):
    variant_samples = samples.filter(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
    if variant_samples.values('individual__family__project_id').distinct().count() > 1:
        raise InvalidSearchException('Location must be specified to search across multiple projects')
    sample_counts = samples.filter(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS).values('sample_type').annotate(
        family_count=Count('individual__family_id', distinct=True),
    )
    if any(sample_count['family_count'] > MAX_FAMILY_COUNTS[sample_count['sample_type']] for sample_count in sample_counts):
        raise InvalidSearchException('Location must be specified to search across multiple families in large projects')


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


LIFTOVERS = {
    GENOME_VERSION_GRCh38: None,
    GENOME_VERSION_GRCh37: None,
}
PYLIFTOVER_BUILD_LOOKUP = {
    GENOME_VERSION_GRCh38: ('hg19', 'hg38'),
    GENOME_VERSION_GRCh37: ('hg38', 'hg19'),
}
def _get_liftover(genome_version):
    if not LIFTOVERS[genome_version]:
        try:
            LIFTOVERS[genome_version] = LiftOver(*PYLIFTOVER_BUILD_LOOKUP[genome_version])
        except Exception as e:
            logger.error('ERROR: Unable to set up liftover. {}'.format(e), user=None)
    return LIFTOVERS[genome_version]


def run_liftover(genome_version, chrom, pos):
    liftover = _get_liftover(genome_version)
    if not liftover:
        return None
    lifted_coord = liftover.convert_coordinate(
        'chr{}'.format(chrom.lstrip('chr')), int(pos)
    )
    if lifted_coord and lifted_coord[0]:
        return (lifted_coord[0][0].lstrip('chr'), lifted_coord[0][1])
    return None
