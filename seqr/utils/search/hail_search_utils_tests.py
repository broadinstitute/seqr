from copy import deepcopy
from django.test import TestCase
import json
import mock
from requests import HTTPError
import responses

from seqr.models import Family
from seqr.utils.search.utils import get_variant_query_gene_counts, query_variants, get_single_variant, \
    get_variants_for_variant_ids, InvalidSearchException
from seqr.utils.search.search_utils_tests import SearchTestHelper, MOCK_COUNTS
from hail_search.test_utils import get_hail_search_body, EXPECTED_SAMPLE_DATA, FAMILY_1_SAMPLE_DATA, \
    FAMILY_2_ALL_SAMPLE_DATA, ALL_AFFECTED_SAMPLE_DATA, CUSTOM_AFFECTED_SAMPLE_DATA, HAIL_BACKEND_VARIANTS

MOCK_HOST = 'http://test-hail-host'


@mock.patch('seqr.utils.search.hail_search_utils.HAIL_BACKEND_SERVICE_HOSTNAME', MOCK_HOST)
class HailSearchUtilsTests(SearchTestHelper, TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        super(HailSearchUtilsTests, self).set_up()
        responses.add(responses.POST, f'{MOCK_HOST}:5000/search', status=200, json={
            'results': HAIL_BACKEND_VARIANTS, 'total': 5,
        })

    def _test_minimal_search_call(self, **kwargs):
        expected_search = get_hail_search_body(genome_version='GRCh37', **kwargs)

        executed_request = responses.calls[-1].request
        self.assertEqual(executed_request.headers.get('From'), 'test_user@broadinstitute.org')
        self.assertDictEqual(json.loads(executed_request.body), expected_search)

    def _test_expected_search_call(self, search_fields=None, gene_ids=None, intervals=None, exclude_intervals= None,
                                   rs_ids=None, variant_ids=None, dataset_type=None, secondary_dataset_type=None,
                                   frequencies=None, custom_query=None, inheritance_mode='de_novo', inheritance_filter=None,
                                   quality_filter=None, sort='xpos', sort_metadata=None, **kwargs):

        expected_search = {
            'sort': sort,
            'sort_metadata': sort_metadata,
            'inheritance_mode': inheritance_mode,
            'inheritance_filter': inheritance_filter or {},
            'dataset_type': dataset_type,
            'secondary_dataset_type': secondary_dataset_type,
            'frequencies': frequencies,
            'quality_filter': quality_filter,
            'custom_query': custom_query,
            'intervals': intervals,
            'exclude_intervals': exclude_intervals,
            'gene_ids': gene_ids,
            'variant_ids': variant_ids,
            'rs_ids': rs_ids,
        }
        expected_search.update({field: self.search_model.search[field] for field in search_fields or []})

        self._test_minimal_search_call(**expected_search, **kwargs)

    @responses.activate
    def test_query_variants(self):
        variants, total = query_variants(self.results_model, user=self.user)
        self.assertListEqual(variants, HAIL_BACKEND_VARIANTS)
        self.assertEqual(total, 5)
        self.assert_cached_results({'all_results': HAIL_BACKEND_VARIANTS, 'total_results': 5})
        self._test_expected_search_call()

        variants, _ = query_variants(
            self.results_model, user=self.user, sort='cadd', skip_genotype_filter=True, page=2, num_results=1,
        )
        self.assertListEqual(variants, HAIL_BACKEND_VARIANTS[1:])
        self._test_expected_search_call(sort='cadd', num_results=2)

        self.search_model.search['locus'] = {'rawVariantItems': '1-248367227-TC-T,2-103343353-GAGA-G'}
        query_variants(self.results_model, user=self.user, sort='in_omim')
        self._test_expected_search_call(
            num_results=2,  dataset_type='VARIANTS', omit_sample_type='SV_WES', rs_ids=[],
            variant_ids=[['1', 248367227, 'TC', 'T'], ['2', 103343353, 'GAGA', 'G']],
            sort='in_omim', sort_metadata=['ENSG00000223972', 'ENSG00000243485', 'ENSG00000268020'],
        )

        self.search_model.search['locus']['rawVariantItems'] = 'rs9876'
        query_variants(self.results_model, user=self.user, sort='constraint')
        self._test_expected_search_call(
            rs_ids=['rs9876'], variant_ids=[], sort='constraint', sort_metadata={'ENSG00000223972': 2},
        )

        self.search_model.search['locus']['rawItems'] = 'DDX11L1, chr2:1234-5678, chr7:100-10100%10, ENSG00000186092'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            gene_ids=['ENSG00000223972', 'ENSG00000186092'], intervals=[
                '2:1234-5678', '7:1-11100', '1:11869-14409', '1:65419-71585'
            ],
        )

        self.search_model.search['locus']['excludeLocations'] = True
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            intervals=['2:1234-5678', '7:1-11100', '1:11869-14409', '1:65419-71585'], exclude_intervals=True,
        )

        self.search_model.search = {
            'inheritance': {'mode': 'recessive', 'filter': {'affected': {
                'I000004_hg00731': 'N', 'I000005_hg00732': 'A', 'I000006_hg00733': 'U',
            }}}, 'annotations': {'frameshift': ['frameshift_variant']},
        }
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type=None,
            search_fields=['annotations'], sample_data=CUSTOM_AFFECTED_SAMPLE_DATA,
        )

        self.search_model.search['inheritance']['filter'] = {}
        self.search_model.search['annotations_secondary'] = {'structural_consequence': ['LOF']}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type='SV',
            search_fields=['annotations', 'annotations_secondary']
        )

        self.search_model.search['annotations_secondary'].update({'SCREEN': ['dELS', 'DNase-only']})
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type='ALL',
            search_fields=['annotations', 'annotations_secondary']
        )

        self.search_model.search['annotations_secondary']['structural_consequence'] = []
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='VARIANTS', secondary_dataset_type='VARIANTS',
            search_fields=['annotations', 'annotations_secondary'], omit_sample_type='SV_WES',
        )

        quality_filter = {'min_ab': 10, 'min_gq': 15, 'vcf_filter': 'pass'}
        freq_filter = {'callset': {'af': 0.1}, 'gnomad_genomes': {'af': 0.01, 'ac': 3, 'hh': 3}}
        custom_query = {'term': {'customFlag': 'flagVal'}}
        genotype_filter = {'genotype': {'I000001_na19675': 'ref_alt'}}
        self.search_model.search = deepcopy({
            'inheritance': {'mode': 'any_affected', 'filter': genotype_filter},
            'freqs': freq_filter,
            'qualityFilter': quality_filter,
            'in_silico': {'cadd': '11.5', 'sift': 'D'},
            'customQuery': custom_query,
        })
        self.results_model.families.set(Family.objects.filter(guid='F000001_1'))
        query_variants(self.results_model, user=self.user, sort='prioritized_gene')
        expected_freq_filter = {'seqr': freq_filter['callset'], 'gnomad_genomes': freq_filter['gnomad_genomes']}
        self._test_expected_search_call(
            inheritance_mode=None, inheritance_filter=genotype_filter, sample_data=FAMILY_1_SAMPLE_DATA,
            search_fields=['in_silico'], frequencies=expected_freq_filter, quality_filter=quality_filter, custom_query=custom_query,
            sort='prioritized_gene', sort_metadata={'ENSG00000268903': 1, 'ENSG00000268904': 11},
        )

        responses.add(responses.POST, f'{MOCK_HOST}:5000/search', status=400, body='Bad Search Error')
        with self.assertRaises(HTTPError) as cm:
            query_variants(self.results_model, user=self.user)
        self.assertEqual(cm.exception.response.status_code, 400)
        self.assertEqual(cm.exception.response.text, 'Bad Search Error')

    @responses.activate
    def test_get_variant_query_gene_counts(self):
        responses.add(responses.POST, f'{MOCK_HOST}:5000/gene_counts', json=MOCK_COUNTS, status=200)

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, MOCK_COUNTS)
        self.assert_cached_results({'gene_aggs': gene_counts})
        self._test_expected_search_call(sort=None)

    @responses.activate
    def test_get_single_variant(self):
        variant = get_single_variant(self.families, '2-103343353-GAGA-G', user=self.user)
        self.assertDictEqual(variant, HAIL_BACKEND_VARIANTS[0])
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G']], variant_keys=[],
            num_results=1, sample_data=ALL_AFFECTED_SAMPLE_DATA, omit_sample_type='SV_WES')

        get_single_variant(self.families, 'prefix_19107_DEL', user=self.user)
        self._test_minimal_search_call(
            variant_ids=[], variant_keys=['prefix_19107_DEL'],
            num_results=1, sample_data=EXPECTED_SAMPLE_DATA, omit_sample_type='VARIANTS')

        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(self.families, '1-91502721-G-A', user=self.user, return_all_queried_families=True)
        self.assertEqual(
            str(cm.exception),
            'Unable to return all families for the following variants: 1-11794419-T-G (F000003_3; F000005_5), 1-91502721-G-A (F000005_5)',
        )

        get_single_variant(self.families.filter(guid='F000002_2'), '2-103343353-GAGA-G', user=self.user, return_all_queried_families=True)
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G']], variant_keys=[],
            num_results=1, sample_data=FAMILY_2_ALL_SAMPLE_DATA)

        responses.add(responses.POST, f'{MOCK_HOST}:5000/search', status=200, json={'results': [], 'total': 0})
        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(self.families, '10-10334333-A-G', user=self.user)
        self.assertEqual(str(cm.exception), 'Variant 10-10334333-A-G not found')

    @responses.activate
    def test_get_variants_for_variant_ids(self):
        variant_ids = ['2-103343353-GAGA-G', '1-248367227-TC-T', 'prefix-938_DEL']
        get_variants_for_variant_ids(self.families, variant_ids, user=self.user)
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G'], ['1', 248367227, 'TC', 'T']],
            variant_keys=['prefix-938_DEL'],
            num_results=3, sample_data=ALL_AFFECTED_SAMPLE_DATA)

        get_variants_for_variant_ids(self.families, variant_ids, user=self.user, dataset_type='VARIANTS')
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G'], ['1', 248367227, 'TC', 'T']],
            variant_keys=[],
            num_results=2, sample_data=ALL_AFFECTED_SAMPLE_DATA, omit_sample_type='SV_WES')
