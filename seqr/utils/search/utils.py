from collections import defaultdict
from copy import deepcopy
from datetime import timedelta

from pyliftover.liftover import LiftOver

from clickhouse_search.search import get_clickhouse_variants, format_clickhouse_results, format_clickhouse_export_results, \
    get_clickhouse_cache_results, clickhouse_variant_lookup, get_clickhouse_variant_by_id, InvalidSearchException
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual, Project, VariantSearchResults
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_get_wildcard_json, safe_redis_set_json
from seqr.utils.search.constants import XPOS_SORT_KEY, PRIORITIZED_GENE_SORT, RECESSIVE, COMPOUND_HET, \
    MAX_NO_LOCATION_COMP_HET_FAMILIES, SV_ANNOTATION_TYPES, MAX_EXPORT_VARIANTS, X_LINKED_RECESSIVE
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_xpos, format_chrom

logger = SeqrLogger(__name__)


SEARCH_EXCEPTION_ERROR_MAP = {
    InvalidSearchException: 400,
}


MAX_GENES_FOR_FILTER = 10000
MIN_MULTI_FAMILY_SEQR_AC = 5000


def _get_filtered_search_samples(search_filter, active_only=True):
    # TODO clean up
    samples = Sample.objects.filter(**search_filter)
    if active_only:
        samples = samples.filter(is_active=True)
    return samples


def get_search_samples(projects, active_only=True):
    return _get_filtered_search_samples({'individual__family__project__in': projects}, active_only=active_only)


def _get_search_genome_version(search_model):
    projects = Project.objects.filter(family__in=search_model.families.all()).values_list('genome_version', 'name').distinct()
    project_versions = defaultdict(set)
    for genome_version, project_name in projects:
        project_versions[genome_version].add(project_name)

    if len(project_versions) > 1:
        summary = '; '.join(
            [f"{build} - {', '.join(sorted(projects))}" for build, projects in sorted(project_versions.items())])
        raise InvalidSearchException(
            f'Searching across multiple genome builds is not supported. Remove projects with differing genome builds from search: {summary}')

    if not project_versions:
        return search_model.variant_search.search.get('no_access_project_genome_version')

    return next(iter(project_versions.keys()))


def get_single_variant(family, variant_id, user=None):
    parsed_variant_id = parse_variant_id(variant_id)
    dataset_type = _variant_id_dataset_type(parsed_variant_id)
    samples = _get_filtered_search_samples({'individual__family_id': family.id})
    if len(samples) < 1:
        raise InvalidSearchException(f'No search data found for families {family.family_id}')
    variant = get_clickhouse_variant_by_id(
        variant_id, parsed_variant_id, samples, family.project.genome_version, dataset_type,
    )
    if not variant:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return variant


def variant_lookup(user, variant_id, genome_version, sample_type=None, affected_only=False, hom_only=False):
    cache_fields = ['variant_lookup_results', variant_id, genome_version]
    if affected_only:
        cache_fields.append('affected')
    if hom_only:
        cache_fields.append('hom')
    cache_key = '__'.join(cache_fields)
    variants = safe_redis_get_json(cache_key)
    if variants:
        return variants

    # TODO move into search helper func
    parsed_variant_id = parse_variant_id(variant_id)
    dataset_type = _variant_id_dataset_type(parsed_variant_id)
    _validate_dataset_type_genome_version(dataset_type, sample_type, genome_version)

    variants = clickhouse_variant_lookup(user, variant_id, parsed_variant_id, dataset_type, sample_type, genome_version, affected_only, hom_only)

    safe_redis_set_json(cache_key, variants, expire=timedelta(weeks=2))
    return variants


def _validate_dataset_type_genome_version(dataset_type, sample_type, genome_version):
    if genome_version == GENOME_VERSION_GRCh37 and dataset_type != Sample.DATASET_TYPE_VARIANT_CALLS:
        raise InvalidSearchException(f'{dataset_type} variants are not available for GRCh37')
    if dataset_type == Sample.DATASET_TYPE_SV_CALLS and not sample_type:
        raise InvalidSearchException('Sample type must be specified to look up a structural variant')


def _get_search_cache_key(search_model, sort=None):
    return 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)


def export_variants(search_model, user):
    previous_search_results, genome_version = _query_variants(search_model, user)
    total_variants = previous_search_results['total_results']
    if total_variants > MAX_EXPORT_VARIANTS:
        raise InvalidSearchException(f'Unable to export more than {MAX_EXPORT_VARIANTS} variants ({total_variants} requested)')
    return format_clickhouse_export_results(previous_search_results['all_results'], genome_version)


def _get_previous_search_results(search_model, sort):
    previous_search_results = None
    if sort:
        cache_key = _get_search_cache_key(search_model, sort=sort)
        previous_search_results = safe_redis_get_json(cache_key) or {}
    if not previous_search_results:
        wildcard_cache_key = _get_search_cache_key(search_model, sort='*')
        previous_search_results = safe_redis_get_wildcard_json(wildcard_cache_key)
        if previous_search_results and sort:
            previous_search_results = get_clickhouse_cache_results(
                previous_search_results['all_results'], sort, family_guid=search_model.families.first().guid,
            )
            cache_key = _get_search_cache_key(search_model, sort=sort)
            safe_redis_set_json(cache_key, previous_search_results, expire=timedelta(weeks=2))
    return previous_search_results


def query_variants(search_model, sort, page, num_results, user):
    resp = _query_variants(search_model, user, sort=sort)
    previous_search_results, genome_version = _query_variants(search_model, user, sort=sort)

    all_results = previous_search_results.get('all_results') or []
    results_page = format_clickhouse_results(all_results[(page-1)*num_results:page*num_results], genome_version)

    return results_page, previous_search_results.get('total_results')


def _query_variants(search_model, user, sort=None, **kwargs):
    genome_version = _get_search_genome_version(search_model)
    previous_search_results = _get_previous_search_results(search_model, sort) or {}
    if previous_search_results:
        return previous_search_results, genome_version

    search = deepcopy(search_model.variant_search.search)
    families = search_model.families.all()
    _validate_sort(sort, families)

    parsed_search = _parse_search(search, genome_version, user)
    dataset_types, secondary_dataset_types = _search_dataset_type(parsed_search, genome_version)
    _validate_search(parsed_search, families)

    samples = Sample.objects.filter(individual__family__in=families, is_active=True)
    if len(samples) < 1:
        if not parsed_search.get('no_access_project_genome_version'):
            raise InvalidSearchException('No search data found for families {}'.format(
                ', '.join([f.family_id for f in families])))
    if dataset_types:
        samples = samples.filter(dataset_type__in={*dataset_types, *(secondary_dataset_types or [])})
        if not samples and not parsed_search.get('no_access_project_genome_version'):
            raise InvalidSearchException(f'Unable to search against dataset type "{dataset_types[0]}"')
    if parsed_search.get('inheritance_mode') or parsed_search.get('inheritance_filter'):
        samples = samples.select_related('individual')
        if samples:
            skipped_samples = _filter_inheritance_family_samples(samples, parsed_search['inheritance_filter'])
            if skipped_samples:
                samples = samples.exclude(id__in=[s.id for s in skipped_samples])

    if (parsed_search.get('inheritance_mode') in {RECESSIVE, COMPOUND_HET}) and secondary_dataset_types:
        invalid_type = next((
            dts[0] for dts in [dataset_types, secondary_dataset_types]
            if dts and samples.filter(dataset_type__in=dts).count() < 1
        ), None)
        if invalid_type:
            raise InvalidSearchException(
                f'Unable to search for comp-het pairs with dataset type "{invalid_type}". This may be because inheritance based search is disabled in families with no loaded affected individuals'
            )

    get_clickhouse_variants(samples, parsed_search, user, previous_search_results, genome_version, sort=sort, **kwargs)

    cache_key = _get_search_cache_key(search_model, sort=sort)
    safe_redis_set_json(cache_key, previous_search_results, expire=timedelta(weeks=2))

    return previous_search_results, genome_version


def _parse_search(search, genome_version, user):
    no_access_project_genome_version = search.get('no_access_project_genome_version')
    locus = search.pop('locus', None) or {}
    exclude = search.get('exclude', None) or {}
    exclude_locations = bool(exclude.get('rawItems'))
    if locus and exclude_locations:
        raise InvalidSearchException('Cannot specify both Location and Excluded Genes/Intervals')

    parsed_search = {**search}
    genes, intervals, invalid_items = parse_locus_list_items(locus or exclude, genome_version=genome_version, additional_model_fields=['id'])
    if invalid_items:
        raise InvalidSearchException('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))
    if no_access_project_genome_version and len(genes or []) != 1:
        raise InvalidSearchException('Including external projects is only available when searching for a single gene')
    if (genes or intervals) and len(genes) + len(intervals) > MAX_GENES_FOR_FILTER:
        raise InvalidSearchException('Too many genes/intervals')
    parsed_search.update({'genes': genes, 'intervals': intervals, 'exclude_locations': exclude_locations})
    if not (genes or intervals):
        variant_ids, parsed_variant_ids, invalid_items = _parse_variant_items(locus)
        if invalid_items:
            raise InvalidSearchException('Invalid variants: {}'.format(', '.join(invalid_items)))
        parsed_search.update({'variant_ids': variant_ids, 'parsed_variant_ids': parsed_variant_ids})

    exclude.pop('rawItems', None)
    if exclude.get('clinvar') and (search.get('pathogenicity') or {}).get('clinvar'):
        duplicates = set(search['pathogenicity']['clinvar']).intersection(exclude['clinvar'])
        if duplicates:
            raise InvalidSearchException(f'ClinVar pathogenicity {", ".join(sorted(duplicates))} is both included and excluded')

    exclude.pop('previousSearch', None)
    exclude_previous_hash = exclude.pop('previousSearchHash', None)
    if exclude_previous_hash:
        parsed_search.update(_get_clickhouse_exclude_keys(exclude_previous_hash, user))

    for annotation_key in ['annotations', 'annotations_secondary']:
        if parsed_search.get(annotation_key):
            parsed_search[annotation_key] = {k: v for k, v in parsed_search[annotation_key].items() if v}

    if parsed_search.get('inheritance'):
        _parse_inheritance(parsed_search)

    return parsed_search


def _get_clickhouse_exclude_keys(search_hash, user):
    previous_search_model = VariantSearchResults.objects.get(search_hash=search_hash)
    cached_results, _ = _query_variants(previous_search_model, user)
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
    previous_search_results, _ = _query_variants(search_model, user)
    flat_variants = [
        v for variants in previous_search_results['all_results'] for v in (variants if isinstance(variants, list) else [variants])
    ]
    gene_aggs = defaultdict(lambda: {'total': 0, 'families': defaultdict(int)})
    for var in flat_variants:
        gene_ids = var['transcripts'].keys() if 'transcripts' in var else {t['geneId'] for t in var['sortedTranscriptConsequences']}
        for gene_id in gene_ids:
            gene_aggs[gene_id]['total'] += 1
            for family_guid in var['familyGuids']:
                gene_aggs[gene_id]['families'][family_guid] += 1
    return gene_aggs


def _parse_variant_items(search_json):
    raw_items = search_json.get('rawVariantItems')
    if not raw_items:
        return None, None, None

    invalid_items = []
    variant_ids = []
    parsed_variant_ids = []
    for item in raw_items.replace(',', ' ').split():
        variant_id = item.lstrip('chr')
        parsed_variant_id = parse_variant_id(variant_id)
        if parsed_variant_id:
            parsed_variant_ids.append(parsed_variant_id)
            variant_ids.append(variant_id)
        else:
            invalid_items.append(item)

    return variant_ids, parsed_variant_ids, invalid_items


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
    if sort == PRIORITIZED_GENE_SORT and len(families) != 1:
        raise InvalidSearchException('Phenotype sort is only supported for single-family search.')


def _search_dataset_type(search, genome_version):
    parsed_variant_ids = search.get('parsed_variant_ids')
    secondary_dataset_types = None
    if parsed_variant_ids:
        dataset_types = _chromosome_filter_dataset_types([vid[0] for vid in parsed_variant_ids])
    else:
        chroms = [gene[f'chromGrch{genome_version}'] for gene in (search.get('genes') or {}).values()] + [
            interval['chrom'] for interval in (search.get('intervals') or [])
        ] if not search.get('exclude_locations') else None
        dataset_types = _annotation_dataset_type(search.get('annotations'), chroms, pathogenicity=search.get('pathogenicity'), exclude_svs=search.pop('exclude_svs', False))
        secondary_dataset_types = _annotation_dataset_type(search['annotations_secondary'], chroms) if search.get('annotations_secondary') else None
        if secondary_dataset_types and len(dataset_types) == 0 and dataset_types[0] == Sample.DATASET_TYPE_SV_CALLS:
            secondary_dataset_types = [dt for dt in secondary_dataset_types if dt != Sample.DATASET_TYPE_MITO_CALLS]

    if search.get('inheritance_mode') == X_LINKED_RECESSIVE:
        if not dataset_types:
            dataset_types = [Sample.DATASET_TYPE_VARIANT_CALLS, Sample.DATASET_TYPE_SV_CALLS]
        elif Sample.DATASET_TYPE_MITO_CALLS in dataset_types:
            dataset_types.remove(Sample.DATASET_TYPE_MITO_CALLS)

    return dataset_types, secondary_dataset_types


def _variant_id_dataset_type(parsed_variant_id):
    if not parsed_variant_id:
        return Sample.DATASET_TYPE_SV_CALLS
    if parsed_variant_id[0].replace('chr', '').startswith('M'):
        return Sample.DATASET_TYPE_MITO_CALLS
    return Sample.DATASET_TYPE_VARIANT_CALLS


def _chromosome_filter_dataset_types(chroms):
    has_mito = [chrom for chrom in chroms if chrom.replace('chr', '').startswith('M')]
    if len(has_mito) == len(chroms):
        return [Sample.DATASET_TYPE_MITO_CALLS]
    dataset_types = [Sample.DATASET_TYPE_VARIANT_CALLS]
    if has_mito:
        dataset_types.append(Sample.DATASET_TYPE_MITO_CALLS)
    return dataset_types


def _annotation_dataset_type(annotations, chroms, pathogenicity=None, exclude_svs=False):
    if not (annotations or chroms):
        return [Sample.DATASET_TYPE_VARIANT_CALLS, Sample.DATASET_TYPE_MITO_CALLS] if (pathogenicity or exclude_svs) else None

    annotation_types = set((annotations or {}).keys())
    if annotations and annotation_types.issubset(SV_ANNOTATION_TYPES) and not pathogenicity:
        return [Sample.DATASET_TYPE_SV_CALLS]

    dataset_types = _chromosome_filter_dataset_types(chroms) if chroms else [Sample.DATASET_TYPE_VARIANT_CALLS, Sample.DATASET_TYPE_MITO_CALLS]

    no_svs = exclude_svs or (annotations and annotation_types.isdisjoint(SV_ANNOTATION_TYPES))
    if not no_svs:
        dataset_types.append(Sample.DATASET_TYPE_SV_CALLS)

    return dataset_types


def _parse_inheritance(search):
    inheritance = search.pop('inheritance')
    inheritance_mode = inheritance.get('mode')
    inheritance_filter = inheritance.get('filter') or {}

    if inheritance_filter.get('genotype'):
        inheritance_mode = None

    search.update({'inheritance_mode': inheritance_mode, 'inheritance_filter': inheritance_filter})

    if not inheritance_mode and list(inheritance_filter.keys()) == ['affected']:
        raise InvalidSearchException('Inheritance must be specified if custom affected status is set')


def _validate_search(search, families):
    has_comp_het_search = search.get('inheritance_mode') in {RECESSIVE, COMPOUND_HET}
    has_location_filter = any(search.get(field) for field in ['genes', 'intervals', 'variant_ids'])
    if has_comp_het_search:
        if not search.get('annotations'):
            raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

        if not has_location_filter and len(families) > MAX_NO_LOCATION_COMP_HET_FAMILIES:
            raise InvalidSearchException(
                'Location must be specified to search for compound heterozygous variants across many families')

        if search.get('no_access_project_genome_version'):
            raise InvalidSearchException('Compound heterozygous search is not supported when including external projects')

    if not has_location_filter and families.values('project_id').distinct().count() > 1:
        raise InvalidSearchException('Location must be specified to search across multiple projects')
    seqr_ac_filter = search.get('freqs', {}).get('callset', {}).get('ac') or (MIN_MULTI_FAMILY_SEQR_AC + 1)
    if seqr_ac_filter > MIN_MULTI_FAMILY_SEQR_AC and len(families) > 1:
        raise InvalidSearchException(
            f'seqr AC frequency of at least {MIN_MULTI_FAMILY_SEQR_AC} must be specified to search across multiple families'
        )


def _filter_inheritance_family_samples(samples, inheritance_filter):
    family_groups = defaultdict(set)
    individual_affected_status = inheritance_filter.get('affected') or {}
    genotype_filter = None if inheritance_filter.get(Individual.AFFECTED_STATUS_AFFECTED) else inheritance_filter.get('genotype')
    for sample in samples:
        if genotype_filter:
            is_filtered_family = sample.individual.guid in genotype_filter
        else:
            affected_status = individual_affected_status.get(sample.individual.guid) or sample.individual.affected
            is_filtered_family = affected_status == Individual.AFFECTED_STATUS_AFFECTED

        if is_filtered_family:
            family_groups[sample.individual.family_id].add(sample.dataset_type)

    if not family_groups:
        raise InvalidSearchException(
            'Invalid custom inheritance' if genotype_filter else
            'Inheritance based search is disabled in families with no data loaded for affected individuals'
        )

    return [
        s for s in samples if s.dataset_type not in family_groups[s.individual.family_id]
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
