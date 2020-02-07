from collections import defaultdict
from copy import deepcopy
import elasticsearch
from elasticsearch_dsl import Search, Q, MultiSearch
import hashlib
import json
import logging
from pyliftover.liftover import LiftOver
from sys import maxint
from itertools import combinations

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.constants import XPOS_SORT_KEY, COMPOUND_HET, RECESSIVE, X_LINKED_RECESSIVE, \
    HAS_ALT_FIELD_KEYS, GENOTYPES_FIELD_KEY, GENOTYPE_FIELDS_CONFIG, POPULATION_RESPONSE_FIELD_CONFIGS, POPULATIONS, \
    SORTED_TRANSCRIPTS_FIELD_KEY, CORE_FIELDS_CONFIG, NESTED_FIELDS, PREDICTION_FIELDS_CONFIG, INHERITANCE_FILTERS, \
    QUERY_FIELD_NAMES, REF_REF, IS_OR_INHERITANCE, GENOTYPE_QUERY_MAP, CLINVAR_SIGNFICANCE_MAP, HGMD_CLASS_MAP, \
    SORT_FIELDS, MAX_VARIANTS, MAX_COMPOUND_HET_GENES, MAX_INDEX_NAME_LENGTH
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.json_utils import _to_camel_case

logger = logging.getLogger(__name__)


class EsSearch(object):

    AGGREGATION_NAME = 'compound het'
    CACHED_COUNTS_KEY = 'loaded_variant_counts'

    def __init__(self, families, previous_search_results=None, skip_unaffected_families=False, return_all_queried_families=False):
        from seqr.utils.elasticsearch.utils import get_es_client, InvalidIndexException
        self._client = get_es_client()

        self.samples_by_family_index = defaultdict(lambda: defaultdict(dict))
        for s in Sample.objects.filter(
            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
            elasticsearch_index__isnull=False,
            is_active=True,
            individual__family__in=families
        ).prefetch_related('individual', 'individual__family'):
            self.samples_by_family_index[s.elasticsearch_index][s.individual.family.guid][s.sample_id] = s

        if len(self.samples_by_family_index) < 1:
            raise InvalidIndexException('No es index found')

        if skip_unaffected_families:
            for index, family_samples in self.samples_by_family_index.items():
                index_skipped_families = []
                for family_guid, samples_by_id in family_samples.items():
                    if not any(s.individual.affected == Individual.AFFECTED_STATUS_AFFECTED
                               for s in samples_by_id.values()):
                        index_skipped_families.append(family_guid)

                for family_guid in index_skipped_families:
                    del self.samples_by_family_index[index][family_guid]

                if not self.samples_by_family_index[index]:
                    del self.samples_by_family_index[index]

            if len(self.samples_by_family_index) < 1:
                raise Exception('Inheritance based search is disabled in families with no affected individuals')

        self._set_index_metadata()

        if len(self.samples_by_family_index) != len(self.index_metadata):
            raise InvalidIndexException('Could not find expected indices: {}'.format(
                ', '.join(set(self.samples_by_family_index.keys()) - set(self.index_metadata.keys()))
            ))

        self.previous_search_results = previous_search_results or {}
        self._return_all_queried_families = return_all_queried_families

        self._search = Search()
        self._index_searches = defaultdict(list)
        self._sort = None
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._filtered_variant_ids = None
        self._no_sample_filters = False
        self._family_individual_affected_status = {}

    def _set_index_metadata(self):
        from seqr.utils.elasticsearch.utils import get_index_metadata
        self.index_name = ','.join(sorted(self.samples_by_family_index.keys()))
        if len(self.index_name) > MAX_INDEX_NAME_LENGTH:
            alias = hashlib.md5(self.index_name).hexdigest()
            cache_key = 'index_alias__{}'.format(alias)
            if safe_redis_get_json(cache_key) != self.index_name:
                self._client.indices.update_aliases(body={'actions': [
                    {'add': {'indices': self.samples_by_family_index.keys(), 'alias': alias}}
                ]})
                safe_redis_set_json(cache_key, self.index_name)
            self.index_name = alias
        self.index_metadata = get_index_metadata(self.index_name, self._client)

    def sort(self, sort):
        self._sort = _get_sort(sort)
        self._search = self._search.sort(*self._sort)

    def filter(self, new_filter):
        self._search = self._search.filter(new_filter)
        return self

    def filter_by_frequency(self, frequencies):
        self.filter(_frequency_filter(frequencies))

    def filter_by_annotations(self, annotations, pathogenicity_filter):
        consequences_filter, allowed_consequences = _annotations_filter(annotations or {})
        if allowed_consequences:
            if pathogenicity_filter:
                # Pathogencicity and transcript consequences act as "OR" filters instead of the usual "AND"
                consequences_filter |= pathogenicity_filter
            self.filter(consequences_filter)
            self._allowed_consequences = allowed_consequences
        elif pathogenicity_filter:
            self.filter(pathogenicity_filter)

    def filter_by_location(self, genes=None, intervals=None, rs_ids=None, variant_ids=None, locus=None):
        genome_version = locus and locus.get('genomeVersion')
        variant_id_genome_versions = {variant_id: genome_version for variant_id in variant_ids or []}
        if variant_id_genome_versions and genome_version:
            lifted_genome_version = GENOME_VERSION_GRCh37 if genome_version == GENOME_VERSION_GRCh38 else GENOME_VERSION_GRCh38
            liftover = _liftover_grch38_to_grch37() if genome_version == GENOME_VERSION_GRCh38 else _liftover_grch37_to_grch38()
            if liftover:
                for variant_id in deepcopy(variant_ids):
                    chrom, pos, ref, alt = self.parse_variant_id(variant_id)
                    lifted_coord = liftover.convert_coordinate('chr{}'.format(chrom), pos)
                    if lifted_coord and lifted_coord[0]:
                        lifted_variant_id = '{chrom}-{pos}-{ref}-{alt}'.format(
                            chrom=lifted_coord[0][0].lstrip('chr'), pos=lifted_coord[0][1], ref=ref, alt=alt
                        )
                        variant_id_genome_versions[lifted_variant_id] = lifted_genome_version
                        variant_ids.append(lifted_variant_id)

        self.filter(_location_filter(genes, intervals, rs_ids, variant_ids, locus))
        if len({genome_version for genome_version in variant_id_genome_versions.items()}) > 1 and not (genes or intervals or rs_ids):
            self._filtered_variant_ids = variant_id_genome_versions
        return self

    def filter_by_annotation_and_genotype(self, inheritance, quality_filter=None, annotations=None, annotations_secondary=None, pathogenicity=None):
        has_previous_compound_hets = self.previous_search_results.get('grouped_results')

        inheritance_mode = (inheritance or {}).get('mode')
        inheritance_filter = (inheritance or {}).get('filter') or {}
        if inheritance_filter.get('genotype'):
            inheritance_mode = None

        quality_filter = dict({'min_ab': 0, 'min_gq': 0}, **(quality_filter or {}))
        if quality_filter['min_ab'] % 5 != 0:
            raise Exception('Invalid ab filter {}'.format(quality_filter['min_ab']))
        if quality_filter['min_gq'] % 5 != 0:
            raise Exception('Invalid gq filter {}'.format(quality_filter['min_gq']))

        if quality_filter and quality_filter.get('vcf_filter') is not None:
            self.filter(~Q('exists', field='filters'))

        annotations_secondary_search = None
        if annotations_secondary:
            annotations_secondary_filter, allowed_consequences_secondary = _annotations_filter(annotations_secondary)
            annotations_filter, _ = _annotations_filter(annotations)
            annotations_secondary_search = self._search.filter(annotations_filter | annotations_secondary_filter)
            self._allowed_consequences_secondary = allowed_consequences_secondary

        pathogenicity_filter = _pathogenicity_filter(pathogenicity or {})
        if annotations or pathogenicity_filter:
            self.filter_by_annotations(annotations, pathogenicity_filter)

        for index, family_samples_by_id in self.samples_by_family_index.items():
            if not inheritance and not quality_filter['min_ab'] and not quality_filter['min_gq']:
                search_sample_count = sum(len(samples) for samples in family_samples_by_id.values())
                index_sample_count = Sample.objects.filter(elasticsearch_index=index, is_active=True).count()
                if search_sample_count == index_sample_count:
                    # If searching across all families in an index with no inheritance mode we do not need to explicitly
                    # filter on inheritance, as all variants have some inheritance for at least one family
                    self._no_sample_filters = True
                    continue

            genotypes_q, index_family_individual_affected_status = _genotype_inheritance_filter(
                inheritance_mode, inheritance_filter, family_samples_by_id, quality_filter,
            )
            self._family_individual_affected_status.update(index_family_individual_affected_status)

            compound_het_q = None
            if inheritance_mode == COMPOUND_HET:
                compound_het_q = genotypes_q
            else:
                self._index_searches[index].append(self._search.filter(genotypes_q))

            if inheritance_mode == RECESSIVE:
                compound_het_q, _ = _genotype_inheritance_filter(
                    COMPOUND_HET, inheritance_filter, family_samples_by_id, quality_filter,
                )

            if compound_het_q and not has_previous_compound_hets:
                compound_het_search = (annotations_secondary_search or self._search).filter(compound_het_q)
                compound_het_search.aggs.bucket(
                    'genes', 'terms', field='geneIds', min_doc_count=2, size=MAX_COMPOUND_HET_GENES+1
                ).metric(
                    'vars_by_gene', 'top_hits', size=100, sort=self._sort, _source=QUERY_FIELD_NAMES
                )
                self._index_searches[index].append(compound_het_search)

    def search(self,  **kwargs):
        indices = self.samples_by_family_index.keys()

        logger.info('Searching in elasticsearch indices: {}'.format(', '.join(indices)))

        is_single_search, search_kwargs = self._should_execute_single_search(**kwargs)

        if is_single_search:
            return self._execute_single_search(**search_kwargs)
        elif not self._index_searches:
            return self._execute_single_search(**search_kwargs)
        else:
            return self._execute_multi_search(**search_kwargs)

    def _should_execute_single_search(self, page=1, num_results=100):
        indices = self.samples_by_family_index.keys()
        is_single_search = len(indices) == 1 and len(self._index_searches.get(indices[0], [])) <= 1
        num_loaded = len(self.previous_search_results.get('all_results', []))

        if is_single_search and not self.previous_search_results.get('grouped_results'):
            start_index = None
            if (page - 1) * num_results < num_loaded:
                start_index = num_loaded
            return True, {'page': page, 'num_results': num_results, 'start_index': start_index}
        elif not self._index_searches:
            # If doing all project-families all inheritance search, do it as a single query
            # Load all variants, do not skip pages
            num_loaded += self.previous_search_results.get('duplicate_doc_count', 0)
            if num_loaded >= (page - 1) * num_results:
                start_index = num_loaded
            else:
                start_index = 0
            return True, {'page': page, 'num_results': num_results, 'start_index': start_index, 'deduplicate': True}
        else:
            return False, {'page': page, 'num_results': num_results}

    def _execute_single_search(self, page=1, num_results=100, start_index=None, **kwargs):
        search = self._get_paginated_searches(
            self.index_name, page=page, num_results=num_results, start_index=start_index
        )[0]
        response = self._execute_search(search)
        parsed_response = self._parse_response(response)
        return self._process_single_search_response(parsed_response, page=page, num_results=num_results, **kwargs)

    def _process_single_search_response(self, parsed_response, page=1, num_results=100, deduplicate=False, **kwargs):
        variant_results, total_results, is_compound_het, _ = parsed_response
        self.previous_search_results['total_results'] = total_results

        results_start_index = (page - 1) * num_results
        if is_compound_het:
            variant_results = _sort_compound_hets(variant_results)
            self.previous_search_results['grouped_results'] = variant_results
            end_index = min(results_start_index + num_results, total_results)
            return _get_compound_het_page(variant_results, results_start_index, end_index)

        if deduplicate:
            variant_results = self._deduplicate_results(variant_results)

        # Only save contiguous pages of results:
        previous_all_results = self.previous_search_results.get('all_results', [])
        if len(previous_all_results) >= results_start_index:
            self.previous_search_results['all_results'] = self.previous_search_results.get('all_results', []) + variant_results
            variant_results = self.previous_search_results['all_results'][results_start_index:]

        return variant_results[:num_results]

    def _execute_multi_search(self, **kwargs):
        indices = self.samples_by_family_index.keys()

        if self.CACHED_COUNTS_KEY and not self.previous_search_results.get(self.CACHED_COUNTS_KEY):
            self.previous_search_results[self.CACHED_COUNTS_KEY] = {}

        ms = MultiSearch()
        for index_name in indices:
            start_index = 0
            if self.CACHED_COUNTS_KEY:
                if self.previous_search_results[self.CACHED_COUNTS_KEY].get(index_name):
                    index_total = self.previous_search_results[self.CACHED_COUNTS_KEY][index_name]['total']
                    start_index = self.previous_search_results[self.CACHED_COUNTS_KEY][index_name]['loaded']
                    if start_index >= index_total:
                        continue
                else:
                    self.previous_search_results[self.CACHED_COUNTS_KEY][index_name] = {'loaded': 0, 'total': 0}

            searches = self._get_paginated_searches(index_name, start_index=start_index, **kwargs)
            ms = ms.index(index_name)
            for search in searches:
                ms = ms.add(search)

        responses = self._execute_search(ms)
        parsed_responses = [self._parse_response(response) for response in responses]
        return self._process_multi_search_responses(parsed_responses, **kwargs)

    def _process_multi_search_responses(self, parsed_responses, page=1, num_results=100):
        new_results = []
        compound_het_results = self.previous_search_results.get('compound_het_results', [])
        for response_hits, response_total, is_compound_het, index_name in parsed_responses:
            if not response_total:
                continue

            if is_compound_het:
                compound_het_results += response_hits
                self.previous_search_results['loaded_variant_counts']['{}_compound_het'.format(index_name)] = {
                    'total': response_total, 'loaded': response_total}
            else:
                new_results += response_hits
                self.previous_search_results['loaded_variant_counts'][index_name]['total'] = response_total
                self.previous_search_results['loaded_variant_counts'][index_name]['loaded'] += len(response_hits)

        self.previous_search_results['total_results'] = sum(
            counts['total'] for counts in self.previous_search_results['loaded_variant_counts'].values())

        # combine new results with unsorted previously loaded results to correctly sort/paginate
        all_loaded_results = self.previous_search_results.get('all_results', [])
        new_results += self.previous_search_results.get('variant_results', [])

        new_results = sorted(new_results, key=lambda variant: variant['_sort'])
        variant_results = self._deduplicate_results(new_results)

        if compound_het_results or self.previous_search_results.get('grouped_results'):
            if compound_het_results:
                compound_het_results = self._deduplicate_compound_het_results(compound_het_results)
                compound_het_results = _sort_compound_hets(compound_het_results)
            return self._process_compound_hets(compound_het_results, variant_results, num_results)
        else:
            end_index = num_results * page
            num_loaded = num_results * page - len(all_loaded_results)
            self.previous_search_results['all_results'] = all_loaded_results + variant_results[:num_loaded]
            self.previous_search_results['variant_results'] = variant_results[num_loaded:]
            return self.previous_search_results['all_results'][end_index-num_results:end_index]

    def _parse_response(self, response):
        index_name = response.hits[0].meta.index if response.hits else None
        if hasattr(response.aggregations, 'genes') and response.hits:
            response_hits, response_total = self._parse_compound_het_response(response)
            return response_hits, response_total, True, index_name

        response_total = response.hits.total
        logger.info('Total hits: {} ({} seconds)'.format(response_total, response.took / 1000.0))

        return [self._parse_hit(hit) for hit in response], response_total, False, index_name

    def _parse_hit(self, raw_hit):
        hit = {k: raw_hit[k] for k in QUERY_FIELD_NAMES if k in raw_hit}
        index_name = raw_hit.meta.index
        index_family_samples = self.samples_by_family_index[index_name]

        if hasattr(raw_hit.meta, 'matched_queries'):
            family_guids = list(raw_hit.meta.matched_queries)
        elif self._return_all_queried_families:
            family_guids = index_family_samples.keys()
        else:
            # Searches for all inheritance and all families do not filter on inheritance so there are no matched_queries
            alt_allele_samples = set()
            for alt_samples_field in HAS_ALT_FIELD_KEYS:
                alt_allele_samples.update(hit[alt_samples_field])
            family_guids = [family_guid for family_guid, samples_by_id in index_family_samples.items()
                            if any(sample_id in alt_allele_samples for sample_id in samples_by_id.keys())]

        genotypes = {}
        for family_guid in family_guids:
            samples_by_id = index_family_samples[family_guid]
            genotypes.update({
                samples_by_id[genotype_hit['sample_id']].individual.guid: _get_field_values(genotype_hit, GENOTYPE_FIELDS_CONFIG)
                for genotype_hit in hit[GENOTYPES_FIELD_KEY] if genotype_hit['sample_id'] in samples_by_id
            })

        genome_version = self.index_metadata[index_name]['genomeVersion']
        lifted_over_genome_version = None
        lifted_over_chrom = None
        lifted_over_pos = None
        liftover_grch38_to_grch37 = _liftover_grch38_to_grch37()
        if liftover_grch38_to_grch37 and genome_version == GENOME_VERSION_GRCh38:
            if liftover_grch38_to_grch37:
                grch37_coord = liftover_grch38_to_grch37.convert_coordinate(
                    'chr{}'.format(hit['contig'].lstrip('chr')), int(hit['start'])
                )
                if grch37_coord and grch37_coord[0]:
                    lifted_over_genome_version = GENOME_VERSION_GRCh37
                    lifted_over_chrom = grch37_coord[0][0].lstrip('chr')
                    lifted_over_pos = grch37_coord[0][1]

        populations = {
            population: _get_field_values(
                hit, POPULATION_RESPONSE_FIELD_CONFIGS, format_response_key=lambda key: key.lower(),
                lookup_field_prefix=population,
                existing_fields=self.index_metadata[index_name]['fields'],
                get_addl_fields=lambda field, field_config:
                [pop_config.get(field)] + ['{}_{}'.format(population, custom_field) for custom_field in
                                           field_config.get('fields', [])],
            )
            for population, pop_config in POPULATIONS.items()
        }

        sorted_transcripts = [
            {_to_camel_case(k): v for k, v in transcript.to_dict().items()}
            for transcript in hit[SORTED_TRANSCRIPTS_FIELD_KEY] or []
        ]
        transcripts = defaultdict(list)
        for transcript in sorted_transcripts:
            transcripts[transcript['geneId']].append(transcript)

        result = _get_field_values(hit, CORE_FIELDS_CONFIG, format_response_key=str)
        result.update({
            field_name: _get_field_values(hit, fields, lookup_field_prefix=field_name)
            for field_name, fields in NESTED_FIELDS.items()
        })
        if hasattr(raw_hit.meta, 'sort'):
            result['_sort'] = [_parse_es_sort(sort, self._sort[i]) for i, sort in enumerate(raw_hit.meta.sort)]

        result.update({
            'familyGuids': sorted(family_guids),
            'genotypes': genotypes,
            'genomeVersion': genome_version,
            'liftedOverGenomeVersion': lifted_over_genome_version,
            'liftedOverChrom': lifted_over_chrom,
            'liftedOverPos': lifted_over_pos,
            'mainTranscriptId': sorted_transcripts[0]['transcriptId'] if len(sorted_transcripts) else None,
            'populations': populations,
            'predictions': _get_field_values(
                hit, PREDICTION_FIELDS_CONFIG, format_response_key=lambda key: key.split('_')[1].lower()
            ),
            'transcripts': transcripts,
        })
        return result

    def _parse_compound_het_response(self, response):
        if len(response.aggregations.genes.buckets) > MAX_COMPOUND_HET_GENES:
            raise Exception('This search returned too many compound heterozygous variants. Please add stricter filters')

        family_unaffected_individual_guids = {
            family_guid: {individual_guid for individual_guid, affected_status in individual_affected_status.items() if
                          affected_status == Individual.AFFECTED_STATUS_UNAFFECTED}
            for family_guid, individual_affected_status in self._family_individual_affected_status.items()
        }

        compound_het_pairs_by_gene = {}
        for gene_agg in response.aggregations.genes.buckets:
            gene_variants = [self._parse_hit(hit) for hit in gene_agg['vars_by_gene']]
            gene_id = gene_agg['key']

            if gene_id in compound_het_pairs_by_gene:
                continue

            # Variants are returned if any transcripts have the filtered consequence, but to be compound het
            # the filtered consequence needs to be present in at least one transcript in the gene of interest
            if self._allowed_consequences:
                gene_variants = [variant for variant in gene_variants if any(
                    transcript['majorConsequence'] in self._allowed_consequences + (self._allowed_consequences_secondary or [])
                    for transcript in variant['transcripts'][gene_id]
                )]

            if len(gene_variants) < 2:
                continue

            # Do not include groups multiple times if identical variants are in the same multiple genes
            if any(all(t['transcriptId'] != variant['mainTranscriptId']
                       for t in variant['transcripts'][gene_id]) for variant in gene_variants):
                if not self._is_primary_compound_het_gene(gene_id, gene_variants, compound_het_pairs_by_gene):
                    continue

            family_compound_het_pairs = defaultdict(list)
            for variant in gene_variants:
                for family_guid in variant['familyGuids']:
                    family_compound_het_pairs[family_guid].append(variant)

            self._filter_invalid_family_compound_hets(gene_id, family_compound_het_pairs, family_unaffected_individual_guids)

            gene_compound_het_pairs = [ch_pair for ch_pairs in family_compound_het_pairs.values() for ch_pair in ch_pairs]
            for compound_het_pair in gene_compound_het_pairs:
                for variant in compound_het_pair:
                    variant['familyGuids'] = [family_guid for family_guid in variant['familyGuids']
                                              if len(family_compound_het_pairs[family_guid]) > 0]
            gene_compound_het_pairs = [compound_het_pair for compound_het_pair in gene_compound_het_pairs
                                       if compound_het_pair[0]['familyGuids'] and compound_het_pair[1]['familyGuids']]
            if gene_compound_het_pairs:
                compound_het_pairs_by_gene[gene_id] = gene_compound_het_pairs

        total_compound_het_results = sum(len(compound_het_pairs) for compound_het_pairs in compound_het_pairs_by_gene.values())
        logger.info('Total compound het hits: {}'.format(total_compound_het_results))

        compound_het_results = []
        for k, compound_het_pairs in compound_het_pairs_by_gene.items():
            compound_het_results.extend([{k: compound_het_pair} for compound_het_pair in compound_het_pairs])
        return compound_het_results, total_compound_het_results

    def _is_primary_compound_het_gene(self, gene_id, gene_variants, compound_het_pairs_by_gene):
        primary_genes = set()
        for variant in gene_variants:
            for gene, transcripts in variant['transcripts'].items():
                if any(t['transcriptId'] == variant['mainTranscriptId'] for t in transcripts):
                    primary_genes.add(gene)
                    break
        if len(primary_genes) == 1:
            is_valid_gene = True
            primary_gene = primary_genes.pop()
            if self._allowed_consequences:
                is_valid_gene = all(any(
                    transcript['majorConsequence'] in self._allowed_consequences for transcript in
                    variant['transcripts'][primary_gene]
                ) for variant in gene_variants)
            if is_valid_gene:
                if primary_gene != gene_id:
                    return False

        else:
            variant_ids = [variant['variantId'] for variant in gene_variants]
            for gene in primary_genes:
                if variant_ids == [compound_het_pair[0]['variantId'] for compound_het_pair in
                                   compound_het_pairs_by_gene.get(gene, [])] and \
                        variant_ids == [compound_het_pair[1]['variantId'] for compound_het_pair in
                                        compound_het_pairs_by_gene.get(gene, [])]:
                    return False
        return True

    def _filter_invalid_family_compound_hets(self, gene_id, family_compound_het_pairs, family_unaffected_individual_guids):
        for family_guid, variants in family_compound_het_pairs.items():
            unaffected_individuals_num_alts = [
                [variant['genotypes'].get(individual_guid, {}).get('numAlt') for variant in variants]
                for individual_guid in family_unaffected_individual_guids.get(family_guid, [])]

            def _is_a_valid_compound_het_pair(variant_1_index, variant_2_index):
                # To be compound het all unaffected individuals need to be hom ref for at least one of the variants
                for unaffected_individual_num_alts in unaffected_individuals_num_alts:
                    is_valid_for_individual = any(unaffected_individual_num_alts[variant_index] != 1
                                                  for variant_index in [variant_1_index, variant_2_index])
                    if not is_valid_for_individual:
                        return False
                return True

            valid_combinations = [[ch_1_index, ch_2_index] for ch_1_index, ch_2_index in
                                  combinations(range(len(variants)), 2)
                                  if _is_a_valid_compound_het_pair(ch_1_index, ch_2_index)]
            compound_het_pairs = [[variants[valid_ch_1_index], variants[valid_ch_2_index]] for
                                  valid_ch_1_index, valid_ch_2_index in valid_combinations]

            # remove compound hets pair that only satisfied secondary consequence
            if self._allowed_consequences and self._allowed_consequences_secondary:
                compound_het_pairs = [compound_het_pair for compound_het_pair in compound_het_pairs if any([
                    any(transcript['majorConsequence'] in self._allowed_consequences for transcript in
                        variant['transcripts'][gene_id]) for variant in compound_het_pair])]
            family_compound_het_pairs[family_guid] = compound_het_pairs

    def _deduplicate_results(self, sorted_new_results):
        original_result_count = len(sorted_new_results)

        if self._filtered_variant_ids:
            sorted_new_results = [
                v for v in sorted_new_results if self._filtered_variant_ids.get(v['variantId']) == v['genomeVersion']
            ]

        genome_builds = {var['genomeVersion'] for var in sorted_new_results}
        if len(genome_builds) > 1:
            variant_results = self._deduplicate_multi_genome_variant_results(sorted_new_results)
        else:
            variant_results = []
            for variant in sorted_new_results:
                if variant_results and variant_results[-1]['variantId'] == variant['variantId']:
                    self._merge_duplicate_variants(variant_results[-1], variant)
                else:
                    variant_results.append(variant)

        previous_duplicates = self.previous_search_results.get('duplicate_doc_count', 0)
        new_duplicates = original_result_count - len(variant_results)
        self.previous_search_results['duplicate_doc_count'] = previous_duplicates + new_duplicates

        self.previous_search_results['total_results'] -= self.previous_search_results['duplicate_doc_count']

        return variant_results

    @classmethod
    def _deduplicate_multi_genome_variant_results(cls, sorted_new_results):
        hg_38_variant_indices = {}
        hg_37_variant_indices = {}

        variant_results = []
        for i, variant in enumerate(sorted_new_results):
            if variant['genomeVersion'] == GENOME_VERSION_GRCh38:
                hg37_id = '{}-{}-{}-{}'.format(variant['liftedOverChrom'], variant['liftedOverPos'], variant['ref'],
                                               variant['alt'])
                existing_38_index = hg_38_variant_indices.get(hg37_id)
                if existing_38_index is not None:
                    cls._merge_duplicate_variants(variant_results[existing_38_index], variant)
                    variant_results.append(None)
                else:
                    existing_37_index = hg_37_variant_indices.get(hg37_id)
                    if existing_37_index is not None:
                        cls._merge_duplicate_variants(variant, variant_results[existing_37_index])
                        variant_results[existing_37_index] = None

                    hg_38_variant_indices[hg37_id] = i
                    variant_results.append(variant)
            else:
                existing_38_index = hg_38_variant_indices.get(variant['variantId'])
                existing_37_index = hg_37_variant_indices.get(variant['variantId'])
                if existing_38_index is not None:
                    cls._merge_duplicate_variants(variant_results[existing_38_index], variant)
                    variant_results.append(None)
                elif existing_37_index is not None:
                    cls._merge_duplicate_variants(variant_results[existing_37_index], variant)
                    variant_results.append(None)
                else:
                    hg_37_variant_indices[variant['variantId']] = i
                    variant_results.append(variant)

        return [var for var in variant_results if var]

    @classmethod
    def _merge_duplicate_variants(cls, variant, duplicate_variant):
        variant['genotypes'].update(duplicate_variant['genotypes'])
        variant['familyGuids'] = sorted(set(variant['familyGuids'] + duplicate_variant['familyGuids']))

    def _deduplicate_compound_het_results(self, compound_het_results):
        duplicates = 0
        results = {}
        for gene_compound_het_pair in compound_het_results:
            gene = gene_compound_het_pair.keys()[0]
            compound_het_pair = gene_compound_het_pair[gene]
            if gene in results:
                variant_ids = {variant['variantId'] for variant in compound_het_pair}
                existing_index = next(
                    (i for i, existing in enumerate(results[gene]) if
                     {variant['variantId'] for variant in existing} == variant_ids), None,
                )
                if existing_index is not None:
                    existing_compound_het_pair = results[gene][existing_index]

                    def _update_existing_variant(existing_variant, variant):
                        existing_variant['genotypes'].update(variant['genotypes'])
                        existing_variant['familyGuids'] = sorted(
                            existing_variant['familyGuids'] + variant['familyGuids']
                        )
                    if existing_compound_het_pair[0]['variantId'] == compound_het_pair[0]['variantId']:
                        _update_existing_variant(existing_compound_het_pair[0], compound_het_pair[0])
                        _update_existing_variant(existing_compound_het_pair[1], compound_het_pair[1])
                    else:
                        _update_existing_variant(existing_compound_het_pair[0], compound_het_pair[1])
                        _update_existing_variant(existing_compound_het_pair[1], compound_het_pair[0])
                    duplicates += 1
                else:
                    results[gene].append(compound_het_pair)
            else:
                results[gene] = [compound_het_pair]

        deduplicated_results = []
        for gene, compound_het_pairs in results.items():
            deduplicated_results += [{gene: ch_pair} for ch_pair in compound_het_pairs]

        self.previous_search_results['duplicate_doc_count'] = duplicates + self.previous_search_results.get('duplicate_doc_count', 0)
        self.previous_search_results['total_results'] -= duplicates

        return deduplicated_results

    def _process_compound_hets(self, compound_het_results, variant_results, num_results):
        if not self.previous_search_results.get('grouped_results'):
            self.previous_search_results['grouped_results'] = []

        # Sort merged result sets
        grouped_variants = [{None: [var]} for var in variant_results]
        grouped_variants = compound_het_results + grouped_variants
        grouped_variants = _sort_compound_hets(grouped_variants)

        loaded_result_count = len(grouped_variants + self.previous_search_results['grouped_results'])

        # Get requested page of variants
        merged_variant_results = []
        num_compound_hets = 0
        num_single_variants = 0
        for variants_group in grouped_variants:
            variants = variants_group.values()[0]

            if loaded_result_count != self.previous_search_results['total_results']:
                self.previous_search_results['grouped_results'].append(variants_group)
            if len(variants) > 1:
                merged_variant_results.append(variants)
                num_compound_hets += 1
            else:
                merged_variant_results += variants
                num_single_variants += 1
            if len(merged_variant_results) >= num_results:
                break

        # Only save non-returned results separately if have not loaded all results
        if loaded_result_count == self.previous_search_results['total_results']:
            self.previous_search_results['grouped_results'] += grouped_variants
            self.previous_search_results['compound_het_results'] = []
            self.previous_search_results['variant_results'] = []
        else:
            self.previous_search_results['compound_het_results'] = compound_het_results[num_compound_hets:]
            self.previous_search_results['variant_results'] = variant_results[num_single_variants:]
        return merged_variant_results

    def _get_paginated_searches(self, index_name, page=1, num_results=100, start_index=None):
        searches = []
        for search in self._index_searches.get(index_name, [self._search]):
            search = search.index(index_name)

            if search.aggs.to_dict():
                # For compound het search get results from aggregation instead of top level hits
                search = search[:1]
                logger.info('Loading {}s for {}'.format(self.AGGREGATION_NAME, index_name))
            else:
                end_index = page * num_results
                if start_index is None:
                    start_index = end_index - num_results
                if end_index > MAX_VARIANTS:
                    # ES request size limits are limited by offset + size, which is the same as end_index
                    raise Exception(
                        'Unable to load more than {} variants ({} requested)'.format(MAX_VARIANTS, end_index))

                search = search[start_index:end_index]
                search = search.source(QUERY_FIELD_NAMES)
                logger.info('Loading {} records {}-{}'.format(index_name, start_index, end_index))

            searches.append(search)
        return searches

    def _execute_search(self, search):
        logger.debug(json.dumps(search.to_dict(), indent=2))
        try:
            return search.using(self._client).execute()
        except elasticsearch.exceptions.ConnectionTimeout as e:
            canceled = self._delete_long_running_tasks()
            logger.error('ES Query Timeout. Canceled {} long running searches'.format(canceled))
            raise e

    def _delete_long_running_tasks(self):
        search_tasks = self._client.tasks.list(actions='*search', group_by='parents')
        canceled = 0
        for parent_id, task in search_tasks['tasks'].items():
            if task['running_time_in_nanos'] > 10 ** 11:
                canceled += 1
                self._client.tasks.cancel(parent_task_id=parent_id)
        return canceled

    @classmethod
    def process_previous_results(cls, previous_search_results, page=1, num_results=100, load_all=False):
        num_results_to_use = num_results
        total_results = previous_search_results.get('total_results')
        if load_all:
            num_results_to_use = total_results or MAX_VARIANTS
        start_index = (page - 1) * num_results_to_use
        end_index = page * num_results_to_use
        if previous_search_results.get('total_results') is not None:
            end_index = min(end_index, previous_search_results['total_results'])

        loaded_results = previous_search_results.get('all_results') or []
        if len(loaded_results) >= end_index:
            return loaded_results[start_index:end_index], {}

        grouped_results = previous_search_results.get('grouped_results')
        if grouped_results:
            results = _get_compound_het_page(grouped_results, start_index, end_index)
            if results is not None:
                return results, {}

        return None, {'page': page, 'num_results': num_results_to_use}

    @classmethod
    def parse_variant_id(cls, variant_id):
        var_fields = variant_id.split('-')
        if len(var_fields) != 4:
            raise ValueError('Invalid variant id')
        return var_fields[0].lstrip('chr'), int(var_fields[1]), var_fields[2], var_fields[3]


# TODO  move liftover to hail pipeline once upgraded to 0.2 (https://github.com/macarthur-lab/seqr/issues/1010)
LIFTOVER_GRCH38_TO_GRCH37 = None
def _liftover_grch38_to_grch37():
    global LIFTOVER_GRCH38_TO_GRCH37
    if not LIFTOVER_GRCH38_TO_GRCH37:
        try:
            LIFTOVER_GRCH38_TO_GRCH37 = LiftOver('hg38', 'hg19')
        except Exception as e:
            logger.warn('WARNING: Unable to set up liftover. {}'.format(e))
    return LIFTOVER_GRCH38_TO_GRCH37


LIFTOVER_GRCH37_TO_GRCH38 = None
def _liftover_grch37_to_grch38():
    global LIFTOVER_GRCH37_TO_GRCH38
    if not LIFTOVER_GRCH37_TO_GRCH38:
        try:
            LIFTOVER_GRCH37_TO_GRCH38 = LiftOver('hg19', 'hg38')
        except Exception as e:
            logger.warn('WARNING: Unable to set up liftover. {}'.format(e))
    return LIFTOVER_GRCH37_TO_GRCH38


def _genotype_inheritance_filter(inheritance_mode, inheritance_filter, family_samples_by_id, quality_filter):
    if inheritance_mode:
        inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

    genotypes_q = None
    affected_status = {}
    for family_guid in sorted(family_samples_by_id.keys()):
        samples_by_id = family_samples_by_id[family_guid]
        # Filter samples by quality
        quality_q = None
        if quality_filter.get('min_ab') or quality_filter.get('min_gq'):
            quality_q = Q()
            for sample_id in samples_by_id.keys():
                if quality_filter['min_ab']:
                    q = _build_or_filter('term', [
                        {'samples_ab_{}_to_{}'.format(i, i + 5): sample_id} for i in range(0, quality_filter['min_ab'], 5)
                    ])
                    #  AB only relevant for hets
                    quality_q &= ~Q(q) | ~Q('term', samples_num_alt_1=sample_id)
                if quality_filter['min_gq']:
                    quality_q &= ~Q(_build_or_filter('term', [
                        {'samples_gq_{}_to_{}'.format(i, i + 5): sample_id} for i in range(0, quality_filter['min_gq'], 5)
                    ]))

        # Filter samples by inheritance
        if inheritance_filter:
            family_samples_q, family_individual_affected_status = _family_genotype_inheritance_filter(
                inheritance_mode, inheritance_filter, samples_by_id
            )
            affected_status[family_guid] = family_individual_affected_status

            # For recessive search, should be hom recessive, x-linked recessive, or compound het
            if inheritance_mode == RECESSIVE:
                x_linked_q, _ = _family_genotype_inheritance_filter(X_LINKED_RECESSIVE, inheritance_filter, samples_by_id)
                family_samples_q |= x_linked_q
        else:
            # If no inheritance specified only return variants where at least one of the requested samples has an alt allele
            sample_ids = samples_by_id.keys()
            family_samples_q = Q('terms', samples_num_alt_1=sample_ids) | Q('terms', samples_num_alt_2=sample_ids)

        sample_queries = [family_samples_q]
        if quality_q:
            sample_queries.append(quality_q)

        family_samples_q = Q('bool', must=sample_queries, _name=family_guid)
        if not genotypes_q:
            genotypes_q = family_samples_q
        else:
            genotypes_q |= family_samples_q

    return genotypes_q, affected_status


def _family_genotype_inheritance_filter(inheritance_mode, inheritance_filter, samples_by_id):
    samples_q = None

    individuals = [sample.individual for sample in samples_by_id.values()]

    individual_genotype_filter = inheritance_filter.get('genotype') or {}
    individual_affected_status = inheritance_filter.get('affected') or {}
    for individual in individuals:
        if not individual_affected_status.get(individual.guid):
            individual_affected_status[individual.guid] = individual.affected

    if inheritance_mode == X_LINKED_RECESSIVE:
        samples_q = Q('match', contig='X')
        for individual in individuals:
            if individual_affected_status[individual.guid] == Individual.AFFECTED_STATUS_UNAFFECTED \
                    and individual.sex == Individual.SEX_MALE:
                individual_genotype_filter[individual.guid] = REF_REF

    for sample_id, sample in samples_by_id.items():

        individual_guid = sample.individual.guid
        affected = individual_affected_status[individual_guid]

        genotype = individual_genotype_filter.get(individual_guid) or inheritance_filter.get(affected)

        if genotype:
            not_allowed_num_alt = GENOTYPE_QUERY_MAP[genotype].get('not_allowed_num_alt')
            num_alt_to_filter = not_allowed_num_alt or GENOTYPE_QUERY_MAP[genotype].get('allowed_num_alt')
            sample_filters = [{'samples_{}'.format(num_alt): sample_id} for num_alt in num_alt_to_filter]

            sample_q = _build_or_filter('term', sample_filters)
            if not_allowed_num_alt:
                sample_q = ~Q(sample_q)

            if not samples_q:
                samples_q = sample_q
            elif inheritance_filter.get(IS_OR_INHERITANCE):
                samples_q |= sample_q
            else:
                samples_q &= sample_q

    return samples_q, individual_affected_status


def _location_filter(genes, intervals, rs_ids, variant_ids, location_filter):
    q = None
    if intervals:
        q = _build_or_filter('range', [{
            'xpos': {
                'gte': get_xpos(interval['chrom'], interval['start']),
                'lte': get_xpos(interval['chrom'], interval['end'])
            }
        } for interval in intervals])

    if genes:
        gene_q = Q('terms', geneIds=genes.keys())
        if q:
            q |= gene_q
        else:
            q = gene_q

    if rs_ids:
        rs_id_q = Q('terms', rsid=rs_ids)
        if q:
            q |= rs_id_q
        else:
            q = rs_id_q

    if variant_ids:
        variant_id_q = Q('terms', variantId=variant_ids)
        if q:
            q |= variant_id_q
        else:
            q = variant_id_q

    if location_filter and location_filter.get('excludeLocations'):
        return ~q
    else:
        return q


def _pathogenicity_filter(pathogenicity):
    clinvar_filters = pathogenicity.get('clinvar', [])
    hgmd_filters = pathogenicity.get('hgmd', [])

    pathogenicity_filter = None
    if clinvar_filters:
        clinvar_clinical_significance_terms = set()
        for clinvar_filter in clinvar_filters:
            clinvar_clinical_significance_terms.update(CLINVAR_SIGNFICANCE_MAP.get(clinvar_filter, []))
        pathogenicity_filter = Q('terms', clinvar_clinical_significance=list(clinvar_clinical_significance_terms))

    if hgmd_filters:
        hgmd_class = set()
        for hgmd_filter in hgmd_filters:
            hgmd_class.update(HGMD_CLASS_MAP.get(hgmd_filter, []))

        hgmd_q = Q('terms', hgmd_class=list(hgmd_class))
        pathogenicity_filter = pathogenicity_filter | hgmd_q if pathogenicity_filter else hgmd_q

    return pathogenicity_filter


def _annotations_filter(annotations):
    vep_consequences = [ann for anns in annotations.values() for ann in anns]

    consequences_filter = Q('terms', transcriptConsequenceTerms=vep_consequences)

    if 'intergenic_variant' in vep_consequences:
        # VEP doesn't add annotations for many intergenic variants so match variants where no transcriptConsequenceTerms
        consequences_filter |= ~Q('exists', field='transcriptConsequenceTerms')

    return consequences_filter, vep_consequences


def _pop_freq_filter(filter_key, value):
    return Q('range', **{filter_key: {'lte': value}}) | ~Q('exists', field=filter_key)


def _frequency_filter(frequencies):
    q = Q()
    for pop, freqs in frequencies.items():
        if freqs.get('af') is not None:
            q &= _pop_freq_filter(POPULATIONS[pop]['AF'], freqs['af'])
        elif freqs.get('ac') is not None:
            q &= _pop_freq_filter(POPULATIONS[pop]['AC'], freqs['ac'])

        if freqs.get('hh') is not None:
            q &= _pop_freq_filter(POPULATIONS[pop]['Hom'], freqs['hh'])
            q &= _pop_freq_filter(POPULATIONS[pop]['Hemi'], freqs['hh'])
    return q


def _build_or_filter(op, filters):
    if not filters:
        return None
    q = Q(op, **filters[0])
    for filter_kwargs in filters[1:]:
        q |= Q(op, **filter_kwargs)
    return q


def _get_sort(sort_key):
    sorts = SORT_FIELDS.get(sort_key, [])

    # Add parameters to scripts
    if len(sorts) and isinstance(sorts[0], dict) and sorts[0].get('_script', {}).get('script', {}).get('params'):
        for key, val_func in sorts[0]['_script']['script']['params'].items():
            if not (isinstance(val_func, dict) or isinstance(val_func, list)):
                sorts[0]['_script']['script']['params'][key] = val_func()

    if XPOS_SORT_KEY not in sorts:
        sorts.append(XPOS_SORT_KEY)
    return sorts


def _sort_compound_hets(grouped_variants):
    return sorted(grouped_variants, key=lambda variants: variants.values()[0][0]['_sort'])


def _get_compound_het_page(grouped_variants, start_index, end_index):
    skipped = 0
    variant_results = []
    variant_count = 0
    for variants in grouped_variants:
        curr_variant = variants.values()[0]
        if skipped < start_index:
            skipped += 1
        else:
            if len(curr_variant) == 1:
                variant_results += curr_variant
            else:
                variant_results.append(curr_variant)
            variant_count += 1
        if variant_count + skipped >= end_index:
            return variant_results
    return None


def _parse_es_sort(sort, sort_config):
    if hasattr(sort_config, 'values') and any(cfg.get('order') == 'desc' for cfg in sort_config.values()):
        if sort == 'Infinity':
            sort = -1
        elif sort == '-Infinity' or sort is None:
            # None of the sorts used by seqr return negative values so -1 is fine
            sort = maxint
        else:
            sort = sort * -1

    # ES returns these values for sort when a sort field is missing
    elif sort == 'Infinity':
        sort = maxint
    elif sort == '-Infinity':
        # None of the sorts used by seqr return negative values so -1 is fine
        sort = -1

    return sort


def _get_field_values(hit, field_configs, format_response_key=_to_camel_case, get_addl_fields=None, lookup_field_prefix='', existing_fields=None):
    return {
        field_config.get('response_key', format_response_key(field)): _value_if_has_key(
            hit,
            (get_addl_fields(field, field_config) if get_addl_fields else []) +
            ['{}_{}'.format(lookup_field_prefix, field) if lookup_field_prefix else field],
            existing_fields=existing_fields,
            **field_config
        )
        for field, field_config in field_configs.items()
    }


def _value_if_has_key(hit, keys, format_value=None, default_value=None, existing_fields=None, **kwargs):
    for key in keys:
        if key in hit:
            return format_value(default_value if hit[key] is None else hit[key]) if format_value else hit[key]
    return default_value if not existing_fields or any(key in existing_fields for key in keys) else None