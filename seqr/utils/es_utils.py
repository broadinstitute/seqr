from collections import defaultdict
import elasticsearch
from elasticsearch_dsl import Q
import logging

from settings import ELASTICSEARCH_SERVICE_HOSTNAME
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.utils.es_search_constants import XPOS_SORT_KEY, VARIANT_DOC_TYPE, MAX_COMPOUND_HET_GENES
from seqr.utils.es_search_helper import EsSearch
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.xpos_utils import get_chrom_pos, get_xpos

logger = logging.getLogger(__name__)


def get_es_client(timeout=30):
    return elasticsearch.Elasticsearch(host=ELASTICSEARCH_SERVICE_HOSTNAME, timeout=timeout, retry_on_timeout=True)


def get_index_metadata(index_name, client):
    cache_key = 'index_metadata__{}'.format(index_name)
    cached_metadata = safe_redis_get_json(cache_key)
    if cached_metadata:
        return cached_metadata

    try:
        mappings = client.indices.get_mapping(index=index_name, doc_type=[VARIANT_DOC_TYPE])
    except Exception as e:
        raise InvalidIndexException('Error accessing index "{}": {}'.format(
            index_name, e.error if hasattr(e, 'error') else e.message))
    index_metadata = {}
    for index_name, mapping in mappings.items():
        variant_mapping = mapping['mappings'].get(VARIANT_DOC_TYPE, {})
        index_metadata[index_name] = variant_mapping.get('_meta', {})
        index_metadata[index_name]['fields'] = variant_mapping['properties'].keys()
    safe_redis_set_json(cache_key, index_metadata)
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


def get_es_variants(search_model, sort=XPOS_SORT_KEY, **kwargs):
    return _get_es_variants_for_search(search_model, EsSearch, sort=sort, **kwargs)


def get_es_variant_gene_counts(search_model):
    gene_counts, _ = _get_es_variants_for_search(search_model, EsGeneAggSearch, aggregate_by_gene=True)
    return gene_counts


def _get_es_variants_for_search(search_model, es_search_cls, sort=None, aggregate_by_gene=False, **kwargs):
    cache_key = 'search_results__{}__{}'.format(search_model.guid, sort or XPOS_SORT_KEY)
    previous_search_results = safe_redis_get_json(cache_key) or {}

    previously_loaded_results, search_kwargs = es_search_cls.process_previous_results(previous_search_results,  **kwargs)
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
        if (variant_ids or rs_ids) and not (genes or intervals) and not search['locus'].get('excludeLocations'):
            search_kwargs['num_results'] = len(variant_ids) + len(rs_ids)

    if search.get('freqs'):
        es_search.filter(_frequency_filter(search['freqs']))

    es_search.filter_by_annotation_and_genotype(
        search.get('inheritance'), quality_filter=search.get('qualityFilter'),
        annotations=search.get('annotations'), annotations_secondary=search.get('annotations_secondary'),
        pathogenicity=search.get('pathogenicity'))

    if aggregate_by_gene:
        es_search.aggregate_by_gene()

    variant_results = es_search.search(**search_kwargs)

    safe_redis_set_json(cache_key, es_search.previous_search_results)

    return variant_results, es_search.previous_search_results['total_results']


class InvalidIndexException(Exception):
    pass


class EsGeneAggSearch(EsSearch):
    AGGREGATION_NAME = 'gene aggregation'
    CACHED_COUNTS_KEY = None

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

    def _should_execute_single_search(self, **kwargs):
        indices = self.samples_by_family_index.keys()
        return len(indices) == 1 and len(self._index_searches.get(indices[0], [])) <= 1, {}

    def _process_single_search_response(self, gene_aggs, **kwargs):
        gene_aggs = {gene_id: {k: counts[k] for k in ['total', 'families']} for gene_id, counts in gene_aggs.items()}
        self._add_compound_hets(gene_aggs)

        self.previous_search_results['gene_aggs'] = gene_aggs

        return gene_aggs

    def _process_multi_search_responses(self, parsed_responses, **kwargs):
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

    @classmethod
    def process_previous_results(cls, previous_search_results, **kwargs):
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
                chrom, pos, _, _ = parse_variant_id(item)
                get_xpos(chrom, pos)
                variant_ids.append(item.lstrip('chr'))
            except (KeyError, ValueError):
                invalid_items.append(item)

    return rs_ids, variant_ids, invalid_items


def parse_variant_id(variant_id):
    var_fields = variant_id.split('-')
    if len(var_fields) != 4:
        raise ValueError('Invalid variant id')
    return var_fields[0].lstrip('chr'), int(var_fields[1]), var_fields[2], var_fields[3]
