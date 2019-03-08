import json
import mock
from copy import deepcopy

from django.test import TestCase
from django.urls.base import reverse

from seqr.models import VariantSearchResults, VariantSearch, Family
from seqr.utils.es_utils import InvalidIndexException
from seqr.views.apis.locus_list_api import add_project_locus_lists
from seqr.views.apis.variant_search_api import query_variants_handler, query_single_variant_handler, \
    export_variants_handler, search_context_handler, get_saved_search_handler, create_saved_search_handler
from seqr.views.utils.test_utils import _check_login


LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'
SEARCH_HASH = 'd380ed0fd28c3127d07a64ea2ba907d7'
SEARCH = {'filters': {}}
PROJECT_FAMILIES = [{'projectGuid': PROJECT_GUID, 'familyGuids': ['F000001_1', 'F000002_2']}]
VARIANTS = [
    {'alt': 'G', 'ref': 'GAGA', 'chrom': '21', 'pos': 3343353, 'xpos': 2103343353, 'genomeVersion': '38',
     'transcripts': {'ENSG00000227232': {}, 'ENSG00000268903': {}}, 'familyGuids': ['F000001_1', 'F000002_2'],
     'genotypes': {'NA19675': {'sampleId': 'NA19675', 'ab': 0.7021276595744681, 'gq': 46.0, 'numAlt': 1, 'dp': '50', 'ad': '14,33'},
                   'NA19679': {'sampleId': 'NA19679', 'ab': 0.0, 'gq': 99.0, 'numAlt': 0, 'dp': '45', 'ad': '45,0'}}},
    {'alt': 'A', 'ref': 'AAAG', 'chrom': '3', 'pos': 835, 'xpos': 3000000835, 'genomeVersion': '38', 'transcripts': {}, 'familyGuids': ['F000001_1'], 'genotypes': {'NA19679': {'ab': 0.0, 'gq': 99.0, 'num_alt': 0, 'dp': '45', 'ad': '45,0'}}},
    {'alt': 'T', 'ref': 'TC', 'chrom': '12', 'pos': 48367227, 'xpos': 1248367227, 'genomeVersion': '38', 'transcripts': {'ENSG00000233653': {}}, 'familyGuids': ['F000002_2'], 'genotypes': {}},
]
EXPECTED_VARIANTS = deepcopy(VARIANTS)
EXPECTED_VARIANTS[0]['locusLists'] = []
EXPECTED_VARIANTS[1]['locusLists'] = ['PID genes - Autosomal dominant']
EXPECTED_VARIANTS[2]['locusLists'] = []


def _get_es_variants(results_model, **kwargs):
    results_model.total_results = len(VARIANTS)
    results_model.save()
    return deepcopy(VARIANTS)


class VariantSearchAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data', 'variant_searches']

    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_variants(self, mock_get_variants):
        url = reverse(query_variants_handler, args=[SEARCH_HASH])
        _check_login(self, url)

        # add a locus list
        response = self.client.post(
            reverse(add_project_locus_lists, args=[PROJECT_GUID]), content_type='application/json',
            data=json.dumps({'locusListGuids': [LOCUS_LIST_GUID]}))
        self.assertEqual(response.status_code, 200)

        # Test invalid inputs
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search: no projects/ families specified')

        mock_get_variants.side_effect = InvalidIndexException('Invalid index')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid index')

        mock_get_variants.side_effect = _get_es_variants

        # Test new search
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'searchedVariants', 'savedVariantsByGuid', 'genesById', 'search'})

        self.assertListEqual(response_json['searchedVariants'], EXPECTED_VARIANTS)
        self.assertDictEqual(response_json['search'], {
            'search': SEARCH,
            'projectFamilies': PROJECT_FAMILIES,
            'totalResults': 3,
        })
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100'}
        )
        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000227232', 'ENSG00000268903', 'ENSG00000233653'}
        )
        self.assertListEqual(
            response_json['genesById']['ENSG00000227232']['locusLists'], ['PID genes - Autosomal dominant']
        )

        results_models = VariantSearchResults.objects.filter(search_hash=SEARCH_HASH)
        self.assertEqual(results_models.count(), 1)
        self.assertEqual(results_models.first().sort, 'xpos')
        mock_get_variants.assert_called_with(results_models.first(), page=1, num_results=100)

        # Test pagination
        response = self.client.get('{}?page=3'.format(url))
        self.assertEqual(response.status_code, 200)
        results_models = VariantSearchResults.objects.filter(search_hash=SEARCH_HASH)
        self.assertEqual(results_models.count(), 1)
        mock_get_variants.assert_called_with(results_models.first(), page=3, num_results=100)

        # Test sort
        response = self.client.get('{}?sort=consequence'.format(url))
        self.assertEqual(response.status_code, 200)
        results_models = VariantSearchResults.objects.filter(search_hash=SEARCH_HASH)
        self.assertEqual(results_models.count(), 2)
        self.assertSetEqual({rm.sort for rm in results_models}, {'xpos', 'consequence'})
        mock_get_variants.assert_called_with(results_models.last(), page=1, num_results=100)

        # Test export
        export_url = reverse(export_variants_handler, args=[SEARCH_HASH])
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)
        export_content = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        self.assertEqual(len(export_content), 4)
        self.assertListEqual(
            export_content[0],
            ['chrom', 'pos', 'ref', 'alt', 'gene', 'worst_consequence', '1kg_freq', 'exac_freq', 'gnomad_genomes_freq',
            'gnomad_exomes_freq', 'topmed_freq', 'cadd', 'revel', 'eigen', 'polyphen', 'sift', 'muttaster', 'fathmm',
             'rsid', 'hgvsc', 'hgvsp', 'clinvar_clinical_significance', 'clinvar_gold_stars', 'filter', 'family_id_1',
             'tags_1', 'notes_1', 'family_id_2', 'tags_2', 'notes_2', 'sample_id_1', 'num_alt_alleles_1', 'ad_1',
             'dp_1', 'gq_1', 'ab_1', 'sample_id_2', 'num_alt_alleles_2', 'ad_2', 'dp_2', 'gq_2', 'ab_2'])
        self.assertListEqual(
            export_content[1],
            ['21', '3343353', 'GAGA', 'G', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '1', 'Tier 1 - Novel gene and phenotype (None)|Review (None)', '', '2', '', '', 'NA19675', '1',
             '14,33', '50', '46.0', '0.702127659574', 'NA19679', '0', '45,0', '45', '99.0', '0.0'])

        mock_get_variants.assert_called_with(results_models.first(), page=1, num_results=3)

    def test_search_context(self):
        search_context_url = reverse(search_context_handler)
        _check_login(self, search_context_url)

        response = self.client.get('{}?foo=bar'.format(search_context_url))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid query params: {"foo": "bar"}')

        response = self.client.get('{}?projectGuid={}'.format(search_context_url, PROJECT_GUID))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.get('{}?familyGuid=F000001_1'.format(search_context_url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.get('{}?analysisGroupGuid=AG0000183_test_group'.format(search_context_url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.get('{}?searchHash={}'.format(search_context_url, SEARCH_HASH))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))

        results_model = VariantSearchResults.objects.create(
            search_hash=SEARCH_HASH,
            variant_search=VariantSearch.objects.create(search=SEARCH),
        )
        results_model.families.set(Family.objects.filter(guid__in=['F000001_1', 'F000002_2']))

        response = self.client.get('{}?searchHash={}'.format(search_context_url, SEARCH_HASH))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'searchesByHash', 'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid',
             'individualsByGuid', 'samplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid',}
        )
        self.assertDictEqual(response.json()['searchesByHash'][SEARCH_HASH], {
            'search': SEARCH,
            'projectFamilies': PROJECT_FAMILIES,
            'totalResults': None,
        })
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

    @mock.patch('seqr.views.apis.variant_search_api.get_single_es_variant')
    def test_query_single_variant(self, mock_get_variant):
        mock_get_variant.return_value = VARIANTS[0]

        url = reverse(query_single_variant_handler, args=['21-3343353-GAGA-G'])
        _check_login(self, url)

        response = self.client.get('{}?familyGuid=F000001_1'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'searchedVariants', 'savedVariantsByGuid', 'genesById', 'projectsByGuid', 'familiesByGuid',
             'individualsByGuid', 'samplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid',}
        )

        self.assertListEqual(response_json['searchedVariants'], EXPECTED_VARIANTS[:1])
        self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), {'SV0000001_2103343353_r0390_100'})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000227232', 'ENSG00000268903'})
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])

    def test_saved_search(self):
        get_saved_search_url = reverse(get_saved_search_handler)
        _check_login(self, get_saved_search_url)

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 3)

        create_saved_search_url = reverse(create_saved_search_handler)

        response = self.client.post(create_saved_search_url, content_type='application/json', data='{}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body = {'name': 'Test Search'}
        body.update(SEARCH)
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        saved_searches = response.json()['savedSearchesByGuid']
        self.assertEqual(len(saved_searches), 1)
        search_guid = saved_searches.keys()[0]
        self.assertDictEqual(saved_searches[search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Test Search', 'search': SEARCH,
        })

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)
