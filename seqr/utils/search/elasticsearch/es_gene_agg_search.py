from collections import defaultdict

from seqr.utils.search.elasticsearch.constants import MAX_COMPOUND_HET_GENES, HAS_ALT_FIELD_KEYS
from seqr.utils.search.elasticsearch.es_search import EsSearch


class EsGeneAggSearch(EsSearch):
    AGGREGATION_NAME = 'gene aggregation'
    CACHED_COUNTS_KEY = None

    def search(self, *args, **kwargs):
        self._aggregate_by_gene()
        return super(EsGeneAggSearch, self).search(*args, **kwargs)

    def _aggregate_by_gene(self):
        searches = [self._search]
        for index_searches in self._index_searches.values():
            searches += [index_search for index_search in index_searches]

        for search in searches:
            agg = search.aggs.bucket(
                'genes', 'terms', field='mainTranscript_gene_id', size=MAX_COMPOUND_HET_GENES+1
            )
            if self._no_sample_filters or self._any_affected_sample_filters:
                for key in HAS_ALT_FIELD_KEYS:
                    agg.bucket(key, 'terms', field=key, size=10000)
            else:
                agg.metric(
                    'vars_by_gene', 'top_hits', size=100, _source='none'
                )

    def _should_execute_single_search(self, page=1, num_results=100):
        return self._is_single_search(), {}

    def _process_single_search_response(self, parsed_response, page=1, num_results=100, deduplicate=False, **kwargs):
        gene_aggs = {gene_id: {k: counts[k] for k in ['total', 'families']} for gene_id, counts in parsed_response.items()}
        self._add_compound_hets(gene_aggs)

        self.previous_search_results['gene_aggs'] = gene_aggs

        return gene_aggs

    def _process_multi_search_responses(self, parsed_responses, page=1, num_results=100):
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
            from seqr.utils.search.utils import InvalidSearchException
            raise InvalidSearchException('This search returned too many genes')

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

                for key in HAS_ALT_FIELD_KEYS:
                    for sample_agg in gene_agg[key]['buckets']:
                        family_guid = families_by_sample.get(sample_agg['key'])
                        if family_guid:
                            gene_counts[gene_id]['families'][family_guid] += sample_agg['doc_count']
                            gene_counts[gene_id]['sample_ids'].add(sample_agg['key'])
                        else:
                            # samples may be returned that are not part of the searched families if they have no
                            # affected individuals and were removed from the "any affected" search.
                            gene_counts[gene_id]['total'] -= sample_agg['doc_count']

        return gene_counts

    def _add_compound_hets(self, gene_counts):
        # Compound hets are always loaded as part of the initial search and are not part of the fetched aggregation
        loaded_compound_hets = self.previous_search_results.get('grouped_results', []) + \
                               self.previous_search_results.get('compound_het_results', [])
        for group in loaded_compound_hets:
            variants = next(iter(group.values()))
            gene_id = next(iter(group))
            if gene_id and gene_id != 'null':
                if gene_id not in gene_counts:
                    gene_counts[gene_id] = {'total': 0, 'families': defaultdict(int)}
                gene_counts[gene_id]['total'] += len(variants)
                for family_guid in variants[0]['familyGuids']:
                    gene_counts[gene_id]['families'][family_guid] += len(variants)
