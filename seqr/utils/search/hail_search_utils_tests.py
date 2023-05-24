from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
import json
import mock
import responses

from seqr.models import Family, Sample, VariantSearch, VariantSearchResults
from seqr.utils.search.utils import get_single_variant, get_variants_for_variant_ids, get_variant_query_gene_counts, \
    query_variants, InvalidSearchException
from seqr.utils.search.search_utils_tests import MOCK_COUNTS
from seqr.views.utils.test_utils import PARSED_VARIANTS, PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, GENE_FIELDS

MOCK_HOST = 'http://test-hail-host'


@mock.patch('seqr.utils.search.hail_search_utils.HAIL_BACKEND_SERVICE_HOSTNAME', MOCK_HOST)
class HailSearchUtilsTests(TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        patcher = mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
        self.mock_redis = patcher.start().return_value
        self.addCleanup(patcher.stop)

        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])
        self.non_affected_search_samples = Sample.objects.filter(guid__in=[
             'S000149_hg00733',  'S000137_na20874',
        ])
        self.affected_search_samples = Sample.objects.filter(guid__in=[
            'S000132_hg00731', 'S000133_hg00732', 'S000134_hg00733', 'S000135_na20870',
            'S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733',
        ])
        self.search_samples = list(self.affected_search_samples) + list(self.non_affected_search_samples)
        self.user = User.objects.get(username='test_user')

        self.search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}})
        self.results_model = VariantSearchResults.objects.create(variant_search=self.search_model)
        self.results_model.families.set(self.families)

    def assert_cached_results(self, expected_results, sort='xpos'):
        cache_key = f'search_results__{self.results_model.guid}__{sort}'
        self.mock_redis.set.assert_called_with(cache_key, json.dumps(expected_results))
        self.mock_redis.expire.assert_called_with(cache_key, timedelta(weeks=2))

    def _test_expected_search_call(self, search_fields=None, gene_ids=None, intervals=None, rs_ids=None, variant_ids=None,
                                   inheritance_mode='de_novo',  dataset_type=None, secondary_dataset_type=None):
        request_body = json.loads(responses.calls[-1].request.body)
        expected_search = {
            'requester_email': 'test_user@broadinstitute.org',
            'sample_data': {
                'VARIANTS': [
                    {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2',
                     'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
                    {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2',
                     'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
                    {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2',
                     'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'},
                    {'sample_id': 'NA20870', 'individual_guid': 'I000007_na20870', 'family_guid': 'F000003_3',
                     'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'M'},
                ], 'SV_WES': [
                    {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2',
                     'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
                    {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2',
                     'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
                    {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2',
                     'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'}
                ],
            },
            'genome_version': 'GRCh37',
            'sort': None,
            'sort_metadata': None,
            'num_results': 100,
            'inheritance_mode': inheritance_mode,
            'inheritance_filter': {},
            'dataset_type': dataset_type,
            'secondary_dataset_type': secondary_dataset_type,
            'frequencies': None,
            'quality_filter': None,
            'custom_query': None,
            'intervals': intervals,
            'exclude_intervals': None,
            'gene_ids': gene_ids,
            'variant_ids': variant_ids,
            'rs_ids': rs_ids,
        }
        expected_search.update({field: self.search_model.search[field] for field in search_fields or []})
        self.assertDictEqual(request_body, expected_search)

    # def test_query_variants(self):
    #     def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
    #         previous_search_results['all_results'] = PARSED_VARIANTS
    #         previous_search_results['total_results'] = 5
    #         return PARSED_VARIANTS
    #     mock_get_variants.side_effect = _mock_get_variants
    #
    #     variants, total = query_variants(self.results_model, user=self.user)
    #     self.assertListEqual(variants, PARSED_VARIANTS)
    #     self.assertEqual(total, 5)
    #     results_cache = {'all_results': PARSED_VARIANTS, 'total_results': 5}
    #     self.assert_cached_results(results_cache)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
    #     )
    #
    #     query_variants(
    #         self.results_model, user=self.user, sort='cadd', skip_genotype_filter=True, page=3, num_results=10,
    #     )
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='cadd', page=3, num_results=10, skip_genotype_filter=True,
    #     )
    #
    #     query_variants(self.results_model, user=self.user, load_all=True)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=10000, skip_genotype_filter=False,
    #     )
    #
    #     self.search_model.search['locus'] = {'rawVariantItems': '1-248367227-TC-T,2-103343353-GAGA-G'}
    #     query_variants(self.results_model, user=self.user)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=2, skip_genotype_filter=False,
    #         search_fields=['locus'], rs_ids=[],  variant_ids=['1-248367227-TC-T', '2-103343353-GAGA-G'],
    #         parsed_variant_ids=[('1', 248367227, 'TC', 'T'), ('2', 103343353, 'GAGA', 'G')], dataset_type='VARIANTS',
    #         omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733'],
    #     )
    #
    #     self.search_model.search['locus']['rawVariantItems'] = 'rs9876'
    #     query_variants(self.results_model, user=self.user)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
    #         search_fields=['locus'], rs_ids=['rs9876'], variant_ids=[], parsed_variant_ids=[],
    #     )
    #
    #     self.search_model.search['locus']['rawItems'] = 'DDX11L1, chr2:1234-5678, chr7:100-10100%10, ENSG00000186092'
    #     query_variants(self.results_model, user=self.user)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
    #         search_fields=['locus'], genes={
    #             'ENSG00000223972': mock.ANY, 'ENSG00000186092': mock.ANY,
    #         }, intervals=[
    #             {'chrom': '2', 'start': 1234, 'end': 5678, 'offset': None},
    #             {'chrom': '7', 'start': 100, 'end': 10100, 'offset': 0.1},
    #         ],
    #     )
    #     parsed_genes = mock_get_variants.call_args.args[1]['parsedLocus']['genes']
    #     for gene in parsed_genes.values():
    #         self.assertSetEqual(set(gene.keys()), GENE_FIELDS)
    #     self.assertEqual(parsed_genes['ENSG00000223972']['geneSymbol'], 'DDX11L1')
    #     self.assertEqual(parsed_genes['ENSG00000186092']['geneSymbol'], 'OR4F5')
    #
    #     self.search_model.search = {
    #         'inheritance': {'mode': 'recessive'}, 'annotations': {'frameshift': ['frameshift_variant']},
    #     }
    #     query_variants(self.results_model, user=self.user)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
    #         inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type=None,
    #         search_fields=['annotations'], omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733'],
    #     )
    #
    #     self.search_model.search['annotations_secondary'] = {'structural_consequence': ['LOF']}
    #     query_variants(self.results_model, user=self.user)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
    #         inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type='SV',
    #         search_fields=['annotations', 'annotations_secondary']
    #     )
    #
    #     self.search_model.search['annotations_secondary'].update({'SCREEN': ['dELS', 'DNase-only']})
    #     query_variants(self.results_model, user=self.user)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
    #         inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type='ALL',
    #         search_fields=['annotations', 'annotations_secondary']
    #     )
    #
    #     self.search_model.search['annotations_secondary']['structural_consequence'] = []
    #     query_variants(self.results_model, user=self.user)
    #     self._test_expected_search_call(
    #         mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
    #         inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type='VARIANTS',
    #         search_fields=['annotations', 'annotations_secondary'],
    #         omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733'],
    #     )

    @responses.activate
    def test_get_variant_query_gene_counts(self):
        responses.add(responses.POST, f'{MOCK_HOST}:5000/gene_counts', json=MOCK_COUNTS, status=200)

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, MOCK_COUNTS)
        results_cache = {'gene_aggs': gene_counts}
        self.assert_cached_results(results_cache)
        self._test_expected_search_call()
