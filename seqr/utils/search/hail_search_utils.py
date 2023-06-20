from collections import defaultdict
from django.db.models import F, Min

import requests
from reference_data.models import Omim, GeneConstraint, GENOME_VERSION_LOOKUP
from seqr.models import Sample, PhenotypePrioritization
from seqr.utils.search.constants import PRIORITIZED_GENE_SORT
from seqr.utils.xpos_utils import MIN_POS, MAX_POS
from settings import HAIL_BACKEND_SERVICE_HOSTNAME, HAIL_BACKEND_SERVICE_PORT


def _hail_backend_url(path):
    return f'{HAIL_BACKEND_SERVICE_HOSTNAME}:{HAIL_BACKEND_SERVICE_PORT}/{path}'


def _execute_search(search_body, user, path='search'):
    response = requests.post(_hail_backend_url(path), json=search_body, headers={'From': user.email}, timeout=300)
    response.raise_for_status()
    return response.json()


def ping_hail_backend():
    requests.get(_hail_backend_url('status'), timeout=5).raise_for_status()


def get_hail_variants(samples, search, user, previous_search_results, genome_version, sort=None, page=1, num_results=100,
                      gene_agg=False, **kwargs):
    end_offset = num_results * page
    search_body = _format_search_body(samples, genome_version, end_offset, search)

    frequencies = search_body.pop('freqs', None)
    if frequencies and frequencies.get('callset'):
        frequencies['seqr'] = frequencies.pop('callset')

    search_body.update({
        'sort': sort,
        'sort_metadata': _get_sort_metadata(sort, samples),
        'frequencies': frequencies,
        'quality_filter': search_body.pop('qualityFilter', None),
        'custom_query': search_body.pop('customQuery', None),
    })
    search_body.pop('skipped_samples', None)

    _parse_location_search(search_body)

    path = 'gene_counts' if gene_agg else 'search'
    response_json = _execute_search(search_body, user, path)

    if gene_agg:
        previous_search_results['gene_aggs'] = response_json
        return response_json

    previous_search_results['total_results'] = response_json['total']
    previous_search_results['all_results'] = response_json['results']
    return response_json['results'][end_offset - num_results:end_offset]


def get_hail_variants_for_variant_ids(samples, genome_version, parsed_variant_ids, user, return_all_queried_families=False):
    search = {
        'variant_ids': [parsed_id for parsed_id in parsed_variant_ids.values() if parsed_id],
        'variant_keys': [variant_id for variant_id, parsed_id in parsed_variant_ids.items() if not parsed_id],
    }
    search_body = _format_search_body(samples, genome_version, len(parsed_variant_ids), search)
    response_json = _execute_search(search_body, user)

    if return_all_queried_families:
        expected_family_guids = set(samples.values_list('individual__family__guid', flat=True))
        _validate_expected_families(response_json['results'], expected_family_guids)

    return response_json['results']


def _format_search_body(samples, genome_version, num_results, search):
    search_body = {
        'genome_version': GENOME_VERSION_LOOKUP[genome_version],
        'num_results': num_results,
    }
    search_body.update(search)
    search_body['sample_data'] = _get_sample_data(samples, search_body.get('inheritance_filter'))
    return search_body


def _get_sample_data(samples, inheritance_filter):
    sample_data = samples.order_by('id').values(
        'sample_id', 'dataset_type', 'sample_type',
        individual_guid=F('individual__guid'),
        family_guid=F('individual__family__guid'),
        project_guid=F('individual__family__project__guid'),
        affected=F('individual__affected'),
        sex=F('individual__sex'),
    )

    custom_affected = (inheritance_filter or {}).pop('affected', None)
    if custom_affected:
        for s in sample_data:
            s['affected'] = custom_affected.get(s['individual_guid']) or s['affected']

    sample_data_by_data_type = defaultdict(list)
    for s in sample_data:
        dataset_type = s.pop('dataset_type')
        sample_type = s.pop('sample_type')
        data_type_key = f'{dataset_type}_{sample_type}' if dataset_type == Sample.DATASET_TYPE_SV_CALLS else dataset_type
        sample_data_by_data_type[data_type_key].append(s)

    return sample_data_by_data_type


def _get_sort_metadata(sort, samples):
    sort_metadata = None
    if sort == 'in_omim':
        sort_metadata = list(Omim.objects.filter(phenotype_mim_number__isnull=False).values_list('gene__gene_id', flat=True))
    elif sort == 'constraint':
        sort_metadata = {
            agg['gene__gene_id']: agg['mis_z_rank'] + agg['pLI_rank'] for agg in
            GeneConstraint.objects.values('gene__gene_id', 'mis_z_rank', 'pLI_rank')
        }
    elif sort == PRIORITIZED_GENE_SORT:
        sort_metadata = {
            agg['gene_id']: agg['min_rank'] for agg in PhenotypePrioritization.objects.filter(
                individual__family_id=samples[0].individual.family_id, rank__lte=100,
            ).values('gene_id').annotate(min_rank=Min('rank'))
        }
    return sort_metadata


def _parse_location_search(search):
    locus = search.pop('locus', None) or {}
    parsed_locus = search.pop('parsedLocus')

    genes = parsed_locus.get('genes') or {}
    intervals = parsed_locus.get('intervals')
    parsed_intervals = None
    if genes or intervals:
        gene_coords = [
            {field: gene[f'{field}{search["genome_version"].title()}'] for field in ['chrom', 'start', 'end']}
            for gene in genes.values()
        ]
        parsed_intervals = [_format_interval(**interval) for interval in intervals or []] + [
            '{chrom}:{start}-{end}'.format(**gene) for gene in gene_coords]

    exclude_locations = locus.get('excludeLocations')

    search.update({
        'intervals': parsed_intervals,
        'exclude_intervals': exclude_locations,
        'gene_ids': None if (exclude_locations or not genes) else list(genes.keys()),
        'variant_ids': parsed_locus.get('parsed_variant_ids'),
        'rs_ids': parsed_locus.get('rs_ids'),
    })


def _format_interval(chrom=None, start=None, end=None, offset=None, **kwargs):
    if offset:
        offset_pos = int((end - start) * offset)
        start = max(start - offset_pos, MIN_POS)
        end = min(end + offset_pos, MAX_POS)
    return f'{chrom}:{start}-{end}'


def _validate_expected_families(results, expected_families):
    # In the ES backed we could force return variants even if all families are hom ref
    # This is not possible in the hail backend as those rows are removed at loading, so fail if missing
    invalid_family_variants = []
    for result in results:
        missing_families = expected_families - set(result['familyGuids'])
        if missing_families:
            invalid_family_variants.append((result['variantId'], missing_families))

    if invalid_family_variants:
        from seqr.utils.search.utils import InvalidSearchException
        missing = ', '.join([
            f'{variant_id} ({"; ".join(sorted(families))})' for variant_id, families in invalid_family_variants
        ])
        raise InvalidSearchException(f'Unable to return all families for the following variants: {missing}')
