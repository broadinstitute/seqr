from collections import defaultdict
from django.db.models import F

import requests
from reference_data.models import Omim, GeneConstraint, GENOME_VERSION_LOOKUP
from seqr.models import Individual, Sample, PhenotypePrioritization
from seqr.utils.search.constants import RECESSIVE, COMPOUND_HET, MAX_NO_LOCATION_COMP_HET_FAMILIES
from seqr.utils.search.utils import InvalidSearchException
from seqr.views.utils.orm_to_json_utils import get_json_for_queryset


def _get_sample_data(families):
    sample_data = Sample.objects.filter(is_active=True, individual__family__in=families).values(
        'sample_id', 'dataset_type', 'sample_type',
        individual_guid=F('individual__guid'),
        family_guid=F('individual__family__guid'),
        project_guid=F('individual__family__project__guid'),
        affected=F('individual__affected'),
        sex=F('individual__sex'),
        project_name=F('individual__family__project__name'),
        project_genome_version=F('individual__family__project__genome_version'),
    )

    sample_data_by_data_type = defaultdict(list)
    genome_version_projects = defaultdict(set)
    for s in sample_data:
        dataset_type = s.pop('dataset_type')
        sample_type = s.pop('sample_type')
        data_type_key = f'{dataset_type}_{sample_type}' if dataset_type == Sample.DATASET_TYPE_SV_CALLS else dataset_type
        sample_data_by_data_type[data_type_key].append(s)
        genome_version_projects[GENOME_VERSION_LOOKUP[s.pop('project_genome_version')]].add(s.pop('project_name'))

    return sample_data_by_data_type, genome_version_projects


def _get_sort_metadata(sort, families):
    sort_metadata = None
    if sort == 'in_omim':
        sort_metadata = Omim.objects.filter(phenotype_mim_number__isnull=False).values_list('gene__gene_id',                                                                                      flat=True)
    elif sort == 'constraint':
        sort_metadata = {
            agg['gene__gene_id']: agg['mis_z_rank'] + agg['pLI_rank'] for agg in
            GeneConstraint.objects.values('gene__gene_id', 'mis_z_rank', 'pLI_rank')
        }
    elif sort == 'prioritized_gene':
        if len(families) != 1:
            raise InvalidSearchException('Phenotype sort is only supported for single-family search.')
        sort_metadata = {
            agg['gene_id']: agg['min_rank'] for agg in PhenotypePrioritization.objects.filter(
                individual__family=list(families)[0], rank__lte=100,
            ).values('gene_id').annotate(min_rank=Min('rank'))
        }
    return sort_metadata


def _parse_location_search(search, families):
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
        parsed_intervals = ['{chrom}:{start}-{end}'.format(**interval) for interval in intervals or []] + [
            '{chrom}:{start}-{end}'.format(**gene) for gene in gene_coords]

    exclude_locations = locus.get('excludeLocations')
    has_location_search = bool(parsed_intervals) and not exclude_locations
    if not has_location_search:
        if len(families) > 1 and len({f.project_id for f in families}) > 1:
            raise InvalidSearchException('Location must be specified to search across multiple projects')

    search.update({
        'intervals': parsed_intervals,
        'exclude_intervals': exclude_locations,
        'gene_ids': None if exclude_locations else list(genes.keys()),
        'variant_ids': parsed_locus.get('parsed_variant_ids'),
        'rs_ids': parsed_locus.get('rs_ids'),
    })


def _parse_inheritance_search(search, families):
    inheritance = search.pop('inheritance', None) or {}
    inheritance_mode = inheritance.get('mode')
    inheritance_filter = inheritance.get('filter') or {}

    if inheritance_filter.get('genotype'):
        inheritance_mode = None

    has_comp_het_search = inheritance_mode in {RECESSIVE, COMPOUND_HET}
    if has_comp_het_search:
        has_location_search = bool(search['intervals']) and not search['exclude_intervals']
        if len(families) > MAX_NO_LOCATION_COMP_HET_FAMILIES and not has_location_search:
            raise InvalidSearchException(
                'Location must be specified to search for compound heterozygous variants across many families')
        if not search.get('annotations'):
            raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

    if not inheritance_mode and inheritance_filter and list(inheritance_filter.keys()) == ['affected']:
        raise InvalidSearchException('Inheritance must be specified if custom affected status is set')

    if inheritance_filter.get('affected'):
        for samples in search['sample_data'].values():
            for s in samples:
                s['affected'] = inheritance_filter['affected'].get(s['individual_guid']) or s['affected']

    if inheritance_mode or inheritance_filter:
        has_affected = any(
            any(s['affected'] == Individual.AFFECTED_STATUS_AFFECTED for s in samples)
            for samples in search['sample_data'].values())
        if not has_affected:
            raise InvalidSearchException(
                'Inheritance based search is disabled in families with no data loaded for affected individuals')

    search.update({'inheritance_mode': inheritance_mode, 'inheritance_filter': inheritance_filter})


def _search(search, previous_search_results, page=1, num_results=100):
    end_offset = num_results * page
    search['num_results'] = end_offset

    response = requests.post('http://hail-search:5000/search', json=search)
    response.raise_for_status()
    response_json = response.json()

    previous_search_results['total_results'] = response_json['total']
    previous_search_results['all_results'] = response_json['results']
    return response_json['results'][end_offset - num_results:end_offset]


def get_hail_variants(families, search, user, previous_search_results, sort=None, page=None, num_results=None,
                      gene_agg=False, skip_genotype_filter=False):
    if gene_agg:
        raise NotImplementedError
    if skip_genotype_filter:
        raise NotImplementedError

    sample_data, genome_version_projects = _get_sample_data(families)

    if len(genome_version_projects) > 1:
        project_builds = '; '.join(
            f'{build} [{", ".join(projects)}]' for build, projects in genome_version_projects.items())
        raise InvalidSearchException(
            f'Search is only enabled on a single genome build, requested the following project builds: {project_builds}')
    genome_version = list(genome_version_projects.keys())[0]

    search_body = {
        'requester_email': user.email,
        'sample_data': sample_data,
        'genome_version': genome_version,
        'sort': sort,
        'sort_metadata': _get_sort_metadata(sort, families),
    }
    search_body.update(search)
    search_body.update({  # TODO do not reformat
        'frequencies': search_body.pop('freqs', None),
        'quality_filter': search_body.pop('qualityFilter', None),
        'custom_query': search_body.pop('customQuery', None),
    })

    _parse_location_search(search_body, families)
    _parse_inheritance_search(search_body, families)

    return _search(search_body, previous_search_results, page=page, num_results=num_results)
