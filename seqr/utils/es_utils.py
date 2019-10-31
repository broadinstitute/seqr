from collections import defaultdict
from copy import deepcopy
import elasticsearch
from elasticsearch_dsl import Search, Q, MultiSearch
import hashlib
import json
import logging
from pyliftover.liftover import LiftOver
from sys import maxint
import redis

import settings
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37, Omim, GeneConstraint
from seqr.models import Sample, Individual
from seqr.utils.xpos_utils import get_xpos, get_chrom_pos
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.views.utils.json_utils import _to_camel_case

logger = logging.getLogger(__name__)


VARIANT_DOC_TYPE = 'variant'
MAX_VARIANTS = 10000
MAX_COMPOUND_HET_GENES = 1000
MAX_INDEX_NAME_LENGTH = 7500

XPOS_SORT_KEY = 'xpos'


def get_es_client(timeout=30):
    return elasticsearch.Elasticsearch(host=settings.ELASTICSEARCH_SERVICE_HOSTNAME, timeout=timeout, retry_on_timeout=True)


def get_index_metadata(index_name, client):
    try:
        mappings = client.indices.get_mapping(index=index_name, doc_type=[VARIANT_DOC_TYPE])
    except Exception as e:
        raise InvalidIndexException('Error accessing index "{}": {}'.format(
            index_name, e.error if hasattr(e, 'error') else e.message))
    index_metadata = {}
    for index_name, mapping in mappings.items():
        variant_mapping = mapping['mappings'].get(VARIANT_DOC_TYPE, {})
        # TODO remove this check once all projects are migrated
        if not variant_mapping['properties'].get('samples_num_alt_1'):
            raise InvalidIndexException('Index "{}" does not have a valid schema'.format(index_name))
        index_metadata[index_name] = variant_mapping.get('_meta', {})
        index_metadata[index_name]['fields'] = variant_mapping['properties'].keys()
    return index_metadata


def get_single_es_variant(families, variant_id, return_all_queried_families=False):
    variants = EsSearch(
        families, return_all_queried_families=return_all_queried_families
    ).filter(_single_variant_id_filter(variant_id)).search(num_results=1)
    if not variants:
        raise Exception('Variant {} not found'.format(variant_id))
    return variants[0]


def get_es_variants_for_variant_tuples(families, xpos_ref_alt_tuples):
    variant_id_filter = _variant_id_filter(xpos_ref_alt_tuples)
    variants = EsSearch(families).filter(variant_id_filter).search(num_results=len(xpos_ref_alt_tuples))
    return variants


def get_es_variants(search_model, sort=XPOS_SORT_KEY, page=1, num_results=100, load_all=False):

    def process_previous_results(previous_search_results):
        num_results_to_use = num_results
        total_results = previous_search_results.get('total_results')
        if load_all:
            num_results_to_use = total_results or 10000
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

    return _get_es_variants_for_search(search_model, EsSearch, process_previous_results, sort=sort)


def get_es_variant_gene_counts(search_model):

    def process_previous_results(previous_search_results):
        if previous_search_results.get('gene_aggs'):
            return previous_search_results['gene_aggs'], {}

        total_results = previous_search_results.get('total_results')
        if total_results is not None:
            gene_aggs = defaultdict(lambda: {'total': 0, 'families': defaultdict(int)})
            if 'all_results' in previous_search_results:
                if len(previous_search_results['all_results']) == total_results:
                    for var in previous_search_results['all_results']:
                        gene_id = next((
                            gene_id for gene_id, transcripts in var['transcripts'].items()
                            if any(t['transcriptId'] == var['mainTranscriptId'] for t in transcripts)
                        ), None) if var['mainTranscriptId'] else None
                        if gene_id:
                            gene_aggs[gene_id]['total'] += 1
                            for family_guid in var['familyGuids']:
                                gene_aggs[gene_id]['families'][family_guid] += 1
                    return gene_aggs, {}
            elif 'grouped_results' in previous_search_results:
                loaded = sum(counts.get('loaded', 0) for counts in previous_search_results.get('loaded_variant_counts', {}).values())
                if loaded == total_results:
                    for group in previous_search_results['grouped_results']:
                        variants = group.values()[0]
                        gene_id = group.keys()[0]
                        if not gene_id or gene_id == 'null':
                            gene_id = next((
                                gene_id for gene_id, transcripts in variants[0]['transcripts'].items()
                                if any(t['transcriptId'] == variants[0]['mainTranscriptId'] for t in transcripts)
                            ), None) if variants[0]['mainTranscriptId'] else None
                        if gene_id:
                            gene_aggs[gene_id]['total'] += len(variants)
                            for family_guid in variants[0]['familyGuids']:
                                gene_aggs[gene_id]['families'][family_guid] += len(variants)
                    return gene_aggs, {}

        return None, {}

    gene_counts, _ = _get_es_variants_for_search(search_model, EsGeneAggSearch, process_previous_results, aggregate_by_gene=True)
    return gene_counts


def _get_es_variants_for_search(search_model, es_search_cls, process_previous_results, sort=None, aggregate_by_gene=False):
    cache_key = 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)
    redis_client = None
    previous_search_results = {}
    try:
        redis_client = redis.StrictRedis(host=settings.REDIS_SERVICE_HOSTNAME, socket_connect_timeout=3)
        previous_search_results = json.loads(redis_client.get(cache_key) or '{}')
    except Exception as e:
        logger.warn("Unable to connect to redis host: {}".format(settings.REDIS_SERVICE_HOSTNAME) + str(e))

    previously_loaded_results, search_kwargs = process_previous_results(previous_search_results)
    if previously_loaded_results is not None:
        return previously_loaded_results, previous_search_results.get('total_results')

    search = search_model.variant_search.search

    genes, intervals, invalid_items = parse_locus_list_items(search.get('locus', {}))
    if invalid_items:
        raise Exception('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))
    rs_ids, variant_ids, invalid_items = _parse_variant_items(search.get('locus', {}))
    if invalid_items:
        raise Exception('Invalid variants: {}'.format(', '.join(invalid_items)))

    es_search = es_search_cls(search_model.families.all(), previous_search_results=previous_search_results, skip_unaffected_families=search.get('inheritance'))

    if sort:
        es_search.sort(sort)

    if genes or intervals or rs_ids or variant_ids:
        es_search.filter_by_location(genes, intervals, rs_ids, variant_ids, search['locus'])

    # Pathogencicity and transcript consequences act as "OR" filters instead of the usual "AND"
    pathogenicity_filter = _pathogenicity_filter(search.get('pathogenicity', {}))
    if search.get('annotations'):
        es_search.filter_by_annotations(search['annotations'], pathogenicity_filter)
    elif pathogenicity_filter:
        es_search.filter(pathogenicity_filter)

    if search.get('freqs'):
        es_search.filter(_frequency_filter(search['freqs']))

    es_search.filter_by_genotype(search.get('inheritance'), quality_filter=search.get('qualityFilter'))

    if aggregate_by_gene:
        es_search.aggregate_by_gene()

    variant_results = es_search.search(**search_kwargs)

    try:
        redis_client.set(cache_key, json.dumps(es_search.previous_search_results))
    except Exception as e:
        logger.warn("Unable to write to redis: {}".format(settings.REDIS_SERVICE_HOSTNAME) + str(e))

    return variant_results, es_search.previous_search_results['total_results']


class InvalidIndexException(Exception):
    pass


class BaseEsSearch(object):

    AGGREGATION_NAME = 'compound het'

    def __init__(self, families, previous_search_results=None, skip_unaffected_families=False, return_all_queried_families=False):
        self._client = get_es_client()

        self.samples_by_family_index = defaultdict(lambda: defaultdict(dict))
        for s in Sample.objects.filter(
            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
            elasticsearch_index__isnull=False,
            is_active=True,
            individual__family__in=families
        ).prefetch_related('individual', 'individual__family'):
            self.samples_by_family_index[s.elasticsearch_index][s.individual.family.guid][s.sample_id] = s

        if skip_unaffected_families:
            for index, family_samples in self.samples_by_family_index.items():
                index_skipped_families = []
                for family_guid, samples_by_id in family_samples.items():
                    if not any(s.individual.affected == AFFECTED for s in samples_by_id.values()):
                        index_skipped_families.append(family_guid)

                for family_guid in index_skipped_families:
                    del self.samples_by_family_index[index][family_guid]

        if len(self.samples_by_family_index) < 1:
            raise InvalidIndexException('No es index found')

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
        self._filtered_variant_ids = None
        self._no_sample_filters = False

    def _set_index_metadata(self):
        self.index_name = ','.join(self.samples_by_family_index.keys())
        if len(self.index_name) > MAX_INDEX_NAME_LENGTH:
            alias = hashlib.md5(self.index_name).hexdigest()
            self._client.indices.update_aliases(body={'actions': [
                {'add': {'indices': self.samples_by_family_index.keys(), 'alias': alias}}
            ]})
            self.index_name = alias
        self.index_metadata = get_index_metadata(self.index_name, self._client)

    def filter(self, new_filter):
        self._search = self._search.filter(new_filter)
        return self

    def filter_by_annotations(self, annotations, pathogenicity_filter):
        consequences_filter, allowed_consequences = _annotations_filter(annotations)
        if allowed_consequences:
            if pathogenicity_filter:
                consequences_filter |= pathogenicity_filter
            self.filter(consequences_filter)
            self._allowed_consequences = allowed_consequences

    def filter_by_location(self, genes, intervals, rs_ids, variant_ids, locus):
        genome_version = locus.get('genomeVersion')
        variant_id_genome_versions = {variant_id: genome_version for variant_id in variant_ids or []}
        if variant_id_genome_versions and genome_version:
            lifted_genome_version = GENOME_VERSION_GRCh37 if genome_version == GENOME_VERSION_GRCh38 else GENOME_VERSION_GRCh38
            liftover = _liftover_grch38_to_grch37() if genome_version == GENOME_VERSION_GRCh38 else _liftover_grch37_to_grch38()
            if liftover:
                for variant_id in deepcopy(variant_ids):
                    chrom, pos, ref, alt = _parse_variant_id(variant_id)
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

    def filter_by_genotype(self, inheritance, quality_filter=None):
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

        for index, family_samples_by_id in self.samples_by_family_index.items():
            if not inheritance and not quality_filter['min_ab'] and not quality_filter['min_gq']:
                search_sample_count = sum(len(samples) for samples in family_samples_by_id.values())
                index_sample_count = Sample.objects.filter(elasticsearch_index=index, is_active=True).count()
                if search_sample_count == index_sample_count:
                    # If searching across all families in an index with no inheritance mode we do not need to explicitly
                    # filter on inheritance, as all variants have some inheritance for at least one family
                    self._no_sample_filters = True
                    continue

            genotypes_q = _genotype_inheritance_filter(
                inheritance_mode, inheritance_filter, family_samples_by_id, quality_filter,
            )

            compound_het_q = None
            if inheritance_mode == COMPOUND_HET:
                compound_het_q = genotypes_q
            else:
                self._index_searches[index].append(self._search.filter(genotypes_q))

            if inheritance_mode == RECESSIVE:
                compound_het_q = _genotype_inheritance_filter(
                    COMPOUND_HET, inheritance_filter, family_samples_by_id, quality_filter,
                )

            if compound_het_q and not has_previous_compound_hets:
                compound_het_search = self._search.filter(compound_het_q)
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

    def _should_execute_single_search(self, **kwargs):
        indices = self.samples_by_family_index.keys()
        return len(indices) == 1 and len(self._index_searches.get(indices[0], [])) <= 1, {}

    def _execute_single_search(self, page=1, num_results=100, start_index=None, **kwargs):
        search = self._get_paginated_searches(
            self.index_name, page=page, num_results=num_results * len(self.samples_by_family_index), start_index=start_index
        )[0]
        response = self._execute_search(search)
        return self._parse_response(response)

    def _execute_multi_search(self, cached_counts_key=None, **kwargs):
        indices = self.samples_by_family_index.keys()

        if cached_counts_key and not self.previous_search_results.get(cached_counts_key):
            self.previous_search_results[cached_counts_key] = {}

        ms = MultiSearch()
        for index_name in indices:
            start_index = 0
            if cached_counts_key:
                if self.previous_search_results[cached_counts_key].get(index_name):
                    index_total = self.previous_search_results[cached_counts_key][index_name]['total']
                    start_index = self.previous_search_results[cached_counts_key][index_name]['loaded']
                    if start_index >= index_total:
                        continue
                else:
                    self.previous_search_results[cached_counts_key][index_name] = {'loaded': 0, 'total': 0}

            searches = self._get_paginated_searches(index_name, start_index=start_index, **kwargs)
            ms = ms.index(index_name)
            for search in searches:
                ms = ms.add(search)

        responses = self._execute_search(ms)
        return [self._parse_response(response) for response in responses]

    def _parse_response(self, response):
        raise NotImplementedError

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
                if end_index - start_index > MAX_VARIANTS:
                    end_index = start_index + MAX_VARIANTS

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


class EsSearch(BaseEsSearch):

    def sort(self, sort):
        self._sort = _get_sort(sort)
        self._search = self._search.sort(*self._sort)

    def _should_execute_single_search(self, page=1, num_results=100):
        is_single_search, _ = super(EsSearch, self)._should_execute_single_search()
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
            if num_loaded >= (page-1)*num_results:
                start_index = num_loaded
            else:
                start_index = 0
            return True, {'page': page, 'num_results': num_results, 'start_index': start_index, 'deduplicate': True}
        else:
            return False, {'page': page, 'num_results': num_results}

    def _execute_single_search(self, page=1, num_results=100, deduplicate=False, **kwargs):
        variant_results, total_results, is_compound_het, _ = super(EsSearch, self)._execute_single_search(
            page=page, num_results=num_results, deduplicate=deduplicate, **kwargs)
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

    def _execute_multi_search(self, page=1, num_results=100):
        parsed_responses = super(EsSearch, self)._execute_multi_search(
            cached_counts_key='loaded_variant_counts', page=page, num_results=num_results)

        new_results = []
        compound_het_results = self.previous_search_results.get('compound_het_results', [])
        for response_hits, response_total, is_compound_het, index_name in parsed_responses:
            if not response_total:
                continue

            if is_compound_het:
                compound_het_results += response_hits
                self.previous_search_results['loaded_variant_counts']['{}_compound_het'.format(index_name)] = {'total': response_total, 'loaded': response_total}
            else:
                new_results += response_hits
                self.previous_search_results['loaded_variant_counts'][index_name]['total'] = response_total
                self.previous_search_results['loaded_variant_counts'][index_name]['loaded'] += len(response_hits)

        self.previous_search_results['total_results'] = sum(counts['total'] for counts in self.previous_search_results['loaded_variant_counts'].values())

        # combine new results with unsorted previously loaded results to correctly sort/paginate
        all_loaded_results = self.previous_search_results.get('all_results', [])
        new_results += self.previous_search_results.get('variant_results', [])

        new_results = sorted(new_results, key=lambda variant: variant['_sort'])
        variant_results = self._deduplicate_results(new_results)

        if compound_het_results or self.previous_search_results.get('grouped_results'):
            if compound_het_results:
                compound_het_results = self._deduplicate_compound_het_results(compound_het_results)
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

    def _parse_compound_het_response(self, response):
        if len(response.aggregations.genes.buckets) > MAX_COMPOUND_HET_GENES:
            raise Exception('This search returned too many compound heterozygous variants. Please add stricter filters')

        index_name = response.hits[0].meta.index

        family_unaffected_individual_guids = {
            family_guid: {sample.individual.guid for sample in samples_by_id.values() if
                          sample.individual.affected == UNAFFECTED}
            for family_guid, samples_by_id in self.samples_by_family_index[index_name].items()
        }

        variants_by_gene = {}
        for gene_agg in response.aggregations.genes.buckets:
            gene_variants = [self._parse_hit(hit) for hit in gene_agg['vars_by_gene']]
            gene_id = gene_agg['key']

            if gene_id in variants_by_gene:
                continue

            if self._allowed_consequences:
                # Variants are returned if any transcripts have the filtered consequence, but to be compound het
                # the filtered consequence needs to be present in at least one transcript in the gene of interest
                gene_variants = [variant for variant in gene_variants if any(
                    transcript['majorConsequence'] in self._allowed_consequences for transcript in
                    variant['transcripts'][gene_id]
                )]
            if len(gene_variants) < 2:
                continue

            # Do not include groups multiple times if identical variants are in the same multiple genes
            if any(all(t['transcriptId'] != variant['mainTranscriptId'] for t in variant['transcripts'][gene_id]) for variant in gene_variants):
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
                            continue

                else:
                    variant_ids = [variant['variantId'] for variant in gene_variants]
                    for gene in primary_genes:
                        if variant_ids == [variant['variantId'] for variant in variants_by_gene.get(gene, [])]:
                            continue

            family_variants = defaultdict(list)
            for variant in gene_variants:
                for family_guid in variant['familyGuids']:
                    family_variants[family_guid].append(variant)

            for family_guid, variants in family_variants.items():
                for individual_guid in family_unaffected_individual_guids.get(family_guid, []):
                    # To be compound het all unaffected individuals need to be hom ref for at least one of the variants
                    is_family_compound_het = any(
                        variant['genotypes'].get(individual_guid, {}).get('numAlt') != 1 for variant in variants)
                    if not is_family_compound_het:
                        family_variants[family_guid] = []
                        break

            for variant in gene_variants:
                variant['familyGuids'] = [family_guid for family_guid in variant['familyGuids']
                                          if len(family_variants[family_guid]) > 1]

            gene_variants = [variant for variant in gene_variants if variant['familyGuids']]

            if gene_variants:
                variants_by_gene[gene_id] = gene_variants

        total_compound_het_results = sum(len(variants) for variants in variants_by_gene.values())
        logger.info('Total compound het hits: {}'.format(total_compound_het_results))

        return [{k: v} for k, v in variants_by_gene.items()], total_compound_het_results

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
                hg37_id = '{}-{}-{}-{}'.format(variant['liftedOverChrom'], variant['liftedOverPos'], variant['ref'], variant['alt'])
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
        for variant_group in compound_het_results:
            gene = variant_group.keys()[0]
            variants = variant_group[gene]
            if gene in results:
                for variant in variants:
                    existing_index = next(
                        (i for i, existing in enumerate(results[gene]) if existing['variantId'] == variant['variantId']), None,
                    )
                    if existing_index is not None:
                        results[gene][existing_index]['genotypes'].update(variant['genotypes'])
                        results[gene][existing_index]['familyGuids'] = sorted(
                            results[gene][existing_index]['familyGuids'] + variant['familyGuids']
                        )
                        duplicates += 1
                    else:
                        results[gene].append(variant)
            else:
                results[gene] = variants

        self.previous_search_results['duplicate_doc_count'] = duplicates + self.previous_search_results.get('duplicate_doc_count', 0)

        self.previous_search_results['total_results'] -= duplicates

        return [{k: v} for k, v in results.items()]

    def _process_compound_hets(self, compound_het_results, variant_results, num_results):
        if not self.previous_search_results.get('grouped_results'):
            self.previous_search_results['grouped_results'] = []

        # Sort merged result sets
        grouped_variants = [{None: [var]} for var in variant_results]
        grouped_variants = compound_het_results + grouped_variants
        grouped_variants = _sort_compound_hets(grouped_variants)

        loaded_result_count = sum(len(variants.values()[0]) for variants in grouped_variants + self.previous_search_results['grouped_results'])

        # Get requested page of variants
        flattened_variant_results = []
        num_compound_hets = 0
        num_single_variants = 0
        for variants_group in grouped_variants:
            variants = variants_group.values()[0]
            flattened_variant_results += variants
            if loaded_result_count != self.previous_search_results['total_results']:
                self.previous_search_results['grouped_results'].append(variants_group)
            if len(variants) > 1:
                num_compound_hets += 1
            else:
                num_single_variants += 1
            if len(flattened_variant_results) >= num_results:
                break

        # Only save non-returned results separately if have not loaded all results
        if loaded_result_count == self.previous_search_results['total_results']:
            self.previous_search_results['grouped_results'] += grouped_variants
            self.previous_search_results['compound_het_results'] = []
            self.previous_search_results['variant_results'] = []
        else:
            self.previous_search_results['compound_het_results'] = compound_het_results[num_compound_hets:]
            self.previous_search_results['variant_results'] = variant_results[num_single_variants:]

        return flattened_variant_results


class EsGeneAggSearch(BaseEsSearch):
    AGGREGATION_NAME = 'gene aggregation'

    def aggregate_by_gene(self):
        searches = {self._search}
        for index_searches in self._index_searches.values():
            searches.update(index_searches)

        for search in searches:
            agg = search.aggs.bucket(
                'genes', 'terms', field='mainTranscript_gene_id', size=MAX_COMPOUND_HET_GENES+1
            )
            if self._no_sample_filters:
                agg.bucket('samples_num_alt_1', 'terms', field='samples_num_alt_1', size=10000)
                agg.bucket('samples_num_alt_2', 'terms', field='samples_num_alt_2', size=10000)
            else:
                agg.metric(
                    'vars_by_gene', 'top_hits', size=100, _source='none'
                )

    def _execute_single_search(self, **kwargs):
        gene_aggs = super(EsGeneAggSearch, self)._execute_single_search(**kwargs)
        gene_aggs = {gene_id: {k: counts[k] for k in ['total', 'families']} for gene_id, counts in gene_aggs.items()}
        self._add_compound_hets(gene_aggs)

        self.previous_search_results['gene_aggs'] = gene_aggs

        return gene_aggs

    def _execute_multi_search(self, **kwargs):
        parsed_responses = super(EsGeneAggSearch, self)._execute_multi_search(**kwargs)
        gene_aggs = parsed_responses[0] if parsed_responses else {}
        for response in parsed_responses[1:]:
            for gene_id, count_details in response.items():
                gene_aggs[gene_id]['sample_ids'].update(count_details['sample_ids'])
                gene_aggs[gene_id]['families'].update(count_details['families'])

        gene_aggs = {
            gene_id: {'total': len(counts['sample_ids']), 'families': counts['families']}
            for gene_id, counts in gene_aggs.items()
        }

        self._add_compound_hets(gene_aggs)
        self.previous_search_results['gene_aggs'] = gene_aggs

        return gene_aggs

    def _parse_response(self, response):
        if len(response.aggregations.genes.buckets) > MAX_COMPOUND_HET_GENES:
            raise Exception('This search returned too many genes')

        gene_counts = defaultdict(lambda: {'total': 0, 'families': defaultdict(int), 'sample_ids': set()})
        for gene_agg in response.aggregations.genes.buckets:
            gene_id = gene_agg['key']
            gene_counts[gene_id]['total'] += gene_agg['doc_count']
            if 'vars_by_gene' in gene_agg:
                for hit in gene_agg['vars_by_gene']:
                    gene_counts[gene_id]['sample_ids'].add(hit.meta.id)
                    for family_guid in hit.meta.matched_queries:
                        gene_counts[gene_id]['families'][family_guid] += 1
            else:
                families_by_sample = {}
                for index_samples_by_family in self.samples_by_family_index.values():
                    for family_guid, samples_by_id in index_samples_by_family.items():
                        for sample_id in samples_by_id.keys():
                            families_by_sample[sample_id] = family_guid

                for sample_agg in gene_agg['samples_num_alt_1']['buckets']:
                    family_guid = families_by_sample[sample_agg['key']]
                    gene_counts[gene_id]['families'][family_guid] += sample_agg['doc_count']
                for sample_agg in gene_agg['samples_num_alt_2']['buckets']:
                    family_guid = families_by_sample[sample_agg['key']]
                    gene_counts[gene_id]['families'][family_guid] += sample_agg['doc_count']

        return gene_counts

    def _add_compound_hets(self, gene_counts):
        # Compound hets are always loaded as part of the initial search and are not part of the fetched aggregation
        loaded_compound_hets = self.previous_search_results.get('grouped_results', []) + \
                               self.previous_search_results.get('compound_het_results', [])
        for group in loaded_compound_hets:
            variants = group.values()[0]
            gene_id = group.keys()[0]
            if gene_id and gene_id != 'null':
                gene_counts[gene_id]['total'] += len(variants)
                for family_guid in variants[0]['familyGuids']:
                    gene_counts[gene_id]['families'][family_guid] += len(variants)


def _variant_id_filter(xpos_ref_alt_tuples):
    variant_ids = []
    for xpos, ref, alt in xpos_ref_alt_tuples:
        chrom, pos = get_chrom_pos(xpos)
        if chrom == 'M':
            chrom = 'MT'
        variant_ids.append('{}-{}-{}-{}'.format(chrom, pos, ref, alt))

    return Q('terms', variantId=variant_ids)


def _single_variant_id_filter(variant_id):
    return Q('term', variantId=variant_id)


AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED

ALT_ALT = 'alt_alt'
REF_REF = 'ref_ref'
REF_ALT = 'ref_alt'
HAS_ALT = 'has_alt'
HAS_REF = 'has_ref'
GENOTYPE_QUERY_MAP = {
    REF_REF: {'not_allowed_num_alt': ['no_call', 'num_alt_1', 'num_alt_2']},
    REF_ALT: {'allowed_num_alt': ['num_alt_1']},
    ALT_ALT: {'allowed_num_alt': ['num_alt_2']},
    HAS_ALT: {'allowed_num_alt': ['num_alt_1', 'num_alt_2']},
    HAS_REF: {'not_allowed_num_alt': ['no_call', 'num_alt_2']},
}

RECESSIVE = 'recessive'
X_LINKED_RECESSIVE = 'x_linked_recessive'
HOMOZYGOUS_RECESSIVE = 'homozygous_recessive'
COMPOUND_HET = 'compound_het'
IS_OR_INHERITANCE = 'is_or_inheritance'
RECESSIVE_FILTER = {
    AFFECTED: ALT_ALT,
    UNAFFECTED: HAS_REF,
}
INHERITANCE_FILTERS = {
    RECESSIVE: RECESSIVE_FILTER,
    X_LINKED_RECESSIVE: RECESSIVE_FILTER,
    HOMOZYGOUS_RECESSIVE: RECESSIVE_FILTER,
    COMPOUND_HET: {
        AFFECTED: REF_ALT,
        UNAFFECTED: HAS_REF,
    },
    'de_novo': {
        AFFECTED: HAS_ALT,
        UNAFFECTED: REF_REF,
    },
    'any_affected': {
        AFFECTED: HAS_ALT,
        IS_OR_INHERITANCE: True,
    },
}

#  TODO move liftover to hail pipeline once upgraded to 0.2
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
            family_samples_q = _family_genotype_inheritance_filter(
                inheritance_mode, inheritance_filter, samples_by_id
            )

            # For recessive search, should be hom recessive, x-linked recessive, or compound het
            if inheritance_mode == RECESSIVE:
                x_linked_q = _family_genotype_inheritance_filter(X_LINKED_RECESSIVE, inheritance_filter, samples_by_id)
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

    return genotypes_q


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
            if individual_affected_status[individual.guid] == UNAFFECTED and individual.sex == Individual.SEX_MALE:
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

    return samples_q


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

    if location_filter.get('excludeLocations'):
        return ~q
    else:
        return q


def _parse_variant_items(search_json):
    raw_items = search_json.get('rawVariantItems')
    if not raw_items:
        return None, None, None

    invalid_items = []
    variant_ids = []
    rs_ids = []
    for item in raw_items.replace(',', ' ').split():
        if item.startswith('rs'):
            rs_ids.append(item)
        else:
            try:
                chrom, pos, _, _ = _parse_variant_id(item)
                get_xpos(chrom, pos)
                variant_ids.append(item.lstrip('chr'))
            except (KeyError, ValueError):
                invalid_items.append(item)

    return rs_ids, variant_ids, invalid_items


def _parse_variant_id(variant_id):
    var_fields = variant_id.split('-')
    if len(var_fields) != 4:
        raise ValueError('Invalid variant id')
    return var_fields[0].lstrip('chr'), int(var_fields[1]), var_fields[2], var_fields[3]


CLINVAR_SIGNFICANCE_MAP = {
    'pathogenic': ['Pathogenic', 'Pathogenic/Likely_pathogenic'],
    'likely_pathogenic': ['Likely_pathogenic', 'Pathogenic/Likely_pathogenic'],
    'benign': ['Benign', 'Benign/Likely_benign'],
    'likely_benign': ['Likely_benign', 'Benign/Likely_benign'],
    'vus_or_conflicting': [
        'Conflicting_interpretations_of_pathogenicity',
        'Uncertain_significance',
        'not_provided',
        'other'
    ],
}

HGMD_CLASS_MAP = {
    'disease_causing': ['DM'],
    'likely_disease_causing': ['DM?'],
    'hgmd_other': ['DP', 'DFP', 'FP', 'FTV'],
}


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
    vep_consequences = [ann for annotations in annotations.values() for ann in annotations]

    consequences_filter = Q('terms', transcriptConsequenceTerms=vep_consequences)

    if 'intergenic_variant' in vep_consequences:
        # for many intergenic variants VEP doesn't add any annotations, so if user selected 'intergenic_variant', also match variants where transcriptConsequenceTerms is emtpy
        consequences_filter |= ~Q('exists', field='transcriptConsequenceTerms')

    return consequences_filter, vep_consequences


POPULATIONS = {
    'callset': {
        'AF': 'AF',
        'AC': 'AC',
        'AN': 'AN',
    },
    'topmed': {
        'use_default_field_suffix': True,
    },
    'g1k': {
        'AF': 'g1k_POPMAX_AF',
    },
    'exac': {
        'AF': 'exac_AF_POPMAX',
        'AC': 'exac_AC_Adj',
        'AN': 'exac_AN_Adj',
        'Hom': 'exac_AC_Hom',
        'Hemi': 'exac_AC_Hemi',
    },
    'gnomad_exomes': {},
    'gnomad_genomes': {},
}
POPULATION_FIELD_CONFIGS = {
    'AF': {'fields': ['AF_POPMAX_OR_GLOBAL'], 'format_value': float},
    'AC': {},
    'AN': {},
    'Hom': {},
    'Hemi': {},
}


def _get_pop_freq_key(population, freq_field):
    pop_config = POPULATIONS[population]
    field_config = POPULATION_FIELD_CONFIGS[freq_field]
    freq_suffix = freq_field
    if field_config.get('fields') and not pop_config.get('use_default_field_suffix'):
        freq_suffix = field_config['fields'][-1]
    return pop_config.get(freq_field) or '{}_{}'.format(population, freq_suffix)


def _pop_freq_filter(filter_key, value):
    return Q('range', **{filter_key: {'lte': value}}) | ~Q('exists', field=filter_key)


def _frequency_filter(frequencies):
    q = Q()
    for pop, freqs in frequencies.items():
        if freqs.get('af') is not None:
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'AF'), freqs['af'])
        elif freqs.get('ac') is not None:
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'AC'), freqs['ac'])

        if freqs.get('hh') is not None:
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'Hom'), freqs['hh'])
            q &= _pop_freq_filter(_get_pop_freq_key(pop, 'Hemi'), freqs['hh'])
    return q


def _build_or_filter(op, filters):
    if not filters:
        return None
    q = Q(op, **filters[0])
    for filter_kwargs in filters[1:]:
        q |= Q(op, **filter_kwargs)
    return q


PATHOGENICTY_SORT_KEY = 'pathogenicity'
PATHOGENICTY_HGMD_SORT_KEY = 'pathogenicity_hgmd'
CLINVAR_SORT = {
    '_script': {
        'type': 'number',
        'script': {
           'source': """
                if (doc['clinvar_clinical_significance'].empty ) {
                    return 2;
                }
                String clinsig = doc['clinvar_clinical_significance'].value;
                if (clinsig.indexOf('Pathogenic') >= 0 || clinsig.indexOf('Likely_pathogenic') >= 0) {
                    return 0;
                } else if (clinsig.indexOf('Benign') >= 0 || clinsig.indexOf('Likely_benign') >= 0) {
                    return 3;
                }
                return 1;
           """
        }
    }
}

SORT_FIELDS = {
    PATHOGENICTY_SORT_KEY: [CLINVAR_SORT],
    PATHOGENICTY_HGMD_SORT_KEY: [CLINVAR_SORT, {
        '_script': {
            'type': 'number',
            'script': {
               'source': "(!doc['hgmd_class'].empty && doc['hgmd_class'].value == 'DM') ? 0 : 1"
            }
        }
    }],
    'in_omim': [{
        '_script': {
            'type': 'number',
            'script': {
                'params': {
                    'omim_gene_ids': lambda *args: [omim.gene.gene_id for omim in Omim.objects.filter(phenotype_mim_number__isnull=False).only('gene__gene_id')]
                },
                'source': "params.omim_gene_ids.contains(doc['mainTranscript_gene_id'].value) ? 0 : 1"
            }
        }
    }],
    'protein_consequence': ['mainTranscript_major_consequence_rank'],
    'gnomad': [{_get_pop_freq_key('gnomad_genomes', 'AF'): {'missing': '_first'}}],
    'exac': [{_get_pop_freq_key('exac', 'AF'): {'missing': '_first'}}],
    '1kg': [{_get_pop_freq_key('g1k', 'AF'): {'missing': '_first'}}],
    'cadd': [{'cadd_PHRED': {'order': 'desc'}}],
    'revel': [{'dbnsfp_REVEL_score': {'order': 'desc'}}],
    'eigen': [{'eigen_Eigen_phred': {'order': 'desc'}}],
    'mpc': [{'mpc_MPC': {'order': 'desc'}}],
    'splice_ai': [{'splice_ai_delta_score': {'order': 'desc'}}],
    'primate_ai': [{'primate_ai_score': {'order': 'desc'}}],
    'constraint': [{
        '_script': {
            'order': 'asc',
            'type': 'number',
            'script': {
                'params': {
                    'constraint_ranks_by_gene': lambda *args: {
                        constraint.gene.gene_id: constraint.mis_z_rank + constraint.pLI_rank
                        for constraint in GeneConstraint.objects.all().only('gene__gene_id', 'mis_z_rank', 'pLI_rank')}
                },
                'source': "params.constraint_ranks_by_gene.getOrDefault(doc['mainTranscript_gene_id'].value, 1000000000)"
            }
        }
    }],
    XPOS_SORT_KEY: ['xpos'],
}


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


CLINVAR_FIELDS = ['clinical_significance', 'variation_id', 'allele_id', 'gold_stars']
HGMD_FIELDS = ['accession', 'class']
GENOTYPES_FIELD_KEY = 'genotypes'
HAS_ALT_FIELD_KEYS = ['samples_num_alt_1', 'samples_num_alt_2']
SORTED_TRANSCRIPTS_FIELD_KEY = 'sortedTranscriptConsequences'
NESTED_FIELDS = {
    field_name: {field: {} for field in fields} for field_name, fields in {
        'clinvar': CLINVAR_FIELDS,
        'hgmd': HGMD_FIELDS,
    }.items()
}

CORE_FIELDS_CONFIG = {
    'alt': {},
    'contig': {'response_key': 'chrom'},
    'filters': {'response_key': 'genotypeFilters', 'format_value': ','.join, 'default_value': []},
    'originalAltAlleles': {'format_value': lambda alleles: [a.split('-')[-1] for a in alleles], 'default_value': []},
    'ref': {},
    'rsid': {},
    'start': {'response_key': 'pos', 'format_value': long},
    'variantId': {},
    'xpos': {'format_value': long},
}
PREDICTION_FIELDS_CONFIG = {
    'cadd_PHRED': {'response_key': 'cadd'},
    'dbnsfp_DANN_score': {},
    'eigen_Eigen_phred': {},
    'dbnsfp_FATHMM_pred': {},
    'dbnsfp_GERP_RS': {'response_key': 'gerp_rs'},
    'mpc_MPC': {},
    'dbnsfp_MetaSVM_pred': {},
    'dbnsfp_MutationTaster_pred': {'response_key': 'mut_taster'},
    'dbnsfp_phastCons100way_vertebrate': {'response_key': 'phastcons_100_vert'},
    'dbnsfp_Polyphen2_HVAR_pred': {'response_key': 'polyphen'},
    'primate_ai_score': {'response_key': 'primate_ai'},
    'splice_ai_delta_score': {'response_key': 'splice_ai'},
    'dbnsfp_REVEL_score': {},
    'dbnsfp_SIFT_pred': {},
}
GENOTYPE_FIELDS_CONFIG = {
    'ab': {},
    'ad': {},
    'dp': {},
    'gq': {},
    'pl': {},
    'sample_id': {},
    'num_alt': {'format_value': int, 'default_value': -1},
}

DEFAULT_POP_FIELD_CONFIG = {
    'format_value': int,
    'default_value': 0,
}
POPULATION_RESPONSE_FIELD_CONFIGS = {k: dict(DEFAULT_POP_FIELD_CONFIG, **v) for k, v in POPULATION_FIELD_CONFIGS.items()}


QUERY_FIELD_NAMES = CORE_FIELDS_CONFIG.keys() + PREDICTION_FIELDS_CONFIG.keys() + \
                    [SORTED_TRANSCRIPTS_FIELD_KEY, GENOTYPES_FIELD_KEY] + HAS_ALT_FIELD_KEYS
for field_name, fields in NESTED_FIELDS.items():
    QUERY_FIELD_NAMES += ['{}_{}'.format(field_name, field) for field in fields.keys()]
for population, pop_config in POPULATIONS.items():
    for field, field_config in POPULATION_RESPONSE_FIELD_CONFIGS.items():
        if pop_config.get(field):
            QUERY_FIELD_NAMES.append(pop_config.get(field))
        QUERY_FIELD_NAMES.append('{}_{}'.format(population, field))
        QUERY_FIELD_NAMES += ['{}_{}'.format(population, custom_field) for custom_field in field_config.get('fields', [])]


def _sort_compound_hets(grouped_variants):
    return sorted(grouped_variants, key=lambda variants: variants.values()[0][0]['_sort'])


def _get_compound_het_page(grouped_variants, start_index, end_index):
    skipped = 0
    variant_results = []
    for i, variants in enumerate(grouped_variants):
        if skipped < start_index:
            skipped += len(variants.values()[0])
        else:
            variant_results += variants.values()[0]
        if len(variant_results) + skipped >= end_index:
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
