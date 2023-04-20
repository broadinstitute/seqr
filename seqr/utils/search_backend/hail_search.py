from collections import defaultdict
from django.db.models import F
import logging

from hail_search.search import search_hail_backend
from reference_data.models import Omim, GeneConstraint, GENOME_VERSION_LOOKUP
from seqr.models import Individual, Sample, PhenotypePrioritization
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, MAX_NO_LOCATION_COMP_HET_FAMILIES
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.es_search import EsSearch
from seqr.views.utils.orm_to_json_utils import get_json_for_queryset

logger = logging.getLogger(__name__)


class HailSearch(object):

    def __init__(self, families, previous_search_results=None, return_all_queried_families=False, user=None, sort=None):
        self._families = families
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

        self._sample_data_by_data_type = defaultdict(list)
        genome_version_projects = defaultdict(set)
        for s in sample_data:
            dataset_type = s.pop('dataset_type')
            sample_type = s.pop('sample_type')
            data_type_key = f'{dataset_type}_{sample_type}' if dataset_type == Sample.DATASET_TYPE_SV_CALLS else dataset_type
            self._sample_data_by_data_type[data_type_key].append(s)
            self._family_guids.add(s['family_guid'])
            genome_version_projects[GENOME_VERSION_LOOKUP[s.pop('project_genome_version')]].add(s.pop('project_name'))

        if len(genome_version_projects) > 1:
            project_builds = '; '.join(
                f'{build} [{", ".join(projects)}]' for build, projects in genome_version_projects.items())
            raise InvalidSearchException(
                f'Search is only enabled on a single genome build, requested the following project builds: {project_builds}')
        self._genome_version = list(genome_version_projects.keys())[0]

        self._user = user  # TODO use for logging, pass to query wrapper

        self._search_body = {
            'sample_data': self._sample_data_by_data_type,
            'genome_version': self._genome_version,
            'sort': sort,
            'sort_metadata': self._get_sort_metadata(sort),
        }

        self._return_all_queried_families = return_all_queried_families # In production: need to implement for reloading saved variants
        self.previous_search_results = previous_search_results or {}

    def _get_sort_metadata(self, sort):
        sort_metadata = None
        if sort == 'in_omim':
            sort_metadata = Omim.objects.filter(phenotype_mim_number__isnull=False).values_list('gene__gene_id',                                                                                      flat=True)
        elif sort == 'constraint':
            sort_metadata = {
                agg['gene__gene_id']: agg['mis_z_rank'] + agg['pLI_rank'] for agg in
                GeneConstraint.objects.values('gene__gene_id', 'mis_z_rank', 'pLI_rank')
            }
        elif sort == 'prioritized_gene':
            if len(self._families) != 1:
                raise InvalidSearchException('Phenotype sort is only supported for single-family search.')
            sort_metadata = {
                agg['gene_id']: agg['min_rank'] for agg in PhenotypePrioritization.objects.filter(
                    individual__family=list(self._families)[0], rank__lte=100,
                ).values('gene_id').annotate(min_rank=Min('rank'))
            }
        return sort_metadata

    @classmethod
    def process_previous_results(cls, *args, **kwargs):
        return EsSearch.process_previous_results(*args, **kwargs)

    def filter_variants(self, inheritance=None, genes=None, intervals=None, variant_ids=None, locus=None,
                        annotations=None, skip_genotype_filter=False, **kwargs):
        parsed_intervals = None
        if variant_ids:
            variant_ids = [EsSearch.parse_variant_id(variant_id) for variant_id in variant_ids]

        genes = genes or {}
        exclude_locations = (locus or {}).get('excludeLocations')
        if genes or intervals:
            gene_coords = [
                {field: gene[f'{field}{self._genome_version.title()}'] for field in ['chrom', 'start', 'end']}
                for gene in genes.values()
            ]
            parsed_intervals = ['{chrom}:{start}-{end}'.format(**interval) for interval in intervals or []] + [
                '{chrom}:{start}-{end}'.format(**gene) for gene in gene_coords]

        has_location_search = bool(parsed_intervals) and not exclude_locations
        if not has_location_search:
            project_ids = {f.project_id for f in self._families}
            if len(project_ids) > 1:
                raise InvalidSearchException('Location must be specified to search across multiple projects')

        inheritance_mode = (inheritance or {}).get('mode')
        inheritance_filter = (inheritance or {}).get('filter') or {}
        if inheritance_filter.get('genotype'):
            inheritance_mode = None
        has_comp_het_search = inheritance_mode in {RECESSIVE, COMPOUND_HET}
        if has_comp_het_search:
            if len(self._families) > MAX_NO_LOCATION_COMP_HET_FAMILIES and not has_location_search:
                raise InvalidSearchException(
                    'Location must be specified to search for compound heterozygous variants across many families')
            if not annotations:
                raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')
        if not inheritance_mode and inheritance_filter and list(inheritance_filter.keys()) == ['affected']:
            raise InvalidSearchException('Inheritance must be specified if custom affected status is set')
        if inheritance_filter.get('affected'):
            for samples in self._sample_data_by_data_type.values():
                for s in samples:
                    s['affected'] = inheritance_filter['affected'].get(s['individual_guid']) or s['affected']
        if inheritance_mode or inheritance_filter:
            has_affected = any(any(s['affected'] == Individual.AFFECTED_STATUS_AFFECTED for s in samples) for samples in self._sample_data_by_data_type.values())
            if not has_affected:
                raise InvalidSearchException(
                    'Inheritance based search is disabled in families with no data loaded for affected individuals')

        self._search_body.update(dict(
            intervals=parsed_intervals, exclude_intervals=exclude_locations,
            gene_ids=None if exclude_locations else set(genes.keys()), variant_ids=variant_ids,
            inheritance_mode=inheritance_mode, inheritance_filter=inheritance_filter, annotations=annotations,
            **kwargs,
        ))

    def filter_by_variant_ids(self, variant_ids):
        self.filter_variants(variant_ids=variant_ids)

    def search(self, page=1, num_results=100):
        end_offset = num_results * page
        self._search_body['num_results'] = end_offset
        try:
            hail_results, total_results = search_hail_backend(self._search_body)
        except Exception as e:
            # TODO use raise_for_response
            raise InvalidSearchException(str(e))
        self.previous_search_results['total_results'] = total_results
        # self.previous_search_results['all_results'] = hail_results  TODO re-enable
        return hail_results[end_offset - num_results:end_offset]
