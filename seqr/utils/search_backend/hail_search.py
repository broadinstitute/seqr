from collections import defaultdict

# TODO import hail

from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, \
    INHERITANCE_FILTERS, ALT_ALT, REF_REF, REF_ALT, HAS_ALT, HAS_REF, \
    POPULATIONS # TODO may need different constants
from seqr.utils.elasticsearch.es_search import EsSearch, _get_family_affected_status, _annotations_filter

class HailSearch(object):

    def __init__(self, families, inheritance_search=None, user=None, **kwargs):

        self.samples_by_family = defaultdict(dict)
        samples = Sample.objects.filter(is_active=True, individual__family__in=families)
        for s in samples.select_related('individual__family'):
            self.samples_by_family[s.individual.family.guid][s.sample_id] = s

        self._family_individual_affected_status = {}
        if inheritance_search:
            skipped_families = []
            for family_guid, samples_by_id in self.samples_by_family.items():
                individual_affected_status = _get_family_affected_status(
                    samples_by_id, inheritance_search.get('filter') or {})
                self._family_individual_affected_status[family_guid].update(individual_affected_status)

                has_affected_samples = any(
                    aftd == Individual.AFFECTED_STATUS_AFFECTED for aftd in individual_affected_status.values()
                )
                if not has_affected_samples:
                    skipped_families.append(family_guid)

            for family_guid in skipped_families:
                del self.samples_by_family[family_guid]

            if len(self.samples_by_family) < 1:
                raise InvalidSearchException(
                    'Inheritance based search is disabled in families with no data loaded for affected individuals')

        self._user = user
        self._allowed_consequences = None
        self._sample_table_queries = {}

        # TODO set up connection to MTs/ any external resources

    def _sample_table(self, sample_id):
        # TODO should implement way to automatically map sample id to table name
        # TODO actually connect to/ load tables
        raise NotImplementedError

    @classmethod
    def process_previous_results(cls, *args, **kwargs):
        return EsSearch.process_previous_results(*args, **kwargs)

    def sort(self, sort):
        raise NotImplementedError

    def filter_by_location(self, genes=None, intervals=None, **kwargs):
        parsed_intervals = [
            hl.parse_locus_interval(interval) for interval in
            ['{chrom}:{start}-{end}'.format(**interval) for interval in intervals or []] + [
                # long-term we should check project to get correct genome version
                '{chromGrch38}:{startGrch38}-{endGrch38}'.format(**gene) for gene in (genes or {}).values()]
        ]

        # TODO actually apply filter - hl.filter_intervals(self._mt, parsed_intervals)
        raise NotImplementedError

    def filter_by_frequency(self, frequencies, **kwargs):
        freq_filters = {}
        for pop, freqs in sorted(frequencies.items()):
            if freqs.get('af') is not None:
                filter_field = next(
                    (field_key for field_key in POPULATIONS[pop]['filter_AF']
                     if any(field_key in index_metadata['fields'] for index_metadata in self.index_metadata.values())),
                    POPULATIONS[pop]['AF'])
                freq_filters[filter_field] = freqs['af']
            elif freqs.get('ac') is not None:
                freq_filters[POPULATIONS[pop]['AC']] = freqs['ac']

            if freqs.get('hh') is not None:
                freq_filters[POPULATIONS[pop]['Hom']] = freqs['hh']
                freq_filters[POPULATIONS[pop]['Hemi']] = freqs['hh']

        # freq_filters example: {'gnomad_genomes_AF_POPMAX_OR_GLOBAL': 0.001, 'AC': 3}
        # TODO actually apply filters, get variants with freq <= specified value, or missing from data entirely
        raise NotImplementedError

    def filter_by_in_silico(self, in_silico_filters):
        raise NotImplementedError

    def filter_by_annotation_and_genotype(self, inheritance, quality_filter=None, annotations=None, **kwargs):
        if annotations:
            self._filter_by_annotations(annotations)

        inheritance_mode = (inheritance or {}).get('mode')
        inheritance_filter = (inheritance or {}).get('filter') or {}
        if inheritance_filter.get('genotype'):
            inheritance_mode = None

        quality_filters_by_family = _quality_filters_by_family(quality_filter, self.samples_by_family) # TODO

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            self._filter_compound_hets(quality_filters_by_family)
            if inheritance_mode == COMPOUND_HET:
                return

        self._filter_by_genotype(inheritance_mode, inheritance_filter, quality_filters_by_family)

    def _filter_by_annotations(self, annotations):
        _, allowed_consequences = _annotations_filter(annotations or {})
        if allowed_consequences:
            # allowed_consequences: list of allowed VEP transcript_consequence
            # TODO actually apply filters, get variants with any transcript with a consequence in the allowed list
            raise NotImplementedError

    def _filter_by_genotype(self, inheritance_mode, inheritance_filter, quality_filters_by_family):
        if inheritance_filter or inheritance_mode:
            self._filter_by_genotype_inheritance(inheritance_mode, inheritance_filter, quality_filters_by_family)
        else:
            all_samples = set()
            for samples_by_id in self.samples_by_family.values():
                all_samples.update(samples_by_id.keys())
            # TODO filter result to desired samples - result.filter_cols(hl.array(all_samples).contains(result.sample_id))
            # TODO remove all samples in families where any sample is not passing the quality filters
            # TODO remove rows where none of the remaining samples have alt alleles
            raise NotImplementedError

    def _filter_by_genotype_inheritance(self, inheritance_mode, inheritance_filter, quality_filters_by_family):
        for family_guid, samples_by_id in self.samples_by_family.items():
            sample_tables = [self._sample_table(sample_id) for sample_id in sorted(samples_by_id.keys())]
            running_join = sample_tables[0]
            for ht in sample_tables[1:]:
                running_join = running_join.join(ht, how="outer")

            affected_status = self._family_individual_affected_status.get(family_guid)

            if inheritance_mode:
                inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

            if list(inheritance_filter.keys()) == ['affected']:
                raise InvalidSearchException('Inheritance must be specified if custom affected status is set')

            samples_q = None

            individual_genotype_filter = inheritance_filter.get('genotype') or {}

            if inheritance_mode == X_LINKED_RECESSIVE:
                # TODO will need to filter by both inheritance and chromosome
                raise NotImplementedError

            for i, (sample_id, sample) in enumerate(sorted(samples_by_id.items())):

                individual_guid = sample.individual.guid
                affected = individual_affected_status[individual_guid]

                genotype = individual_genotype_filter.get(individual_guid) or inheritance_filter.get(affected)
                if genotype:
                    not_allowed_num_alt = [
                        num_alt for num_alt in GENOTYPE_QUERY_MAP[genotype].get('not_allowed_num_alt', [])
                        if num_alt in index_fields
                    ]
                    allowed_num_alt = [
                        num_alt for num_alt in GENOTYPE_QUERY_MAP[genotype].get('allowed_num_alt', [])
                        if num_alt in index_fields
                    ]
                    num_alt_to_filter = not_allowed_num_alt or allowed_num_alt
                    sample_filters = [{num_alt_key: sample_id} for num_alt_key in num_alt_to_filter]

                    sample_q = _build_or_filter('term', sample_filters)
                    if not_allowed_num_alt:
                        sample_q = ~Q(sample_q)

                    if not samples_q:
                        samples_q = sample_q
                    else:
                        samples_q &= sample_q

            if not family_samples_q:
                raise InvalidSearchException('Invalid custom inheritance')

            # For recessive search, should be hom recessive, x-linked recessive, or compound het
            if inheritance_mode == RECESSIVE:
                # TODO should add an OR filter for variants on the X chromosome only that conform to X-linked
                pass

        # TODO actually filter
        """
        running_join = sample_tables[0]

        for ht in sample_tables[1:]:
            running_join = running_join.join(ht, how="outer")

        # By default this creates a situation where the first genotype is called GT, the second is called GT_1, third called GT_2, etc.

        result = running_join.filter(running_join.GT.is_het() & running_join.GT_1.is_hom_ref() & running_join.GT_2.is_het()).collect()
        """

    def _filter_compound_hets(self, quality_filters_by_family):
        # TODO
        raise NotImplementedError

    def search(self, page=1, num_results=100, **kwargs):
        # TODO actually get results back - result.collect() ?
        # TODO format return values into correct dicts, potentially post-process compound hets
        raise NotImplementedError
