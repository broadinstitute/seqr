from collections import defaultdict

from django.db.models import F, Min, Count, Case, When
from urllib3.connectionpool import connection_from_url

import requests
from reference_data.models import Omim, GeneConstraint, GENOME_VERSION_LOOKUP
from seqr.models import Sample, PhenotypePrioritization, Individual
from seqr.utils.search.constants import PRIORITIZED_GENE_SORT, X_LINKED_RECESSIVE
from seqr.utils.xpos_utils import MIN_POS, MAX_POS
from settings import HAIL_BACKEND_SERVICE_HOSTNAME, HAIL_BACKEND_SERVICE_PORT


def _hail_backend_url(path):
    return f'http://{HAIL_BACKEND_SERVICE_HOSTNAME}:{HAIL_BACKEND_SERVICE_PORT}/{path}'

def _execute_search(search_body, user, path='search', exception_map=None, user_email=None):
    response = requests.post(_hail_backend_url(path), json=search_body, headers={'From': user_email or user.email}, timeout=300)

    if response.status_code >= 400:
        error = (exception_map or {}).get(response.status_code) or response.text or response.reason
        raise requests.HTTPError(error, response=response)

    return response.json()


def ping_hail_backend():
    response = connection_from_url(_hail_backend_url('status')).urlopen('HEAD', '/status', timeout=5, retries=3)
    if response.status >= 400:
        raise requests.HTTPError(f'{response.status}: {response.reason or response.text}', response=response)


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


def get_hail_variants_for_variant_ids(samples, genome_version, parsed_variant_ids, user, user_email=None, return_all_queried_families=False):
    search = {
        'variant_ids': [parsed_id for parsed_id in parsed_variant_ids.values() if parsed_id],
        'variant_keys': [variant_id for variant_id, parsed_id in parsed_variant_ids.items() if not parsed_id],
    }
    search_body = _format_search_body(samples, genome_version, len(parsed_variant_ids), search)
    response_json = _execute_search(search_body, user, user_email=user_email)

    if return_all_queried_families:
        expected_family_guids = set(samples.values_list('individual__family__guid', flat=True))
        _validate_expected_families(response_json['results'], expected_family_guids)

    return response_json['results']


def _execute_lookup(user, variant_id, data_type, **kwargs):
    body = {
        'variant_id': variant_id,
        'data_type': data_type,
        **kwargs,
    }
    return _execute_search(body, user, path='lookup', exception_map={404: 'Variant not present in seqr'}), body


def hail_variant_lookup(user, variant_id, dataset_type, **kwargs):
    variant, _ = _execute_lookup(user, variant_id, data_type=dataset_type, **kwargs)
    return variant


def hail_sv_variant_lookup(user, variant_id, dataset_type, samples, sample_type=None, **kwargs):
    if not sample_type:
        from seqr.utils.search.utils import InvalidSearchException
        raise InvalidSearchException('Sample type must be specified to look up a structural variant')
    data_type = f'{dataset_type}_{sample_type}'

    sample_data = _get_sample_data(samples)
    variant, body = _execute_lookup(user, variant_id, data_type, sample_data=sample_data.pop(data_type), **kwargs)
    variants = [variant]

    if variant['svType'] in {'DEL', 'DUP'}:
        del body['variant_id']
        body.update({
            'sample_data': sample_data,
            'padded_interval': {'chrom': variant['chrom'], 'start': variant['pos'], 'end': variant['end'], 'padding': 0.2},
            'annotations': {'structural': [variant['svType'], f"gCNV_{variant['svType']}"]}
        })
        variants += _execute_search(body, user)['results']

    return variants


def hail_variant_multi_lookup(user_email, variant_ids, data_type, genome_version):
    body = {'genome_version': genome_version, 'data_type': data_type, 'variant_ids': variant_ids}
    response_json = _execute_search(body, user=None, user_email=user_email, path='multi_lookup')
    return response_json['results']


def _format_search_body(samples, genome_version, num_results, search):
    search_body = {
        'genome_version': GENOME_VERSION_LOOKUP[genome_version],
        'num_results': num_results,
    }
    search_body.update(search)
    search_body['sample_data'] = _get_sample_data(samples, **search_body)
    return search_body


def search_data_type(dataset_type, sample_type):
    return f'{dataset_type}_{sample_type}' if dataset_type == Sample.DATASET_TYPE_SV_CALLS else dataset_type


def _get_sample_data(samples, inheritance_filter=None, inheritance_mode=None, **kwargs):
    sample_values = dict(
        individual_guid=F('individual__guid'),
        family_guid=F('individual__family__guid'),
        project_guid=F('individual__family__project__guid'),
        affected=F('individual__affected'),
    )
    if inheritance_mode == X_LINKED_RECESSIVE:
        sample_values['is_male'] = Case(When(individual__sex__in=Individual.MALE_SEXES, then=True), default=False)
    sample_data = samples.order_by('guid').values('individual__individual_id', 'dataset_type', 'sample_type', **sample_values)

    custom_affected = (inheritance_filter or {}).pop('affected', None)
    if custom_affected:
        for s in sample_data:
            s['affected'] = custom_affected.get(s['individual_guid']) or s['affected']

    sample_data_by_data_type = defaultdict(list)
    for s in sample_data:
        dataset_type = s.pop('dataset_type')
        s['sample_id'] = s.pop('individual__individual_id')  # Note: set sample_id to individual_id
        data_type_key = search_data_type(dataset_type, s['sample_type'])
        sample_data_by_data_type[data_type_key].append(s)

    return sample_data_by_data_type


def _get_sort_metadata(sort, samples):
    sort_metadata = None
    if sort == 'in_omim':
        sort_metadata = list(Omim.objects.filter(phenotype_mim_number__isnull=False, gene__isnull=False).values_list('gene__gene_id', flat=True))
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
    exclude_locations = locus.get('excludeLocations')

    genes = parsed_locus.get('genes') or {}
    intervals = parsed_locus.get('intervals')
    parsed_intervals = None
    if genes or intervals:
        gene_coords = [
            {field: gene[f'{field}{search["genome_version"].title()}'] for field in ['chrom', 'start', 'end']}
            for gene in genes.values()
        ]
        parsed_intervals = [_format_interval(**interval) for interval in intervals or []] + sorted([
            [gene['chrom'], gene['start'], gene['end']] for gene in gene_coords])
        if Sample.DATASET_TYPE_MITO_CALLS in search['sample_data'] and not exclude_locations:
            chromosomes = {gene['chrom'] for gene in gene_coords + (intervals or [])}
            if 'M' not in chromosomes:
                search['sample_data'].pop(Sample.DATASET_TYPE_MITO_CALLS)
            elif chromosomes == {'M'}:
                search['sample_data'] = {Sample.DATASET_TYPE_MITO_CALLS: search['sample_data'][Sample.DATASET_TYPE_MITO_CALLS]}

    search.update({
        'intervals': parsed_intervals,
        'exclude_intervals': exclude_locations,
        'gene_ids': None if (exclude_locations or not genes) else sorted(genes.keys()),
        'variant_ids': parsed_locus.get('parsed_variant_ids'),
        'rs_ids': parsed_locus.get('rs_ids'),
    })


def _format_interval(chrom=None, start=None, end=None, offset=None, **kwargs):
    if offset:
        offset_pos = int((end - start) * offset)
        start = max(start - offset_pos, MIN_POS)
        end = min(end + offset_pos, MAX_POS)
    return chrom, start, end


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


MAX_FAMILY_COUNTS = {Sample.SAMPLE_TYPE_WES: 200, Sample.SAMPLE_TYPE_WGS: 35}


def validate_hail_backend_no_location_search(samples):
    sample_counts = samples.filter(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS).values('sample_type').annotate(
        family_count=Count('individual__family_id', distinct=True),
        project_count=Count('individual__family__project_id', distinct=True),
    )
    from seqr.utils.search.utils import InvalidSearchException
    if sample_counts and (len(sample_counts) > 1 or sample_counts[0]['project_count'] > 1):
        raise InvalidSearchException('Location must be specified to search across multiple projects')
    if sample_counts and sample_counts[0]['family_count'] > MAX_FAMILY_COUNTS[sample_counts[0]['sample_type']]:
        raise InvalidSearchException('Location must be specified to search across multiple families in large projects')
