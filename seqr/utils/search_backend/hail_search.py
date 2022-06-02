from collections import defaultdict
import logging

from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, MAX_NO_LOCATION_COMP_HET_FAMILIES
from seqr.utils.elasticsearch.es_search import EsSearch, _get_family_affected_status
from seqr.utils.search_backend.hail_query_wrapper import VariantHailTableQuery

logger = logging.getLogger(__name__)

class HailSearch(object):

    def __init__(self, families, previous_search_results=None, return_all_queried_families=False, user=None, sort=None):
        self.samples = Sample.objects.filter(
            is_active=True, individual__family__in=families,
        ).select_related('individual__family', 'individual__family__project')

        projects = {s.individual.family.project for s in self.samples}
        genome_version_projects = defaultdict(list)
        for p in projects:
            genome_version_projects[p.get_genome_version_display()].append(p.name)
        if len(genome_version_projects) > 1:
            project_builds = '; '.join(f'build [{", ".join(projects)}]' for build, projects in genome_version_projects.items())
            raise InvalidSearchException(
                f'Search is only enabled on a single genome build, requested the following project builds: {project_builds}')
        self._genome_version = list(genome_version_projects.keys())[0]

        self._user = user
        self._sort = sort
        self._return_all_queried_families = return_all_queried_families # In production: need to implement for reloading saved variants
        self.previous_search_results = previous_search_results or {}

    def _load_table(self, **kwargs):
        # TODO filter by searched dataset type
        data_sources_by_type = defaultdict(set)
        for s in self.samples:
            data_sources_by_type[s.dataset_type].add(s.elasticsearch_index)  # In production: should use a different model field
        multi_data_sources = next(
            (data_sources for data_sources in data_sources_by_type.values() if len(data_sources) > 1), None)
        if multi_data_sources:
            raise InvalidSearchException(
                f'Search is only enabled on a single data source, requested {", ".join(multi_data_sources)}')
        data_sources_by_type = {k: v.pop() for k, v in data_sources_by_type.items()}

        # TODO load correct data type
        self.samples = [s for s in self.samples if s.dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS]
        data_source = data_sources_by_type[Sample.DATASET_TYPE_VARIANT_CALLS]
        query_cls = VariantHailTableQuery
        self._query_wrapper = query_cls(data_source, genome_version=self._genome_version, **kwargs)

    @classmethod
    def process_previous_results(cls, previous_search_results, page=1, num_results=100, load_all=False):
        # return EsSearch.process_previous_results(*args, **kwargs)
        # TODO #2496: re-enable caching, not helpful for initial development
        return None, {'page': page, 'num_results': num_results}

    def filter_variants(self, inheritance=None, genes=None, intervals=None, variant_ids=None, locus=None,
                        annotations_secondary=None, quality_filter=None, skip_genotype_filter=False, **kwargs):
        has_location_filter = genes or intervals
        if has_location_filter:
            self._filter_by_intervals(genes, intervals, locus.get('excludeLocations'))
        elif variant_ids:
            self.filter_by_variant_ids(variant_ids)
        else:
            self._load_table()

        quality_filter = quality_filter or {}
        self._query_wrapper.filter_variants(quality_filter=quality_filter, **kwargs)

        inheritance_mode = (inheritance or {}).get('mode')
        inheritance_filter = (inheritance or {}).get('filter') or {}
        if inheritance_filter.get('genotype'):
            inheritance_mode = None
        if not inheritance_mode and inheritance_filter and list(inheritance_filter.keys()) == ['affected']:
            raise InvalidSearchException('Inheritance must be specified if custom affected status is set')

        family_individual_affected_status = {}
        samples_by_family = defaultdict(dict)
        for s in self.samples:
            samples_by_family[s.individual.family.guid][s.sample_id] = s

        if inheritance:
            for family_guid, samples_by_id in samples_by_family.items():
                family_individual_affected_status[family_guid] = _get_family_affected_status(
                    samples_by_id, inheritance_filter)

            for family_guid, individual_affected_status in family_individual_affected_status.items():
                has_affected_samples = any(
                    aftd == Individual.AFFECTED_STATUS_AFFECTED for aftd in individual_affected_status.values()
                )
                if not has_affected_samples:
                    del samples_by_family[family_guid]

            if len(samples_by_family) < 1:
                raise InvalidSearchException(
                    'Inheritance based search is disabled in families with no data loaded for affected individuals')

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            if not has_location_filter and len(samples_by_family) > MAX_NO_LOCATION_COMP_HET_FAMILIES:
                raise InvalidSearchException(
                    'Location must be specified to search for compound heterozygous variants across many families')

            comp_het_only = inheritance_mode == COMPOUND_HET
            self._query_wrapper.filter_compound_hets(
                samples_by_family, family_individual_affected_status, annotations_secondary, quality_filter,
                keep_main_ht=not comp_het_only)
            if comp_het_only:
                return

        self._query_wrapper.filter_main_annotations()
        self._query_wrapper.annotate_filtered_genotypes(
            samples_by_family, family_individual_affected_status, inheritance_mode, inheritance_filter, quality_filter)

    def filter_by_variant_ids(self, variant_ids):
        # In production: support SV variant IDs?
        variant_ids = [EsSearch.parse_variant_id(variant_id) for variant_id in variant_ids]
        # TODO #2716: format chromosome for genome build
        intervals = [ f'[chr{chrom}:{pos}-{pos}]' for chrom, pos, _, _ in variant_ids]
        self._load_table(intervals=intervals)
        self._query_wrapper.filter_by_variant_ids(variant_ids)

    def _filter_by_intervals(self, genes, intervals, exclude_locations):
        parsed_intervals = None
        if genes or intervals:
            # TODO #2716: format chromosomes for genome build
            gene_coords = [
                {field: gene[f'{field}{self._genome_version.title()}'] for field in ['chrom', 'start', 'end']}
                for gene in (genes or {}).values()
            ]
            parsed_intervals = ['{chrom}:{start}-{end}'.format(**interval) for interval in intervals or []] + [
                'chr{chrom}:{start}-{end}'.format(**gene) for gene in gene_coords]

        self._load_table(intervals=parsed_intervals, exclude_intervals=exclude_locations)

    def search(self, page=1, num_results=100):
        hail_results, total_results = self._query_wrapper.search(page, num_results, self._sort)
        self.previous_search_results['total_results'] = total_results
        # TODO #2496 actually cache results
        return hail_results
