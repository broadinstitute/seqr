from collections import defaultdict
from copy import deepcopy
import elasticsearch
from elasticsearch_dsl import Search, Q, MultiSearch
import hashlib
import json
from sys import maxsize
from itertools import combinations

from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual
from seqr.utils.search.constants import XPOS_SORT_KEY, COMPOUND_HET, RECESSIVE, NEW_SV_FIELD, ALL_DATA_TYPES, X_LINKED_RECESSIVE, MAX_VARIANTS, \
    INHERITANCE_FILTERS, REF_REF, ANY_AFFECTED, AFFECTED, UNAFFECTED, HAS_ALT
from seqr.utils.search.elasticsearch.constants import \
    HAS_ALT_FIELD_KEYS, GENOTYPES_FIELD_KEY, POPULATION_RESPONSE_FIELD_CONFIGS, POPULATIONS, \
    SORTED_TRANSCRIPTS_FIELD_KEY, CORE_FIELDS_CONFIG, NESTED_FIELDS, PREDICTION_FIELDS_RESPONSE_CONFIG, \
    QUERY_FIELD_NAMES, GENOTYPE_QUERY_MAP, HGMD_CLASS_MAP, \
    SORT_FIELDS, MAX_COMPOUND_HET_GENES, MAX_INDEX_NAME_LENGTH, QUALITY_QUERY_FIELDS, \
    GRCH38_LOCUS_FIELD, MAX_SEARCH_CLAUSES, SV_SAMPLE_OVERRIDE_FIELD_CONFIGS, \
    PREDICTION_FIELD_LOOKUP, MULTI_FIELD_PREDICTORS, SPLICE_AI_FIELD, CLINVAR_KEY, HGMD_KEY, CLINVAR_PATH_SIGNIFICANCES, \
    PATH_FREQ_OVERRIDE_CUTOFF, CANONICAL_TRANSCRIPT_FILTER, \
    get_prediction_response_key, XSTOP_FIELD, GENOTYPE_FIELDS, SCREEN_KEY, MAX_INDEX_SEARCHES, PREFILTER_SEARCH_SIZE
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.xpos_utils import get_xpos, MIN_POS, MAX_POS, get_chrom_pos
from seqr.views.utils.json_utils import _to_camel_case

logger = SeqrLogger(__name__)

class EsSearch(object):

    AGGREGATION_NAME = 'compound het'
    CACHED_COUNTS_KEY = 'loaded_variant_counts'

    def __init__(self, samples, genome_version, previous_search_results=None, return_all_queried_families=False, user=None, sort=None, skipped_samples=None):
        from seqr.utils.search.utils import InvalidSearchException
        from seqr.utils.search.elasticsearch.es_utils import get_es_client, InvalidIndexException
        self._client = get_es_client()

        self.samples_by_family_index = defaultdict(lambda: defaultdict(dict))
        for s in samples.select_related('individual__family'):
            self.samples_by_family_index[s.elasticsearch_index][s.individual.family.guid][s.sample_id] = s

        self._set_indices(sorted(list(self.samples_by_family_index.keys())))
        self._set_index_metadata()

        invalid_genome_indices = [
            f"{index} ({meta['genomeVersion']})" for index, meta in self.index_metadata.items()
            if meta['genomeVersion'] != genome_version
        ]
        self._genome_version = genome_version
        self._skipped_samples = skipped_samples

        self.indices_by_dataset_type = defaultdict(list)
        for index in self._indices:
            dataset_type = self._get_index_dataset_type(index)
            self.indices_by_dataset_type[dataset_type].append(index)

        self.previous_search_results = {} if previous_search_results is None else previous_search_results
        self._return_all_queried_families = return_all_queried_families
        self._user = user

        self._search = Search()
        self._index_searches = defaultdict(list)
        self._family_individual_affected_status = {}
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._consequence_overrides = {}
        self._filtered_gene_ids = None
        self._paired_index_comp_het = False
        self._no_sample_filters = False
        self._any_affected_sample_filters = False

        self._sort = deepcopy(SORT_FIELDS.get(sort, [])) if sort else None
        if self._sort:
            self._sort_variants(samples)

    @staticmethod
    def _parse_xstop(result):
        xstop = result.pop(XSTOP_FIELD, None)

    def _get_index_dataset_type(self, index):
        return self.get_index_metadata_dataset_type(self.index_metadata[index])

    @staticmethod
    def get_index_metadata_dataset_type(index_metadata):
        data_type = index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS)
        return data_type

    def _set_indices(self, indices):
        self._indices = indices
        self._set_index_name()

    def _set_index_name(self):
        self.index_name = ','.join(sorted(self._indices))

    def _set_index_metadata(self):
        from seqr.utils.search.elasticsearch.es_utils import get_index_metadata
        self.index_metadata = get_index_metadata(self.index_name, self._client, include_fields=True)

    def _sort_variants(self, sample_data):
        main_sort_dict = self._sort[0] if len(self._sort) and isinstance(self._sort[0], dict) else None

        # always final sort on variant ID to keep different variants at the same position grouped properly
        if 'variantId' not in self._sort:
            self._sort.append('variantId')

        self._search = self._search.sort(*self._sort)

    def _filter(self, new_filter):
        self._search = self._search.filter(new_filter)
        return self

    def filter_by_variant_ids(self, variant_ids):
        self._filter(Q('terms', variantId=variant_ids))
        return self

    def search(self, page=1, num_results=100):
        indices = self._indices

        logger.info('Searching in elasticsearch indices: {}'.format(', '.join(indices)), self._user)

        is_single_search, search_kwargs = self._should_execute_single_search(page=page, num_results=num_results)

        if is_single_search:
            return self._execute_single_search(**search_kwargs)

    def _is_single_search(self):
        return len(self._indices) == 1 and len(self._index_searches) < 2 and \
               len(self._index_searches.get(self._indices[0], [])) <= 1

    def _should_execute_single_search(self, page=1, num_results=100):
        is_single_search = self._is_single_search()
        num_loaded = len(self.previous_search_results.get('all_results', []))

        if is_single_search and not self.previous_search_results.get('grouped_results'):
            start_index = None
        elif not self._index_searches:
            # If doing all project-families all inheritance search, do it as a single query
            # Load all variants, do not skip pages
            num_loaded += self.previous_search_results.get('duplicate_doc_count', 0)
            if num_loaded >= (page - 1) * num_results:
                start_index = num_loaded
            else:
                start_index = 0
            return True, {'page': page, 'num_results': num_results, 'start_index': start_index, 'deduplicate': True}

    def _execute_single_search(self, page=1, num_results=100, start_index=None, deduplicate=False, **kwargs):
        num_results_for_search = num_results * len(self._indices) if deduplicate else num_results
        searches, log_messages = self._get_paginated_searches(
            self.index_name, page=page, num_results=num_results_for_search, start_index=start_index
        )
        logger.info(log_messages[0], self._user)
        search = searches[0]
        response = self._execute_search(search)
        parsed_response = self._parse_response(response)
        return self._process_single_search_response(
            parsed_response, page=page, num_results=num_results, deduplicate=deduplicate, **kwargs)

    def _process_single_search_response(self, parsed_response, page=1, num_results=100, deduplicate=False, **kwargs):
        variant_results, total_results, is_compound_het, _ = parsed_response
        self.previous_search_results['total_results'] = total_results

        results_start_index = (page - 1) * num_results

        if deduplicate:
            variant_results = self._deduplicate_results(variant_results)

        # Only save contiguous pages of results:
        previous_all_results = self.previous_search_results.get('all_results', [])
        if len(previous_all_results) >= results_start_index:
            self.previous_search_results['all_results'] = self.previous_search_results.get('all_results', []) + variant_results
            variant_results = self.previous_search_results['all_results'][results_start_index:]

        return variant_results[:num_results]

    def _parse_response(self, response):
        index_name = response.hits[0].meta.index if response.hits else None

        response_total = response.hits.total['value']
        logger.info('Total hits: {} ({} seconds)'.format(response_total, response.took / 1000.0), self._user)
        return [self._parse_hit(hit) for hit in response], response_total, False, index_name

    def _parse_hit(self, raw_hit):
        hit = {k: raw_hit[k] for k in QUERY_FIELD_NAMES if k in raw_hit}
        index_name = raw_hit.meta.index
        index_family_samples = self.samples_by_family_index[index_name]
        data_type = self._get_index_dataset_type(index_name)

        family_guids, genotypes = self._parse_genotypes(raw_hit, hit, index_family_samples, data_type)

        result = _get_field_values(hit, CORE_FIELDS_CONFIG, format_response_key=str)
        result.update({
            field_name: _get_field_values(hit, fields, lookup_field_prefix=field_name)
            for field_name, fields in NESTED_FIELDS.items()
        })
        if hasattr(raw_hit.meta, 'sort'):
            result['_sort'] = [_parse_es_sort(sort, self._sort[i]) for i, sort in enumerate(raw_hit.meta.sort)]

        result['genomeVersion'] = self._genome_version
        self._parse_xstop(result)
        result[CLINVAR_KEY]['version'] = self.index_metadata[index_name].get('clinvar_version')

        populations = {
            population: _get_field_values(
                hit, POPULATION_RESPONSE_FIELD_CONFIGS, format_response_key=lambda key: key.lower(),
                lookup_field_prefix=population,
                existing_fields=self.index_metadata[index_name]['fields'],
                get_addl_fields=lambda field: pop_config[field] if isinstance(pop_config[field], list) else [pop_config[field]],
                skip_fields=[field for field, val in pop_config.items() if val is None],
            )
            for population, pop_config in POPULATIONS.items()
        }

        sorted_transcripts = [
            {_to_camel_case(k): v for k, v in transcript.to_dict().items()}
            for transcript in hit[SORTED_TRANSCRIPTS_FIELD_KEY] or []
        ]

        transcripts = defaultdict(list)
        for transcript in sorted_transcripts:
            if transcript['geneId']:
                transcripts[transcript['geneId']].append(transcript)
        gene_ids = result.pop('geneIds', None)
        main_transcript_id, selected_main_transcript_id = self._get_main_transcript(sorted_transcripts)

        result.update({
            'familyGuids': sorted(family_guids),
            'genotypes': genotypes,
            'mainTranscriptId': main_transcript_id,
            'selectedMainTranscriptId': selected_main_transcript_id,
            'populations': populations,
            'predictions': _get_field_values(
                hit, PREDICTION_FIELDS_RESPONSE_CONFIG, format_response_key=get_prediction_response_key,
                get_addl_fields=lambda field: MULTI_FIELD_PREDICTORS.get(field, [])
            ),
            'transcripts': dict(transcripts),
        })
        return result

    def _parse_genotypes(self, raw_hit, hit, index_family_samples, data_type):
        if hasattr(raw_hit.meta, 'matched_queries'):
            family_guids = list(raw_hit.meta.matched_queries)
        else:
            # Searches for all inheritance and all families do not filter on inheritance so there are no matched_queries
            alt_allele_samples = set()
            for alt_samples_field in HAS_ALT_FIELD_KEYS:
                if alt_samples_field in hit:
                    alt_allele_samples.update(hit[alt_samples_field])

            if self._any_affected_sample_filters:
                pass
            else:
                _is_matched_sample = lambda *args: True

            family_guids = [family_guid for family_guid, samples_by_id in index_family_samples.items()
                if any(sample_id in alt_allele_samples and _is_matched_sample(family_guid, sample)
                       for sample_id, sample in samples_by_id.items())]

        genotypes = {}
        genotype_fields_config = GENOTYPE_FIELDS[data_type]
        for family_guid in family_guids:
            samples_by_id = index_family_samples[family_guid]
            for genotype_hit in hit[GENOTYPES_FIELD_KEY]:
                sample = samples_by_id.get(genotype_hit['sample_id'])
                if sample:
                    genotype_hit['sample_type'] = sample.sample_type
                    genotypes[sample.individual.guid] = _get_field_values(genotype_hit, genotype_fields_config)

        return family_guids, genotypes

    def _get_main_transcript(self, sorted_transcripts):
        main_transcript_id = sorted_transcripts[0]['transcriptId'] \
            if len(sorted_transcripts) and 'transcriptRank' in sorted_transcripts[0] else None

        selected_main_transcript_id = None

        return main_transcript_id, selected_main_transcript_id

    def _deduplicate_results(self, sorted_new_results):
        original_result_count = len(sorted_new_results)
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

    def _get_paginated_searches(self, index_name, page=1, num_results=100, start_index=None):
        searches = []
        log_messages = []
        for search in self._index_searches.get(index_name, [self._search]):
            search = search.index(index_name.split(','))

            if search.aggs.to_dict():
                # For compound het search get results from aggregation instead of top level hits
                search = search[:1]
                log_messages.append('Loading {}s for {}'.format(self.AGGREGATION_NAME, index_name))
            else:
                end_index = page * num_results

                search = search[start_index:end_index]
                search = search.source(QUERY_FIELD_NAMES)
                log_messages.append('Loading {} records {}-{}'.format(index_name, start_index, end_index))

            searches.append(search)
        return searches, log_messages

    def _execute_search(self, search):
        logger.debug(json.dumps(search.to_dict(), indent=2), self._user)
        try:
            return search.using(self._client).execute()
        except elasticsearch.exceptions.ConnectionTimeout as e:
            raise e


def _get_family_affected_status(samples_by_id, inheritance_filter):
    individual_affected_status = inheritance_filter.get('affected') or {}
    affected_status = {}
    for sample in samples_by_id.values():
        indiv = sample.individual
        affected_status[indiv.guid] = individual_affected_status.get(indiv.guid) or indiv.affected

    return affected_status


VUS_FILTER = 'vus_or_conflicting'
VUS_REGEX = 'Conflicting_interpretations_of_pathogenicity.*|~((.*[Bb]enign.*)|(.*[Pp]athogenic.*))'


def _parse_es_sort(sort, sort_config):
    if sort in {'Infinity', '-Infinity', None}:
        # ES returns these values for sort when a sort field is missing, using the correct value for the given direction
        sort = maxsize
    elif hasattr(sort_config, 'values') and any(cfg.get('order') == 'desc' for cfg in sort_config.values()):
        sort = float(sort) * -1

    return sort


def _get_field_values(hit, field_configs, format_response_key=_to_camel_case, get_addl_fields=None, lookup_field_prefix='', existing_fields=None, skip_fields=None):
    return {
        field_config.get('response_key') or format_response_key(field): _value_if_has_key(
            hit,
            (get_addl_fields(field) if get_addl_fields else []) +
            ['{}_{}'.format(lookup_field_prefix, field) if lookup_field_prefix else field],
            existing_fields=existing_fields,
            **field_config
        ) if field not in (skip_fields or []) else None
        for field, field_config in field_configs.items()
    }


def _value_if_has_key(hit, keys, format_value=None, default_value=None, existing_fields=None, **kwargs):
    for key in keys:
        if key in hit:
            return format_value(default_value if hit[key] is None else hit[key]) if format_value else hit[key]
    return default_value if not existing_fields or any(key in existing_fields for key in keys) else None
