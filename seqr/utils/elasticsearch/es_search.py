from __future__ import unicode_literals

from collections import defaultdict
from copy import deepcopy
import elasticsearch
from elasticsearch_dsl import Search, Q, MultiSearch
import hashlib
import json
import logging
from pyliftover.liftover import LiftOver
from sys import maxsize
from itertools import combinations

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.constants import XPOS_SORT_KEY, COMPOUND_HET, RECESSIVE, X_LINKED_RECESSIVE, \
    HAS_ALT_FIELD_KEYS, GENOTYPES_FIELD_KEY, GENOTYPE_FIELDS_CONFIG, POPULATION_RESPONSE_FIELD_CONFIGS, POPULATIONS, \
    SORTED_TRANSCRIPTS_FIELD_KEY, CORE_FIELDS_CONFIG, NESTED_FIELDS, PREDICTION_FIELDS_CONFIG, INHERITANCE_FILTERS, \
    QUERY_FIELD_NAMES, REF_REF, ANY_AFFECTED, GENOTYPE_QUERY_MAP, CLINVAR_SIGNFICANCE_MAP, HGMD_CLASS_MAP, \
    SORT_FIELDS, MAX_VARIANTS, MAX_COMPOUND_HET_GENES, MAX_INDEX_NAME_LENGTH, SV_DOC_TYPE, QUALITY_FIELDS
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.json_utils import _to_camel_case

logger = logging.getLogger(__name__)


class EsSearch(object):

    AGGREGATION_NAME = 'compound het'
    CACHED_COUNTS_KEY = 'loaded_variant_counts'

    def __init__(self, families, previous_search_results=None, skip_unaffected_families=False,
                 return_all_queried_families=False):
        from seqr.utils.elasticsearch.utils import get_es_client, InvalidIndexException
        self._client = get_es_client()

        self.samples_by_family_index = defaultdict(lambda: defaultdict(dict))
        samples = Sample.objects.filter(is_active=True, individual__family__in=families)
        for s in samples.select_related('individual__family'):
            self.samples_by_family_index[s.elasticsearch_index][s.individual.family.guid][s.sample_id] = s

        if len(self.samples_by_family_index) < 1:
            raise InvalidIndexException('No es index found')

        self._skipped_sample_count = defaultdict(int)
        if skip_unaffected_families:
            for index, family_samples in list(self.samples_by_family_index.items()):
                index_skipped_families = []
                for family_guid, samples_by_id in family_samples.items():
                    affected_samples = [
                        s for s in samples_by_id.values() if s.individual.affected == Individual.AFFECTED_STATUS_AFFECTED
                    ]
                    if not affected_samples:
                        index_skipped_families.append(family_guid)

                        self._skipped_sample_count[index] += len(samples_by_id) - len(affected_samples)

                for family_guid in index_skipped_families:
                    del self.samples_by_family_index[index][family_guid]

                if not self.samples_by_family_index[index]:
                    del self.samples_by_family_index[index]

            if len(self.samples_by_family_index) < 1:
                raise Exception('Inheritance based search is disabled in families with no affected individuals')

        self._indices = sorted(list(self.samples_by_family_index.keys()), reverse = True)
        self._set_index_metadata()

        if len(self.samples_by_family_index) != len(self.index_metadata):
            raise InvalidIndexException('Could not find expected indices: {}'.format(
                ', '.join(sorted(set(self._indices) - set(self.index_metadata.keys())))
            ))

        self.indices_by_dataset_type = defaultdict(list)
        for index in self._indices:
            dataset_type = self.index_metadata[index].get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS)
            self.indices_by_dataset_type[dataset_type].append(index)

        self.previous_search_results = previous_search_results or {}
        self._return_all_queried_families = return_all_queried_families

        self._search = Search()
        self._index_searches = defaultdict(list)
        self._sort = None
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._filtered_variant_ids = None
        self._no_sample_filters = False
        self._any_affected_sample_filters = False
        self._family_individual_affected_status = {}

    def _set_index_name(self):
        self.index_name = ','.join(sorted(self._indices))
        if len(self.index_name) > MAX_INDEX_NAME_LENGTH:
            alias = hashlib.md5(self.index_name).hexdigest()
            cache_key = 'index_alias__{}'.format(alias)
            if safe_redis_get_json(cache_key) != self.index_name:
                self._client.indices.update_aliases(body={'actions': [
                    {'add': {'indices': self._indices, 'alias': alias}}
                ]})
                safe_redis_set_json(cache_key, self.index_name)
            self.index_name = alias

    def _set_index_metadata(self):
        self._set_index_name()
        from seqr.utils.elasticsearch.utils import get_index_metadata
        self.index_metadata = get_index_metadata(self.index_name, self._client)

    def update_dataset_type(self, dataset_type, keep_previous=False):
        new_indices = self.indices_by_dataset_type[dataset_type]
        if keep_previous:
            indices = set(self._indices)
            indices.update(new_indices)
            self._indices = list(indices)
        else:
            self._indices = new_indices
        self._set_index_name()
        return self

    def sort(self, sort):
        self._sort = _get_sort(sort)
        self._search = self._search.sort(*self._sort)

    def filter(self, new_filter):
        self._search = self._search.filter(new_filter)
        return self

    def filter_by_frequency(self, frequencies):
        q = Q()
        for pop, freqs in frequencies.items():
            if freqs.get('af') is not None:
                filter_field = next(
                    (field_key for field_key in POPULATIONS[pop]['filter_AF']
                     if any(field_key in index_metadata['fields'] for index_metadata in self.index_metadata.values())),
                    POPULATIONS[pop]['AF'])
                q &= _pop_freq_filter(filter_field, freqs['af'])
            elif freqs.get('ac') is not None:
                q &= _pop_freq_filter(POPULATIONS[pop]['AC'], freqs['ac'])

            if freqs.get('hh') is not None:
                q &= _pop_freq_filter(POPULATIONS[pop]['Hom'], freqs['hh'])
                q &= _pop_freq_filter(POPULATIONS[pop]['Hemi'], freqs['hh'])
        self.filter(q)

    def filter_by_annotations(self, annotations, pathogenicity_filter):
        consequences_filter, allowed_consequences = _annotations_filter(annotations or {})
        if allowed_consequences:
            if pathogenicity_filter:
                # Pathogencicity and transcript consequences act as "OR" filters instead of the usual "AND"
                consequences_filter |= pathogenicity_filter
            self.filter(consequences_filter)
            self._allowed_consequences = allowed_consequences
            dataset_type = _dataset_type_for_annotations(annotations)
            if dataset_type:
                self.update_dataset_type(dataset_type)
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
        if not (genes or intervals or rs_ids) and len({genome_version for genome_version in variant_id_genome_versions.items()}) > 1:
            self._filtered_variant_ids = variant_id_genome_versions
        return self

    def filter_by_annotation_and_genotype(self, inheritance, quality_filter=None, annotations=None, annotations_secondary=None, pathogenicity=None):
        has_previous_compound_hets = self.previous_search_results.get('grouped_results')

        inheritance_mode = (inheritance or {}).get('mode')
        inheritance_filter = (inheritance or {}).get('filter') or {}
        if inheritance_filter.get('genotype'):
            inheritance_mode = None

        if quality_filter and quality_filter.get('vcf_filter') is not None:
            self.filter(~Q('exists', field='filters'))

        annotations_secondary_search = None
        secondary_dataset_type = None
        if annotations_secondary:
            annotations_secondary_filter, allowed_consequences_secondary = _annotations_filter(annotations_secondary)
            annotations_filter, _ = _annotations_filter(annotations)
            annotations_secondary_search = self._search.filter(annotations_filter | annotations_secondary_filter)
            self._allowed_consequences_secondary = allowed_consequences_secondary
            secondary_dataset_type = _dataset_type_for_annotations(annotations_secondary)

        pathogenicity_filter = _pathogenicity_filter(pathogenicity or {})
        if annotations or pathogenicity_filter:
            self.filter_by_annotations(annotations, pathogenicity_filter)

        if inheritance_filter or inheritance_mode:
            for index in self._indices:
                family_samples_by_id = self.samples_by_family_index[index]
                affected_status = _get_family_affected_status(family_samples_by_id, inheritance_filter)
                for family_guid in affected_status:
                    if family_guid in self._family_individual_affected_status:
                        self._family_individual_affected_status[family_guid].update(affected_status[family_guid])
                    else:
                        self._family_individual_affected_status[family_guid] = affected_status[family_guid]

        quality_filters_by_family = _quality_filters_by_family(quality_filter, self.samples_by_family_index, self._indices)

        if inheritance_mode in {RECESSIVE, COMPOUND_HET} and not has_previous_compound_hets:
            if secondary_dataset_type:
                self.update_dataset_type(secondary_dataset_type, keep_previous=True)
            self._filter_compound_hets(quality_filters_by_family, annotations_secondary_search)
            if inheritance_mode == COMPOUND_HET:
                return

        self._filter_by_genotype(inheritance_mode, inheritance_filter, quality_filters_by_family)

    def _filter_by_genotype(self, inheritance_mode, inheritance_filter, quality_filters_by_family):
        has_inheritance_filter = inheritance_filter or inheritance_mode
        all_sample_search = (not quality_filters_by_family) and (inheritance_mode == ANY_AFFECTED or not has_inheritance_filter)
        no_filter_indices = set()
        for index in self._indices:
            family_samples_by_id = self.samples_by_family_index[index]
            index_fields = self.index_metadata[index]['fields']

            genotypes_q = None
            if all_sample_search:
                search_sample_count = sum(len(samples) for samples in family_samples_by_id.values()) + self._skipped_sample_count[index]
                index_sample_count = Sample.objects.filter(elasticsearch_index=index, is_active=True).count()
                if search_sample_count == index_sample_count:
                    if inheritance_mode == ANY_AFFECTED:
                        sample_ids = []
                        for family_guid, samples_by_id in family_samples_by_id.items():
                            sample_ids += [
                                sample_id for sample_id, sample in samples_by_id.items()
                                if self._family_individual_affected_status[family_guid][sample.individual.guid] == Individual.AFFECTED_STATUS_AFFECTED]
                        genotypes_q = _any_affected_sample_filter(sample_ids)
                        self._any_affected_sample_filters = True
                    else:
                        # If searching across all families in an index with no inheritance mode we do not need to explicitly
                        # filter on inheritance, as all variants have some inheritance for at least one family
                        self._no_sample_filters = True
                        no_filter_indices.add(index)
                        continue

            if not genotypes_q:
                for family_guid in sorted(family_samples_by_id.keys()):
                    samples_by_id = family_samples_by_id[family_guid]
                    affected_status = self._family_individual_affected_status.get(family_guid)

                    # Filter samples by inheritance
                    if inheritance_mode == ANY_AFFECTED:
                        # Only return variants where at least one of the affected samples has an alt allele
                        sample_ids = [sample_id for sample_id, sample in samples_by_id.items()
                                      if affected_status[sample.individual.guid] == Individual.AFFECTED_STATUS_AFFECTED]
                        family_samples_q = _any_affected_sample_filter(sample_ids)
                    elif has_inheritance_filter:
                        if inheritance_mode:
                            inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

                        if list(inheritance_filter.keys()) == ['affected']:
                            raise Exception('Inheritance must be specified if custom affected status is set')

                        family_samples_q = _family_genotype_inheritance_filter(
                            inheritance_mode, inheritance_filter, samples_by_id, affected_status, index_fields,
                        )

                        # For recessive search, should be hom recessive, x-linked recessive, or compound het
                        if inheritance_mode == RECESSIVE:
                            x_linked_q = _family_genotype_inheritance_filter(
                                X_LINKED_RECESSIVE, inheritance_filter, samples_by_id, affected_status, index_fields,
                            )
                            family_samples_q |= x_linked_q
                    else:
                        # If no inheritance specified only return variants where at least one of the requested samples has an alt allele
                        family_samples_q = _any_affected_sample_filter(list(samples_by_id.keys()))

                    family_samples_q = _named_family_sample_q(family_samples_q, family_guid, quality_filters_by_family)
                    if not genotypes_q:
                        genotypes_q = family_samples_q
                    else:
                        genotypes_q |= family_samples_q

            self._index_searches[index].append(self._search.filter(genotypes_q))

        if no_filter_indices and self._index_searches:
            for index in no_filter_indices:
                self._index_searches[index].append(self._search)

    def _filter_compound_hets(self, quality_filters_by_family, annotations_secondary_search):
        indices = self._indices

        paired_index_families = defaultdict(dict)
        if len(indices) > 1:
            sv_indices = [
                index for index in self.indices_by_dataset_type[Sample.DATASET_TYPE_SV_CALLS] if index in indices
            ]
            variant_indices = [
                index for index in self.indices_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS] if index in indices
            ]
            if sv_indices and variant_indices:
                for sv_index in sv_indices:
                    sv_families = set(self.samples_by_family_index[sv_index].keys())
                    for var_index in variant_indices:
                        overlapping_families = sv_families & set(self.samples_by_family_index[var_index].keys())
                        if overlapping_families:
                            paired_index_families[sv_index].update({var_index: overlapping_families})
                            paired_index_families[var_index].update({sv_index: overlapping_families})

        seen_paired_indices = set()
        comp_het_q_by_index = {}
        for index in indices:
            family_samples_by_id = self.samples_by_family_index[index]
            index_fields = self.index_metadata[index]['fields']
            seen_paired_indices.add(index)

            paired_families = {}
            for pair_index, families in paired_index_families[index].items():
                paired_families.update({family: pair_index for family in families})

            for family_guid in sorted(family_samples_by_id.keys()):
                paired_index = paired_families.get(family_guid)
                if paired_index and paired_index in seen_paired_indices:
                    continue

                samples_by_id = family_samples_by_id[family_guid]

                affected_status = self._family_individual_affected_status[family_guid]
                family_samples_q = _family_genotype_inheritance_filter(
                    COMPOUND_HET, INHERITANCE_FILTERS[COMPOUND_HET], samples_by_id, affected_status, index_fields,
                )

                if paired_index:
                    pair_index_fields = self.index_metadata[paired_index]['fields']
                    pair_samples_by_id = self.samples_by_family_index[paired_index][family_guid]
                    family_samples_q |= _family_genotype_inheritance_filter(
                        COMPOUND_HET, INHERITANCE_FILTERS[COMPOUND_HET], pair_samples_by_id, affected_status,
                        pair_index_fields,
                    )
                    index = ','.join(sorted([index, paired_index]))

                samples_q = _named_family_sample_q(family_samples_q, family_guid, quality_filters_by_family)

                index_comp_het_q = comp_het_q_by_index.get(index)
                if not index_comp_het_q:
                    comp_het_q_by_index[index] = samples_q
                else:
                    comp_het_q_by_index[index] |= samples_q

        for index, compound_het_q in comp_het_q_by_index.items():
            compound_het_search = (annotations_secondary_search or self._search).filter(compound_het_q)
            compound_het_search.aggs.bucket(
                'genes', 'terms', field='geneIds', min_doc_count=2, size=MAX_COMPOUND_HET_GENES + 1
            ).metric(
                'vars_by_gene', 'top_hits', size=100, sort=self._sort, _source=QUERY_FIELD_NAMES
            )
            self._index_searches[index].append(compound_het_search)

    def search(self,  **kwargs):
        indices = self._indices

        logger.info('Searching in elasticsearch indices: {}'.format(', '.join(indices)))

        is_single_search, search_kwargs = self._should_execute_single_search(**kwargs)

        if is_single_search:
            return self._execute_single_search(**search_kwargs)
        elif not self._index_searches:
            return self._execute_single_search(**search_kwargs)
        else:
            return self._execute_multi_search(**search_kwargs)

    def _is_single_search(self):
        return len(self._indices) == 1 and len(self._index_searches) < 2 and \
               len(self._index_searches.get(self._indices[0], [])) <= 1

    def _should_execute_single_search(self, page=1, num_results=100):
        is_single_search = self._is_single_search()
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

    def _execute_single_search(self, page=1, num_results=100, start_index=None, deduplicate=False, **kwargs):
        num_results_for_search = num_results * len(self._indices) if deduplicate else num_results
        if num_results_for_search > MAX_VARIANTS and deduplicate:
            num_results_for_search = MAX_VARIANTS
        search = self._get_paginated_searches(
            self.index_name, page=page, num_results=num_results_for_search, start_index=start_index
        )[0]
        response = self._execute_search(search)
        parsed_response = self._parse_response(response)
        return self._process_single_search_response(
            parsed_response, page=page, num_results=num_results, deduplicate=deduplicate, **kwargs)

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
        indices = sorted(list(self._index_searches.keys()) or self._indices, reverse = True)

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
            ms = ms.index(index_name.split(','))
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
            family_guids = list(index_family_samples.keys())
        else:
            # Searches for all inheritance and all families do not filter on inheritance so there are no matched_queries
            alt_allele_samples = set()
            for alt_samples_field in HAS_ALT_FIELD_KEYS:
                if alt_samples_field in hit:
                    alt_allele_samples.update(hit[alt_samples_field])

            if self._any_affected_sample_filters:
                # If using the any inheritance filter only include matched families
                def _is_matched_sample(family_guid, sample):
                    return self._family_individual_affected_status[family_guid][sample.individual.guid] == \
                           Individual.AFFECTED_STATUS_AFFECTED
            else:
                _is_matched_sample = lambda *args: True

            family_guids = [family_guid for family_guid, samples_by_id in index_family_samples.items()
                            if any(sample_id in alt_allele_samples and _is_matched_sample(family_guid, sample)
                                   for sample_id, sample in samples_by_id.items())]

        genotypes = {}
        is_sv = raw_hit.meta.doc_type == SV_DOC_TYPE
        for family_guid in family_guids:
            samples_by_id = index_family_samples[family_guid]
            genotypes.update({
                samples_by_id[genotype_hit['sample_id']].individual.guid: _get_field_values(genotype_hit, GENOTYPE_FIELDS_CONFIG)
                for genotype_hit in hit[GENOTYPES_FIELD_KEY] if genotype_hit['sample_id'] in samples_by_id
            })
            if len(samples_by_id) != len(genotypes) and is_sv:
                # Family members with no variants are not included in the SV index
                for sample_id, sample in samples_by_id.items():
                    if sample.individual.guid not in genotypes:
                        genotypes[sample.individual.guid] = _get_field_values(
                            {'sample_id': sample_id}, GENOTYPE_FIELDS_CONFIG)
                        genotypes[sample.individual.guid]['isRef'] = True
                        if hit['contig'] == 'X' and sample.individual.sex == Individual.SEX_MALE:
                            genotypes[sample.individual.guid]['cn'] = 1

        # If an SV has genotype-specific coordinates that differ from the main coordinates, use those
        if is_sv and all((gen.get('isRef') or gen.get('start') or gen.get('end')) for gen in genotypes.values()):
            start = min([gen.get('start') or hit['start'] for gen in genotypes.values() if not gen.get('isRef')])
            end = max([gen.get('end') or hit['end'] for gen in genotypes.values() if not gen.get('isRef')])
            num_exon = max([gen.get('numExon') or hit['num_exon'] for gen in genotypes.values() if not gen.get('isRef')])
            if start != hit['start']:
                hit['start'] = start
                hit['xpos'] = get_xpos(hit['contig'], start)
            if end != hit['end']:
                hit['end'] = end
            if num_exon != hit['num_exon']:
                hit['num_exon'] = num_exon
            for gen in genotypes.values():
                if gen.get('start') == start and gen.get('end') == end:
                    gen['start'] = None
                    gen['end'] = None

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
                get_addl_fields=lambda field: pop_config[field] if isinstance(pop_config[field], list) else [pop_config[field]],
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
        main_transcript_id = sorted_transcripts[0]['transcriptId'] \
            if len(sorted_transcripts) and 'transcriptRank' in sorted_transcripts[0] else None

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
            'mainTranscriptId': main_transcript_id,
            'populations': populations,
            'predictions': _get_field_values(
                hit, PREDICTION_FIELDS_CONFIG, format_response_key=lambda key: key.split('_')[1].lower()
            ),
            'transcripts': dict(transcripts),
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
                for variant in gene_variants:
                    variant['gene_consequences'] = {
                        k: [variant['svType']] if variant.get('svType') else [
                            transcript['majorConsequence'] for transcript in transcripts
                        ] for k, transcripts in variant['transcripts'].items()}

                gene_variants = [variant for variant in gene_variants if any(
                    consequence in self._allowed_consequences + (self._allowed_consequences_secondary or [])
                    for consequence in variant['gene_consequences'].get(gene_id, [])
                )]

            if len(gene_variants) < 2:
                continue

            # Do not include groups multiple times if identical variants are in the same multiple genes
            if any((not variant['mainTranscriptId']) or all(t['transcriptId'] != variant['mainTranscriptId']
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
                    variant.pop('gene_consequences', None)
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
            if variant['mainTranscriptId']:
                for gene, transcripts in variant['transcripts'].items():
                    if any(t['transcriptId'] == variant['mainTranscriptId'] for t in transcripts):
                        primary_genes.add(gene)
                        break
        if len(primary_genes) == 1:
            is_valid_gene = True
            primary_gene = primary_genes.pop()
            if self._allowed_consequences:
                is_valid_gene = all(any(
                    consequence in self._allowed_consequences for consequence in
                    variant['gene_consequences'].get(primary_gene, [])
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
            unaffected_genotypes = [
                [variant['genotypes'].get(individual_guid, {'isRef': True}) for variant in variants]
                for individual_guid in family_unaffected_individual_guids.get(family_guid, [])
            ]

            gene_consequences = [
                variant['gene_consequences'].get(gene_id, []) for variant in variants
            ]

            def _is_valid_compound_het_pair(variant_1_index, variant_2_index):
                # To be compound het all unaffected individuals need to be hom ref for at least one of the variants
                for genotype in unaffected_genotypes:
                    is_valid_for_individual = any(
                        genotype[variant_index].get('numAlt') == 0 or genotype[variant_index].get('isRef')
                        for variant_index in [variant_1_index, variant_2_index]
                    )
                    if not is_valid_for_individual:
                        return False
                if self._allowed_consequences and self._allowed_consequences_secondary:
                    consequences = gene_consequences[variant_1_index] + gene_consequences[variant_2_index]
                    if all(consequence not in self._allowed_consequences for consequence in consequences) or all(
                            consequence not in self._allowed_consequences_secondary for consequence in consequences):
                        return False
                return True

            valid_combinations = [[ch_1_index, ch_2_index] for ch_1_index, ch_2_index in
                                  combinations(range(len(variants)), 2)
                                  if _is_valid_compound_het_pair(ch_1_index, ch_2_index)]

            family_compound_het_pairs[family_guid] = [
                [variants[valid_ch_1_index], variants[valid_ch_2_index]] for
                valid_ch_1_index, valid_ch_2_index in valid_combinations]

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
            gene = next(iter(gene_compound_het_pair))
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
                    _update_existing_variant(existing_compound_het_pair[0], compound_het_pair[0])
                    _update_existing_variant(existing_compound_het_pair[1], compound_het_pair[1])
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

        # Get requested page of variants
        merged_variant_results = []
        num_compound_hets = 0
        num_single_variants = 0
        for variants_group in grouped_variants:
            variants = next(iter(variants_group.values()))

            self.previous_search_results['grouped_results'].append(variants_group)
            if len(variants) > 1:
                merged_variant_results.append(variants)
                num_compound_hets += 1
            else:
                merged_variant_results += variants
                num_single_variants += 1
            if len(merged_variant_results) >= num_results:
                break

        self.previous_search_results['compound_het_results'] = compound_het_results[num_compound_hets:]
        self.previous_search_results['variant_results'] = variant_results[num_single_variants:]
        return merged_variant_results

    def _get_paginated_searches(self, index_name, page=1, num_results=100, start_index=None):
        searches = []
        for search in self._index_searches.get(index_name, [self._search]):
            search = search.index(index_name.split(','))

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


def _get_family_affected_status(family_samples_by_id, inheritance_filter):
    individual_affected_status = inheritance_filter.get('affected') or {}
    affected_status = {}
    for family_guid, samples_by_id in family_samples_by_id.items():
        affected_status[family_guid] = {}
        for sample in samples_by_id.values():
            indiv = sample.individual
            affected_status[family_guid][indiv.guid] = individual_affected_status.get(indiv.guid) or indiv.affected

    return affected_status


def _quality_filters_by_family(quality_filter, samples_by_family_index, indices):
    quality_field_configs = {
        'min_{}'.format(field): {'field': field, 'step': step} for field, step in QUALITY_FIELDS.items()
    }
    quality_filter = dict({field: 0 for field in quality_field_configs.keys()}, **(quality_filter or {}))
    for field, config in quality_field_configs.items():
        if quality_filter[field] % config['step'] != 0:
            raise Exception('Invalid {} filter {}'.format(config['field'], quality_filter[field]))

    quality_filters_by_family = {}
    if any(quality_filter[field] for field in quality_field_configs.keys()):
        for index in indices:
            family_samples_by_id = samples_by_family_index[index]
            for family_guid, samples_by_id in family_samples_by_id.items():
                quality_q = Q()
                for sample_id in samples_by_id.keys():
                    for field, config in quality_field_configs.items():
                        if quality_filter[field]:
                            q = _build_or_filter('term', [
                                {'samples_{}_{}_to_{}'.format(config['field'], i, i + config['step']): sample_id}
                                for i in range(0, quality_filter[field], config['step'])
                            ])
                            if field == 'min_ab':
                                #  AB only relevant for hets
                                quality_q &= ~Q(q) | ~Q('term', samples_num_alt_1=sample_id)
                            else:
                                quality_q &= ~Q(q)
                quality_filters_by_family[family_guid] = quality_q
    return quality_filters_by_family


def _any_affected_sample_filter(sample_ids):
    sample_ids = sorted(sample_ids)
    return Q('terms', samples_num_alt_1=sample_ids) | Q('terms', samples_num_alt_2=sample_ids) | Q('terms', samples=sample_ids)


def _family_genotype_inheritance_filter(inheritance_mode, inheritance_filter, samples_by_id, individual_affected_status, index_fields):
    samples_q = None

    individuals = [sample.individual for sample in samples_by_id.values()]

    individual_genotype_filter = inheritance_filter.get('genotype') or {}

    if inheritance_mode == X_LINKED_RECESSIVE:
        samples_q = Q('match', contig='X')
        for individual in individuals:
            if individual_affected_status[individual.guid] == Individual.AFFECTED_STATUS_UNAFFECTED \
                    and individual.sex == Individual.SEX_MALE:
                individual_genotype_filter[individual.guid] = REF_REF

    is_sv_comp_het = inheritance_mode == COMPOUND_HET and 'samples' in index_fields
    for sample_id, sample in samples_by_id.items():

        individual_guid = sample.individual.guid
        affected = individual_affected_status[individual_guid]

        genotype = individual_genotype_filter.get(individual_guid) or inheritance_filter.get(affected)

        if genotype:
            if is_sv_comp_het and affected == Individual.AFFECTED_STATUS_UNAFFECTED:
                # Unaffected individuals for SV compound het search can have any genotype so are not included
                continue

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

    return samples_q


def _named_family_sample_q(family_samples_q, family_guid, quality_filters_by_family):
    sample_queries = [family_samples_q]
    quality_q = quality_filters_by_family.get(family_guid)
    if quality_q:
        sample_queries.append(quality_q)

    return Q('bool', must=sample_queries, _name=family_guid)


def _location_filter(genes, intervals, rs_ids, variant_ids, location_filter):
    q = None
    if intervals:
        interval_xpos_range = [
            (get_xpos(interval['chrom'], interval['start']), get_xpos(interval['chrom'], interval['end']))
            for interval in intervals
        ]
        range_filters = []
        for key in ['xpos', 'xstop']:
            range_filters += [{
                key: {
                    'gte': xstart,
                    'lte': xstop,
                }
            } for (xstart, xstop) in interval_xpos_range]
        q = _build_or_filter('range', range_filters)
        for (xstart, xstop) in interval_xpos_range:
            q |= Q('range', xpos={'lte': xstart}) & Q('range', xstop={'gte': xstop})

    filters = [
        {'geneIds': list((genes or {}).keys())},
        {'rsid': rs_ids},
        {'variantId': variant_ids},
    ]
    filters = [f for f in filters if next(iter(f.values()))]
    if filters:
        location_q = _build_or_filter('terms', filters)
        if q:
            q |= location_q
        else:
            q = location_q

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
        pathogenicity_filter = Q('terms', clinvar_clinical_significance=sorted(list(clinvar_clinical_significance_terms)))

    if hgmd_filters:
        hgmd_class = set()
        for hgmd_filter in hgmd_filters:
            hgmd_class.update(HGMD_CLASS_MAP.get(hgmd_filter, []))

        hgmd_q = Q('terms', hgmd_class=sorted(list(hgmd_class)))
        pathogenicity_filter = pathogenicity_filter | hgmd_q if pathogenicity_filter else hgmd_q

    return pathogenicity_filter


def _annotations_filter(annotations):
    vep_consequences = sorted([ann for anns in annotations.values() for ann in anns])

    consequences_filter = Q('terms', transcriptConsequenceTerms=vep_consequences)

    if 'intergenic_variant' in vep_consequences:
        # VEP doesn't add annotations for many intergenic variants so match variants where no transcriptConsequenceTerms
        consequences_filter |= ~Q('exists', field='transcriptConsequenceTerms')

    return consequences_filter, vep_consequences


def _dataset_type_for_annotations(annotations):
    sv = bool(annotations.get('structural'))
    non_sv = any(v for k, v in annotations.items() if k != 'structural')
    if sv and not non_sv:
        return Sample.DATASET_TYPE_SV_CALLS
    elif not sv and non_sv:
        return Sample.DATASET_TYPE_VARIANT_CALLS
    return None


def _pop_freq_filter(filter_key, value):
    return Q('range', **{filter_key: {'lte': value}}) | ~Q('exists', field=filter_key)


def _build_or_filter(op, filters):
    q = Q(op, **filters[0])
    for filter_kwargs in filters[1:]:
        q |= Q(op, **filter_kwargs)
    return q


def _get_sort(sort_key):
    sorts = SORT_FIELDS.get(sort_key, [])

    # Add parameters to scripts
    if len(sorts) and isinstance(sorts[0], dict) and sorts[0].get('_script', {}).get('script', {}).get('params'):
        for key, val_func in sorts[0]['_script']['script']['params'].items():
            if callable(val_func):
                sorts[0]['_script']['script']['params'][key] = val_func()

    if XPOS_SORT_KEY not in sorts:
        sorts.append(XPOS_SORT_KEY)
    return sorts


def _sort_compound_hets(grouped_variants):
    return sorted(grouped_variants, key=lambda variants: next(iter(variants.values()))[0]['_sort'])


def _get_compound_het_page(grouped_variants, start_index, end_index):
    skipped = 0
    variant_results = []
    variant_count = 0
    for variants in grouped_variants:
        curr_variant = next(iter(variants.values()))
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
    if sort in {'Infinity', '-Infinity'}:
        # ES returns these values for sort when a sort field is missing, using the correct value for the given direction
        sort = maxsize
    elif hasattr(sort_config, 'values') and any(cfg.get('order') == 'desc' for cfg in sort_config.values()):
        sort = sort * -1

    return sort


def _get_field_values(hit, field_configs, format_response_key=_to_camel_case, get_addl_fields=None, lookup_field_prefix='', existing_fields=None):
    return {
        field_config.get('response_key', format_response_key(field)): _value_if_has_key(
            hit,
            (get_addl_fields(field) if get_addl_fields else []) +
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