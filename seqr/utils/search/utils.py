from collections import defaultdict
from copy import deepcopy
from datetime import timedelta

from pyliftover.liftover import LiftOver

from clickhouse_search.search import get_clickhouse_variants, format_clickhouse_results, format_clickhouse_export_results, \
    get_sorted_search_results, clickhouse_variant_lookup, InvalidSearchException
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample, Project, VariantSearchResults
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_get_wildcard_json, safe_redis_set_json
from clickhouse_search.constants import XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_xpos, format_chrom
from seqr.views.utils.permissions_utils import user_is_analyst

logger = SeqrLogger(__name__)


MAX_GENES_FOR_FILTER = 10000
MIN_MULTI_FAMILY_SEQR_AC = 5000
MAX_EXPORT_VARIANTS = 1000


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


def get_single_variant(family, variant_id, user):
    parsed_variant_id = parse_variant_id(variant_id)
    parsed_variant_ids = [parsed_variant_id] if parsed_variant_id else None
    genome_version = family.project.genome_version
    variants = get_clickhouse_variants([family], user, genome_version, parsed_variant_ids=parsed_variant_ids, variant_ids=[variant_id])
    if not variants:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))
    return format_clickhouse_results(variants, genome_version)[0]


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

    parsed_variant_id = parse_variant_id(variant_id)
    variants = clickhouse_variant_lookup(user, variant_id, parsed_variant_id, sample_type, genome_version, affected_only, hom_only)

    safe_redis_set_json(cache_key, variants, expire=timedelta(weeks=2))
    return variants


def _get_search_cache_key(search_model, sort=None):
    return 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)


def export_variants(search_model, user):
    search_results, genome_version = _query_variants(search_model, user)
    total_variants = len(search_results)
    if total_variants > MAX_EXPORT_VARIANTS:
        raise InvalidSearchException(f'Unable to export more than {MAX_EXPORT_VARIANTS} variants ({total_variants} requested)')
    return format_clickhouse_export_results(search_results, genome_version)


def _get_previous_search_results(search_model, sort):
    previous_search_results = None
    if sort:
        cache_key = _get_search_cache_key(search_model, sort=sort)
        previous_search_results = safe_redis_get_json(cache_key) or []
    if not previous_search_results:
        wildcard_cache_key = _get_search_cache_key(search_model, sort='*')
        previous_search_results = safe_redis_get_wildcard_json(wildcard_cache_key)
        if previous_search_results and sort:
            previous_search_results = get_sorted_search_results(
                previous_search_results, sort, families=search_model.families.all(),
            )
            cache_key = _get_search_cache_key(search_model, sort=sort)
            safe_redis_set_json(cache_key, previous_search_results, expire=timedelta(weeks=2))
    return previous_search_results


def query_variants(search_model, sort, page, num_results, user):
    if sort == PATHOGENICTY_SORT_KEY and user_is_analyst(user):
        sort = PATHOGENICTY_HGMD_SORT_KEY
    all_results, genome_version = _query_variants(search_model, user, sort=sort or XPOS_SORT_KEY)

    results_page = format_clickhouse_results(all_results[(page-1)*num_results:page*num_results], genome_version)

    return results_page, len(all_results)


def _query_variants(search_model, user, sort=None):
    genome_version = _get_search_genome_version(search_model)
    previous_search_results = _get_previous_search_results(search_model, sort) or {}
    if previous_search_results:
        return previous_search_results, genome_version

    search = deepcopy(search_model.variant_search.search)
    families = search_model.families.all()

    parsed_search = _parse_search(search, genome_version, user)

    results = get_clickhouse_variants(families, user, genome_version, sort=sort, **parsed_search)

    cache_key = _get_search_cache_key(search_model, sort=sort)
    safe_redis_set_json(cache_key, results, expire=timedelta(weeks=2))

    return results, genome_version


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

    return parsed_search


def _get_clickhouse_exclude_keys(search_hash, user):
    previous_search_model = VariantSearchResults.objects.get(search_hash=search_hash)
    results, _ = _query_variants(previous_search_model, user)
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
    results, _ = _query_variants(search_model, user)
    flat_variants = [
        v for variants in results for v in (variants if isinstance(variants, list) else [variants])
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
