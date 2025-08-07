from collections import defaultdict

from django.db.models import F, Min, Case, When
from time import sleep
from urllib3.connectionpool import connection_from_url

import requests
from reference_data.models import Omim, GeneConstraint, GENOME_VERSION_LOOKUP
from seqr.models import Sample, PhenotypePrioritization, Individual
from seqr.utils.search.constants import PRIORITIZED_GENE_SORT, X_LINKED_RECESSIVE
from settings import HAIL_BACKEND_SERVICE_HOSTNAME, HAIL_BACKEND_SERVICE_PORT


def _hail_backend_url(path):
    return f'http://{HAIL_BACKEND_SERVICE_HOSTNAME}:{HAIL_BACKEND_SERVICE_PORT}/{path}'

def _execute_search(search_body, user, path='search', exception_map=None, user_email=None, max_retries=0):
    for _ in range(max_retries + 1):
        response = requests.post(_hail_backend_url(path), json=search_body, headers={'From': user_email or user.email}, timeout=300)
        if response.status_code == 200:
            return response.json()
        sleep(1)

    error = (exception_map or {}).get(response.status_code) or response.text or response.reason
    raise requests.HTTPError(error, response=response)


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
        **search_body.pop('parsed_locus')
    })
    search_body.pop('skipped_samples', None)

    sv_data_types = [data_type for data_type in search_body['sample_data'] if data_type.startswith(Sample.DATASET_TYPE_SV_CALLS)]
    if len(sv_data_types) > 1 and not gene_agg:
        response_json = _execute_multi_sample_types_searches(sv_data_types, search_body, user)
    else:
        path = 'gene_counts' if gene_agg else 'search'
        response_json = _execute_search(search_body, user, path)

    if gene_agg:
        previous_search_results['gene_aggs'] = response_json
        return response_json

    previous_search_results['total_results'] = response_json['total']
    previous_search_results['all_results'] = response_json['results']
    return response_json['results'][end_offset - num_results:end_offset]


def _execute_multi_sample_types_searches(sv_data_types, search_body, user):
    sample_data_by_sample_data_type = defaultdict(lambda: defaultdict(list))
    for data_type, samples in search_body['sample_data'].items():
        if data_type in sv_data_types:
            sample_type = samples[0]['sample_type']
            sample_data_by_sample_data_type[sample_type][data_type] = samples
        else:
            for sample in samples:
                sample_data_by_sample_data_type[sample['sample_type']][data_type].append(sample)

    total = 0
    results = []
    for sample_type in sorted(sample_data_by_sample_data_type.keys()):
        search_body['sample_data'] = sample_data_by_sample_data_type[sample_type]
        sample_response_json = _execute_search(search_body, user)
        total += sample_response_json['total']
        results += sample_response_json['results']

    return {'total': total, 'results': sorted(results, key=lambda x: x[0]['_sort'] if isinstance(x, list) else x['_sort'])[:search_body['num_results']]}


def get_hail_variants_for_variant_ids(samples, genome_version, parsed_variant_ids, user, user_email=None):
    search = {
        'variant_ids': [parsed_id for parsed_id in parsed_variant_ids.values() if parsed_id],
        'variant_keys': [variant_id for variant_id, parsed_id in parsed_variant_ids.items() if not parsed_id],
    }
    search_body = _format_search_body(samples, genome_version, len(parsed_variant_ids), search)
    response_json = _execute_search(search_body, user, user_email=user_email)

    return response_json['results']


def hail_variant_lookup(user, variant_id, data_type, genome_version=None, samples=None, **kwargs):
    body = {
        'variant_id': variant_id,
        'data_type': data_type,
        'genome_version': GENOME_VERSION_LOOKUP[genome_version],
        **kwargs,
    }
    if samples:
        body['sample_data'] = _get_sample_data(samples).pop(data_type)
    return _execute_search(body, user, path='lookup', exception_map={404: 'Variant not present in seqr'})


def hail_variant_multi_lookup(user_email, variant_ids, data_type, genome_version):
    body = {'genome_version': genome_version, 'data_type': data_type, 'variant_ids': variant_ids}
    response_json = _execute_search(body, user=None, user_email=user_email, path='multi_lookup', max_retries=2)
    return response_json['results']


def _format_search_body(samples, genome_version, num_results, search):
    search_body = {
        'genome_version': GENOME_VERSION_LOOKUP[genome_version],
        'num_results': num_results,
    }
    search_body.update(search)
    search_body['sample_data'] = _get_sample_data(samples, **search_body)
    search_body.pop('dataset_type', None)
    search_body.pop('secondary_dataset_type', None)
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
