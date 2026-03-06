from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
import json
import mock

from clickhouse_search.test_utils import VARIANT1, VARIANT2, VARIANT3, VARIANT4, PROJECT_2_VARIANT2, format_cached_variant, \
    GENE_COUNTS, VARIANT_LOOKUP_VARIANT, SV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT, SV_VARIANT1
from seqr.models import Project, Family, Sample, VariantSearch, VariantSearchResults
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets
from seqr.utils.search.utils import get_single_variant, get_variant_query_gene_counts, \
    query_variants, variant_lookup, InvalidSearchException
from seqr.views.utils.test_utils import DifferentDbTransactionSupportMixin, \
    PARSED_VARIANTS, PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, GENE_FIELDS


SV_SAMPLES = ['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733']
MITO_SAMPLES = ['S000149_hg00733']
NON_SNP_INDEL_SAMPLES = SV_SAMPLES + MITO_SAMPLES
FAMILY_3_SAMPLE = 'S000135_na20870'

GENE_COUNTS = {
    **GENE_COUNTS,
    'ENSG00000177000': {**GENE_COUNTS['ENSG00000177000'], 'total': 3},
    'ENSG00000277258': {**GENE_COUNTS['ENSG00000277258'], 'total': 2},
}

class SearchTestHelper(object):

    def set_up(self):
        patcher = mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
        self.mock_redis = patcher.start().return_value
        self.addCleanup(patcher.stop)

        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])
        self.user = User.objects.get(username='test_user')

        self.search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}, 'freqs': {'callset': {'ac': 1000}}})
        self.results_model = VariantSearchResults.objects.create(variant_search=self.search_model)
        self.results_model.families.set(self.families)

    def set_cache(self, cached):
        self.mock_redis.get.return_value = json.dumps(cached)

    def assert_cached_results(self, expected_results, sort='xpos', cache_key=None):
        cache_key = cache_key or f'search_results__{self.results_model.guid}__{sort}'
        self.mock_redis.set.assert_called_with(cache_key, mock.ANY)
        self.assertEqual(json.loads(self.mock_redis.set.call_args.args[1]), expected_results)
        self.mock_redis.expire.assert_called_with(cache_key, timedelta(weeks=2))


class SearchUtilsTests(DifferentDbTransactionSupportMixin, TestCase, SearchTestHelper):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_transcripts']

    PARSED_CACHED_VARIANTS = [VARIANT1, VARIANT2, VARIANT3, VARIANT4]
    CACHED_VARIANTS = [format_cached_variant(v) for v in PARSED_CACHED_VARIANTS]

    def setUp(self):
        self.set_up()

        self.non_affected_search_samples = Sample.objects.filter(guid__in=[
             'S000137_na20874',
        ])
        self.affected_search_samples = Sample.objects.filter(guid__in=[
            'S000132_hg00731', 'S000133_hg00732', 'S000134_hg00733', FAMILY_3_SAMPLE,
            'S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733', 'S000149_hg00733',
        ])
        self.search_samples = list(self.affected_search_samples) + list(self.non_affected_search_samples)


    def _get_expected_search_call(self, results_cache, search_fields=None, has_gene_search=False,
                                   variant_ids=None, parsed_variant_ids=None, inheritance_mode='de_novo',
                                   dataset_type=None, secondary_dataset_type=None, exclude_keys=None, exclude_key_pairs=None,
                                   exclude_locations=False, exclude=None, annotations=None, annotations_secondary=None, single_gene_search=False, **kwargs):
        genes = intervals = None
        if has_gene_search:
            genes = {'ENSG00000186092': mock.ANY, 'ENSG00000227232': mock.ANY}
            intervals = [{'chrom': '2', 'start': 1234, 'end': 5678, 'offset': None}, {'chrom': '7', 'start': 100, 'end': 10100, 'offset': 0.1}]
        if single_gene_search:
            genes = {'ENSG00000227232': mock.ANY}
            intervals = intervals[2:3]

        expected_search = {
            'inheritance_mode': inheritance_mode,
            'inheritance_filter': {},
            'skipped_samples': mock.ANY,
            'dataset_type': dataset_type,
            'secondary_dataset_type': secondary_dataset_type,
            'exclude_locations': exclude_locations,
            'genes': genes,
            'intervals': intervals,
            'freqs': {'callset': {'ac': 1000}},
        }
        if not genes:
            expected_search.update({
                'parsed_variant_ids': parsed_variant_ids,
                'variant_ids': variant_ids,
            })
        expected_search.update({field: self.search_model.search[field] for field in search_fields or []})
        if exclude:
            expected_search['exclude'] = exclude
        if annotations is not None:
            expected_search['annotations'] = annotations
        if annotations_secondary is not None:
            expected_search['annotations_secondary'] = annotations_secondary
        if exclude_keys is not None:
            expected_search['exclude_keys'] = exclude_keys
        if exclude_key_pairs is not None:
            expected_search['exclude_key_pairs'] = exclude_key_pairs

        return (mock.ANY, expected_search, self.user, results_cache, '37'), kwargs, genes

    def _test_expected_search_call(self, mock_get_variants, *args, has_gene_search=False, exclude_locations=False, omitted_sample_guids=None, **kwargs):
        call_args, call_kwargs, genes = self._get_expected_search_call(*args, has_gene_search=has_gene_search, exclude_locations=exclude_locations, **kwargs)
        mock_get_variants.assert_called_with(*call_args, **call_kwargs)
        self._assert_expected_search_samples(mock_get_variants, omitted_sample_guids, has_gene_search and not exclude_locations)

        if genes:
            parsed_genes = mock_get_variants.call_args.args[1]['genes']
            for gene in parsed_genes.values():
                self.assertSetEqual(set(gene.keys()), {'id', *GENE_FIELDS})
            self.assertEqual(parsed_genes['ENSG00000227232']['geneSymbol'], 'WASH7P')
            if len(genes) > 1:
                self.assertEqual(parsed_genes['ENSG00000186092']['geneSymbol'], 'OR4F5')


    def _assert_expected_search_samples(self, mock_get_variants, omitted_sample_guids, has_gene_search):
        searched_samples = self.affected_search_samples
        non_affected_search_samples = self.non_affected_search_samples
        if omitted_sample_guids:
            searched_samples = searched_samples.exclude(guid__in=omitted_sample_guids)
            non_affected_search_samples = non_affected_search_samples.exclude(guid__in=omitted_sample_guids)
        if has_gene_search:
            searched_samples = searched_samples.exclude(guid__in=MITO_SAMPLES)
        self.assertSetEqual(set(mock_get_variants.call_args.args[0]), set(searched_samples))
        self.assertSetEqual(set(mock_get_variants.call_args.args[1]['skipped_samples']), set(non_affected_search_samples))



    def _assert_expected_cached_variants(self, variants, num_results):
        self.assertListEqual(
            json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets)),
            self.PARSED_CACHED_VARIANTS[:num_results],
        )

    @mock.patch('seqr.utils.search.utils.get_clickhouse_variants')
    def test_get_variant_query_gene_counts(self, mock_get_variants):
        gene_agg_all_results = self.CACHED_VARIANTS + [format_cached_variant(PROJECT_2_VARIANT2)]
        def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['all_results'] = gene_agg_all_results
            return None

        mock_get_variants.side_effect = _mock_get_variants

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, GENE_COUNTS)
        results_cache = {'all_results': gene_agg_all_results}
        self.assert_cached_results(results_cache)
        kwargs = dict(sort=None, num_results=100)
        self._test_expected_search_call(
            mock_get_variants, results_cache, **kwargs,
        )
