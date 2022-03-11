from collections import defaultdict
import hail as hl
import logging

from seqr.views.utils.json_utils import _to_camel_case
from reference_data.models import GENOME_VERSION_GRCh38
from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, \
    INHERITANCE_FILTERS, ALT_ALT, REF_REF, REF_ALT, HAS_ALT, HAS_REF, \
    POPULATIONS # TODO may need different constants
from seqr.utils.elasticsearch.es_search import EsSearch, _get_family_affected_status, _annotations_filter

logger = logging.getLogger(__name__)

GENOTYPE_QUERY_MAP = {
    REF_REF: 'is_hom_ref',
    REF_ALT: 'is_het',
    ALT_ALT: 'is_hom_var',
    HAS_ALT: 'is_non_ref',
    HAS_REF: '', # TODO find function for this
}


class HailSearch(object):

    def __init__(self, families, previous_search_results=None, inheritance_search=None, user=None, **kwargs):

        self.samples_by_family = defaultdict(dict)
        samples = Sample.objects.filter(is_active=True, individual__family__in=families)

        data_sources = {s.elasitcsearch_Ondex for s in samples}
        if len(data_sources) > 1:
            raise InvalidSearchException(
                f'Search is only enabled on a single data source, requested {", ".join(data_sources)}')
        data_source = data_sources.pop()

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
        self.previous_search_results = previous_search_results or {}
        self._allowed_consequences = None
        self._sample_table_queries = {}

        # TODO set up connection to MTs/ any external resources
        #self.mt = hl.experimental.load_dataset("1000_Genomes_HighCov_autosomes", "NYGC_30x_phased", "GRCh38")
        self.mt = hl.read_matrix_table(f'/hail_datasets/{data_source}.mt')

    def _sample_table(self, sample_id):
        # TODO should implement way to map sample id to table name
        # TODO actually connect to/ load tables
        raise NotImplementedError

    @classmethod
    def process_previous_results(cls, *args, **kwargs):
        return EsSearch.process_previous_results(*args, **kwargs)

    def sort(self, sort):
        pass
        # raise NotImplementedError

    def filter_by_location(self, genes=None, intervals=None, **kwargs):
        parsed_intervals = [
            hl.parse_locus_interval(interval, reference_genome="GRCh38") for interval in
            ['{chrom}:{start}-{end}'.format(**interval) for interval in intervals or []] + [
                # long-term we should check project to get correct genome version
                'chr{chromGrch38}:{startGrch38}-chr{chromGrch38}:{endGrch38}'.format(**gene) for gene in (genes or {}).values()]
        ]

        self.mt = hl.filter_intervals(self.mt, parsed_intervals)

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

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            self._filter_compound_hets(quality_filter)
            if inheritance_mode == COMPOUND_HET:
                return

        self._filter_by_genotype(inheritance_mode, inheritance_filter, quality_filter)

    def _filter_by_annotations(self, annotations):
        _, allowed_consequences = _annotations_filter(annotations or {})
        if allowed_consequences:
            # allowed_consequences: list of allowed VEP transcript_consequence
            # TODO actually apply filters, get variants with any transcript with a consequence in the allowed list -
            allowed_consequences_set = hl.set(allowed_consequences)
            consequence_terms = self.mt.vep.transcript_consequences.flatmap(lambda tc: tc.consequence_terms)
            self.mt = self.mt.filter_rows(consequence_terms.any(lambda ct: allowed_consequences_set.contains(ct)))

    def _filter_by_genotype(self, inheritance_mode, inheritance_filter, quality_filter):
        if inheritance_filter or inheritance_mode:
            self._filter_by_genotype_inheritance(inheritance_mode, inheritance_filter, quality_filter)
        else:
            all_samples = set()
            for samples_by_id in self.samples_by_family.values():
                all_samples.update(samples_by_id.keys())
            self.mt = self.mt.filter_cols(hl.array(all_samples).contains(self.mt.s))

            # TODO remove all samples in families where any sample is not passing the quality filters
            # - maybe should be part of _filter_by_genotype_inheritance if has quality filter?

            # TODO remove rows where none of the remaining samples have alt alleles
            # raise NotImplementedError

    def _filter_by_genotype_inheritance(self, inheritance_mode, inheritance_filter, quality_filter):
        if inheritance_mode:
            inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

        for family_guid, samples_by_id in self.samples_by_family.items():
            sample_ids = sorted(samples_by_id.keys())
            sample_tables = [self._sample_table(sample_id) for sample_id in sample_ids]
            running_join = sample_tables[0]
            for ht in sample_tables[1:]:
                running_join = running_join.join(ht, how="outer")

            affected_status = self._family_individual_affected_status.get(family_guid)

            if list(inheritance_filter.keys()) == ['affected']:
                raise InvalidSearchException('Inheritance must be specified if custom affected status is set')

            individual_genotype_filter = inheritance_filter.get('genotype') or {}

            if inheritance_mode == X_LINKED_RECESSIVE:
                # TODO will need to filter by both inheritance and chromosome
                raise NotImplementedError

            family_samples_q = None
            for i, (sample_id, sample) in enumerate(sorted(samples_by_id.items())):

                individual_guid = sample.individual.guid
                affected = affected_status[individual_guid]

                genotype = individual_genotype_filter.get(individual_guid) or inheritance_filter.get(affected)
                if genotype:
                    #  TODO correct syntax?
                    gt = running_join.getattr('GT' if i == 0 else 'GT_{}'.format(i))
                    sample_q = gt.getattr(GENOTYPE_QUERY_MAP[genotype])()

                    if quality_filter:
                        # TODO filter by gq and/or ab
                        # quality_filters format: dict with key min_qg/ min_ab and integer value value
                        # ab is only relevant for hets -confirm will not filter ab for hom ref or hom alt calls
                        raise NotImplementedError

                    if not family_samples_q:
                        family_samples_q = sample_q
                    else:
                        family_samples_q &= sample_q

            if not family_samples_q:
                raise InvalidSearchException('Invalid custom inheritance')

            # For recessive search, should be hom recessive, x-linked recessive, or compound het
            if inheritance_mode == RECESSIVE:
                # TODO should add an OR filter for variants with X-linked inheritance
                pass

            # # TODO actually apply the filter - running_join.filter(family_samples_q) ?
            raise NotImplementedError

    def _filter_compound_hets(self, quality_filter):
        self._filter_by_genotype_inheritance(COMPOUND_HET, inheritance_filter={}, quality_filter=quality_filter)
        # TODO modify query - get multiple hits within a single gene and ideally return grouped by gene
        raise NotImplementedError

    def search(self, page=1, num_results=100, **kwargs): # List of dictionaries of results {pos, ref, alt}
        family_guids = list(self.samples_by_family.keys())
        samples = []
        for family_guid in family_guids:
            samples += list(self.samples_by_family[family_guid].values())
        sample_individuals = {s.sample_id: s.individual.guid for s in samples}

        rows = self.mt.annotate_rows(genotypes=hl.agg.collect(hl.struct(
            sampleId=self.mt.s,
            gq=self.mt.GQ,
            numAlt=hl.if_else(hl.is_defined(self.mt.GT), self.mt.GT.n_alt_alleles(), -1),
            dp=self.mt.DP,
            # TODO ab
        ))).rows()

        rows.annotate(
            clinvar=hl.struct(
                clinicalSignificance=rows.clinvar.clinical_significance,
                alleleId=rows.clinvar.allele_id,
                goldStars=rows.clinvar.gold_stars,
            ),
            genotypeFilters=hl.str(' ,').join(rows.filters),
        )
        # TODO populations and predictions

        rows = rows.rename({'contig': 'chrom'})
        rows = rows.select(
            'chrom', 'pos', 'ref', 'alt', 'rg37_locus', 'genotypes', 'sortedTranscriptConsequences', 'variantId',
            'genotypeFilters', 'clinvar', 'hgmd','rsid', 'xpos', # TODO populations and predictions
        )
        collected = rows.take(num_results)

        # localized = self.mt.localize_entries("ent", "s")
        # localized = localized.transmute(GT=localized.ent.GT)
        #
        # collected = localized.take(num_results)
        # sample_info = hl.eval(localized.globals.s)
        # sample_ids = [sample.s for sample in sample_info]

        hail_results = []
        for variant in collected:
            transcripts = defaultdict(lambda: list())
            for tc in variant.sortedTranscriptConsequences:
                tc_dict = dict(tc.drop("domains"))
                tc_dict = {_to_camel_case(k): v for k, v in tc_dict.items()}
                transcripts[tc.gene_id].append(tc_dict)

            result = {
                'transcripts': transcripts,
                'mainTranscriptId': variant.sortedTranscriptConsequences[0].transcript_id,
                'familyGuids': family_guids,
                'genomeVersion': GENOME_VERSION_GRCh38,
                'liftedOverGenomeVersion': None,
                'liftedOverChrom': variant.rg37_locus.contig,
                'liftedOverPos': variant.rg37_locus.position,
            }
            variant.drop('locus', 'alleles', 'sortedTranscriptConsequences')
            result.update(variant)
            result['genotypes'] = {sample_individuals[gen['sampleId']]: gen for gen in result['genotypes']}

            # genotypes = {sample_individuals[sample_id]: {
            #     "sampleId": sample_id,
            #     "numAlt": gt_call.n_alt_alleles(),
            #     "gq": 0,
            #     "ab": 0,
            #     "dp": 0
            # } for sample_id, gt_call in zip(sample_ids, s.GT)}
            #
            # transcripts = defaultdict(lambda: list())
            # for tc in s.vep.transcript_consequences:
            #     tc_dict = dict(tc.drop("domains"))
            #     tc_dict = {_to_camel_case(k): v for k, v in tc_dict.items()}
            #     #  TODO should be sorted
            #     tc_dict["majorConsequence"] = tc_dict["consequenceTerms"][0]
            #     transcripts[tc.gene_id].append(tc_dict)
            #
            # hail_results.append({
            #     'chrom': s.locus.contig,
            #     'pos': s.locus.position,
            #     'ref': s.alleles[0],
            #     'alt': s.alleles[1],
            #     'genotypes': genotypes,
            #     'transcripts': transcripts,
            #     'mainTranscriptId': s.vep.transcript_consequences[0].transcript_id,
            #     'variantId': str(idx),
            #     'familyGuids': family_guids,
            #     'genomeVersion': GENOME_VERSION_GRCh38,
            #     'liftedOverGenomeVersion': None,
            #     'liftedOverChrom': None, # TODO rg37_locus
            #     'liftedOverPos': None, # TODO rg37_locus
            #     'clinvar': {}, # TODO
            #     'hgmd': {},  # TODO
            #     'populations': {}, # TODO
            #     'predictions': {}, # TODO
            #     # 'filters': {'response_key': 'genotypeFilters', 'format_value': ', '.join, 'default_value': ''},
            #     # 'num_exon': {'response_key': 'numExon'},
            #     # 'originalAltAlleles': {'format_value': lambda alleles: [a.split('-')[-1] for a in alleles], 'default_value': []},
            #     # 'rsid': {},
            #     # 'xpos': {'format_value': int},
            #     # 'algorithms': {'format_value': ', '.join}
            # })
            #

        # TODO format return values into correct dicts, potentially post-process compound hets

        # TODO get total number results beyond the current page (currently computes up to 10000)
        self.previous_search_results['total_results'] = len(hail_results)

        return hail_results
