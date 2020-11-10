import json
import mock
from copy import deepcopy

from django.urls.base import reverse
from elasticsearch.exceptions import ConnectionTimeout

from seqr.models import VariantSearchResults, LocusList, Project, VariantSearch
from seqr.utils.elasticsearch.utils import InvalidIndexException
from seqr.views.apis.variant_search_api import query_variants_handler, query_single_variant_handler, \
    export_variants_handler, search_context_handler, get_saved_search_handler, create_saved_search_handler, \
    update_saved_search_handler, delete_saved_search_handler, get_variant_gene_breakdown
from seqr.views.utils.test_utils import AuthenticationTestCase, VARIANTS, AnvilAuthenticationTestCase,\
    MixAuthenticationTestCase, WORKSPACE_FIELDS

LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'
SEARCH_HASH = 'd380ed0fd28c3127d07a64ea2ba907d7'
SEARCH = {'filters': {}, 'inheritance': None}
PROJECT_FAMILIES = [{'projectGuid': PROJECT_GUID, 'familyGuids': ['F000001_1', 'F000002_2']}]

VARIANTS_WITH_DISCOVERY_TAGS = deepcopy(VARIANTS)
VARIANTS_WITH_DISCOVERY_TAGS[2]['discoveryTags'] = [{
    'savedVariant': {
        'variantGuid': 'SV0000006_1248367227_r0003_tes',
        'familyGuid': 'F000011_11',
        'projectGuid': 'R0003_test',
    },
    'tagGuid': 'VT1726961_2103343353_r0003_tes',
    'name': 'Tier 1 - Novel gene and phenotype',
    'category': 'CMG Discovery Tags',
    'color': '#03441E',
    'searchHash': None,
    'lastModifiedDate': '2018-05-29T16:32:51.449Z',
    'createdBy': None,
}]


def _get_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(VARIANTS), len(VARIANTS)


def _get_empty_es_variants(results_model, **kwargs):
    results_model.save()
    return [], 0


COMP_HET_VARAINTS = [[VARIANTS[2], VARIANTS[1]]]
def _get_compound_het_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(COMP_HET_VARAINTS), 1


class VariantSearchAPITest(object):
    multi_db = True

    @mock.patch('seqr.views.apis.variant_search_api.get_es_variant_gene_counts')
    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_variants(self, mock_get_variants, mock_get_gene_counts):
        url = reverse(query_variants_handler, args=['abc'])
        self.check_collaborator_login(url, request_data={'projectFamilies': PROJECT_FAMILIES})
        url = reverse(query_variants_handler, args=[SEARCH_HASH])

        # add a locus list
        LocusList.objects.get(guid=LOCUS_LIST_GUID).projects.add(Project.objects.get(guid=PROJECT_GUID))

        # Test invalid inputs
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))

        response = self.client.post(url, content_type='application/json', data=json.dumps({'search': SEARCH}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search: no projects/ families specified')

        mock_get_variants.side_effect = InvalidIndexException('Invalid index')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid index')

        mock_get_variants.side_effect = ConnectionTimeout()
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.reason_phrase, 'Query Time Out')

        mock_get_variants.side_effect = _get_es_variants

        # Test new search
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'searchedVariants', 'savedVariantsByGuid', 'genesById', 'search', 'variantTagsByGuid', 'variantNotesByGuid',
            'variantFunctionalDataByGuid', 'locusListsByGuid'})
        self.assertListEqual(response_json['searchedVariants'], VARIANTS)
        self.assertDictEqual(response_json['search'], {
            'search': SEARCH,
            'projectFamilies': [{'projectGuid': PROJECT_GUID, 'familyGuids': mock.ANY}],
            'totalResults': 3,
        })
        self.assertSetEqual(
            set(response_json['search']['projectFamilies'][0]['familyGuids']), {'F000001_1', 'F000002_2'})
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100'}
        )
        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000227232', 'ENSG00000268903', 'ENSG00000233653'}
        )
        self.assertListEqual(
            response_json['genesById']['ENSG00000227232']['locusListGuids'], [LOCUS_LIST_GUID]
        )
        self.assertSetEqual(set(response_json['locusListsByGuid'].keys()), {LOCUS_LIST_GUID})
        intervals = response_json['locusListsByGuid'][LOCUS_LIST_GUID]['intervals']
        self.assertEqual(len(intervals), 2)
        self.assertSetEqual(
            set(intervals[0].keys()), {'locusListGuid', 'locusListIntervalGuid', 'genomeVersion', 'chrom', 'start', 'end'}
        )

        results_model = VariantSearchResults.objects.get(search_hash=SEARCH_HASH)
        mock_get_variants.assert_called_with(results_model, sort='xpos', page=1, num_results=100)

        # Test pagination
        response = self.client.get('{}?page=3'.format(url))
        self.assertEqual(response.status_code, 200)
        mock_get_variants.assert_called_with(results_model, sort='xpos', page=3, num_results=100)

        # Test sort
        response = self.client.get('{}?sort=pathogenicity'.format(url))
        self.assertEqual(response.status_code, 200)
        mock_get_variants.assert_called_with(results_model, sort='pathogenicity', page=1, num_results=100)

        # Test export
        export_url = reverse(export_variants_handler, args=[SEARCH_HASH])
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)
        expected_content = [
            ['chrom', 'pos', 'ref', 'alt', 'gene', 'worst_consequence', '1kg_freq', 'exac_freq', 'gnomad_genomes_freq',
             'gnomad_exomes_freq', 'topmed_freq', 'cadd', 'revel', 'eigen', 'polyphen', 'sift', 'muttaster', 'fathmm',
             'rsid', 'hgvsc', 'hgvsp', 'clinvar_clinical_significance', 'clinvar_gold_stars', 'filter', 'family_id_1',
             'tags_1', 'notes_1', 'family_id_2', 'tags_2', 'notes_2', 'sample_1:num_alt_alleles:gq:ab',
             'sample_2:num_alt_alleles:gq:ab'],
            ['21', '3343400', 'GAGA', 'G', 'WASH7P', 'missense_variant', '', '', '', '', '', '', '', '', '', '', '', '',
             '', 'ENST00000623083.3:c.1075G>A', 'ENSP00000485442.1:p.Gly359Ser', '', '', '', '1',
             'Tier 1 - Novel gene and phenotype (None)|Review (None)', '', '2', '', '', 'NA19675:1:46.0:0.702127659574', 'NA19679:0:99.0:0.0'],
            ['3', '835', 'AAAG', 'A', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '1', '', '', '', '', '', 'NA19679:0:99.0:0.0', ''],
            ['12', '48367227', 'TC', 'T', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '2', 'Known gene for phenotype (None)|Excluded (None)', 'test n\xf8te (None)', '', '', '', '', '']]
        self.assertEqual(response.content, ('\n'.join(['\t'.join(line) for line in expected_content])+'\n').encode('utf-8'))

        mock_get_variants.assert_called_with(results_model, page=1, load_all=True)

        # Test gene breakdown
        gene_counts = {
            'ENSG00000227232': {'total': 2, 'families': {'F000001_1': 2, 'F000002_2': 1}},
            'ENSG00000268903': {'total': 1, 'families': {'F000002_2': 1}}
        }
        mock_get_gene_counts.return_value = gene_counts

        gene_breakdown_url = reverse(get_variant_gene_breakdown, args=[SEARCH_HASH])
        response = self.client.get(gene_breakdown_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'searchGeneBreakdown', 'genesById'})
        self.assertDictEqual(response_json['searchGeneBreakdown'], {SEARCH_HASH: gene_counts})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000227232', 'ENSG00000268903'})

        # Test compound hets
        mock_get_variants.side_effect = _get_compound_het_es_variants
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'searchedVariants', 'savedVariantsByGuid', 'genesById', 'search', 'variantTagsByGuid', 'variantNotesByGuid',
            'variantFunctionalDataByGuid', 'locusListsByGuid'})
        self.assertListEqual(response_json['searchedVariants'], COMP_HET_VARAINTS)
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000002_1248367227_r0390_100'}
        )
        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000233653'}
        )

        # Test cross-project discovery for staff users
        self.login_staff_user()
        mock_get_variants.side_effect = _get_es_variants
        response = self.client.get('{}?sort=pathogenicity'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'searchedVariants', 'savedVariantsByGuid', 'genesById', 'search', 'variantTagsByGuid', 'variantNotesByGuid',
            'variantFunctionalDataByGuid', 'familiesByGuid', 'locusListsByGuid'})

        self.assertListEqual(response_json['searchedVariants'], VARIANTS_WITH_DISCOVERY_TAGS)
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {'F000011_11'})
        mock_get_variants.assert_called_with(results_model, sort='pathogenicity_hgmd', page=1, num_results=100)

        # Test no results
        mock_get_variants.side_effect = _get_empty_es_variants
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {
            'searchedVariants': [],
            'search': {
                'search': SEARCH,
                'projectFamilies': PROJECT_FAMILIES,
                'totalResults': 0,
            }
        })

    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_all_projects_variants(self, mock_get_variants):
        url = reverse(query_variants_handler, args=[SEARCH_HASH])
        self.check_require_login(url)

        mock_get_variants.side_effect = _get_es_variants

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'allProjectFamilies': True, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['search'], {
            'search': SEARCH,
            'projectFamilies': [],
            'totalResults': 3,
        })

        VariantSearchResults.objects.get(search_hash=SEARCH_HASH).delete()
        self.login_collaborator()
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'allProjectFamilies': True, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['search'], {
            'search': SEARCH,
            'projectFamilies': [{'projectGuid': PROJECT_GUID, 'familyGuids': mock.ANY}],
            'totalResults': 3,
        })
        self.assertSetEqual(
            set(response_json['search']['projectFamilies'][0]['familyGuids']),
            {'F000001_1', 'F000002_2', 'F000003_3', 'F000004_4', 'F000005_5', 'F000006_6', 'F000007_7', 'F000008_8',
             'F000009_9', 'F000010_10', 'F000013_13'}
        )

    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_all_project_families_variants(self, mock_get_variants):
        url = reverse(query_variants_handler, args=['abc'])
        self.check_collaborator_login(url, request_data={'projectGuids': ['R0003_test']})
        url = reverse(query_variants_handler, args=[SEARCH_HASH])

        mock_get_variants.side_effect = _get_es_variants

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectGuids': ['R0003_test'], 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['search'], {
            'search': SEARCH,
            'projectFamilies': [{'projectGuid': 'R0003_test', 'familyGuids': ['F000011_11', 'F000012_12']}],
            'totalResults': 3,
        })

    def test_search_context(self):
        search_context_url = reverse(search_context_handler)
        self.check_collaborator_login(search_context_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'foo': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"foo": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectGuid': PROJECT_GUID}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'igvSamplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'F000001_1'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'igvSamplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'analysisGroupGuid': 'AG0000183_test_group'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'igvSamplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectCategoryGuid': 'PC000003_test_category_name'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'igvSamplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', 'projectCategoriesByGuid'}
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertSetEqual(set(response_json['projectsByGuid'].keys()), {PROJECT_GUID, 'R0003_test'})
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])
        self.assertListEqual(list(response_json['projectCategoriesByGuid'].keys()), ['PC000003_test_category_name'])

        # Test search hash context
        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH, 'searchParams': {'search': SEARCH}}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search: no projects/ families specified')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH, 'searchParams': {'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH}}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'igvSamplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'igvSamplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])

    @mock.patch('seqr.views.apis.variant_search_api.get_single_es_variant')
    def test_query_single_variant(self, mock_get_variant):
        mock_get_variant.return_value = VARIANTS[0]

        url = '{}?familyGuid=F000001_1'.format(reverse(query_single_variant_handler, args=['21-3343353-GAGA-G']))
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'searchedVariants', 'savedVariantsByGuid', 'genesById', 'projectsByGuid', 'familiesByGuid',
             'individualsByGuid', 'samplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', 'variantTagsByGuid',
             'variantNotesByGuid', 'variantFunctionalDataByGuid', 'igvSamplesByGuid', }
        )

        self.assertListEqual(response_json['searchedVariants'], VARIANTS[:1])
        self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), {'SV0000001_2103343353_r0390_100'})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000227232', 'ENSG00000268903'})
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])

    def test_saved_search(self):
        get_saved_search_url = reverse(get_saved_search_handler)
        self.check_require_login(get_saved_search_url)

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 3)

        create_saved_search_url = reverse(create_saved_search_handler)

        response = self.client.post(create_saved_search_url, content_type='application/json', data='{}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body = {'name': 'Test Search'}

        invalid_body = {'inheritance': {'filter': {'genotype': {'indiv_1': 'ref_alt'}}}}
        invalid_body.update(body)
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(invalid_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Saved searches cannot include custom genotype filters')

        body.update(SEARCH)
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        saved_searches = response.json()['savedSearchesByGuid']
        self.assertEqual(len(saved_searches), 1)
        search_guid = next(iter(saved_searches))
        self.assertDictEqual(saved_searches[search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Test Search', 'search': SEARCH, 'createdById': 13,
        })

        # Test no errors if duplicate searches get created
        dup_search_guid = VariantSearch.objects.create(search=SEARCH, created_by=self.no_access_user).guid
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json()['savedSearchesByGuid'].keys()), [search_guid])
        self.assertIsNone(VariantSearch.objects.filter(guid=dup_search_guid).first())

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)

        update_saved_search_url = reverse(update_saved_search_handler, args=[search_guid])
        body['name'] = None
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body['name'] = 'Updated Test Search'
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json()['savedSearchesByGuid'][search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Updated Test Search', 'search': SEARCH, 'createdById': 13,
        })

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedSearchesByGuid': {search_guid: None}})

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 3)

        global_saved_search_guid = next(iter(response.json()['savedSearchesByGuid']))

        update_saved_search_url = reverse(update_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 403)


# Tests for AnVIL access disabled
class LocalVariantSearchAPITest(AuthenticationTestCase, VariantSearchAPITest):
    fixtures = ['users', '1kg_project', 'reference_data', 'variant_searches']


def assert_no_list_ws_has_acl(self, acl_call_count, path=None):
    self.mock_list_workspaces.assert_not_called()
    if not path:
        path = 'api/workspaces/my-seqr-billing/anvil-1kg project n\u00e5me with uni\u00e7\u00f8de/acl'
    self.mock_service_account.get.assert_called_with(path)
    self.assertEqual(self.mock_service_account.get.call_count, acl_call_count)


# Test for permissions from AnVIL only
class AnvilVariantSearchAPITest(AnvilAuthenticationTestCase, VariantSearchAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'variant_searches']

    def test_query_variants(self):
        super(AnvilVariantSearchAPITest, self).test_query_variants()
        assert_no_list_ws_has_acl(self, 9)

    def test_query_all_projects_variants(self):
        super(AnvilVariantSearchAPITest, self).test_query_all_projects_variants()
        calls = [
            mock.call(self.no_access_user, fields=WORKSPACE_FIELDS),
            mock.call(self.collaborator_user, fields = WORKSPACE_FIELDS),
        ]
        self.mock_list_workspaces.assert_has_calls(calls)
        self.mock_service_account.get.assert_called_with(
            'api/workspaces/my-seqr-billing/anvil-1kg project n\u00e5me with uni\u00e7\u00f8de/acl')
        self.assertEqual(self.mock_service_account.get.call_count, 1)

    def test_query_all_project_families_variants(self):
        super(AnvilVariantSearchAPITest, self).test_query_all_project_families_variants()
        assert_no_list_ws_has_acl(self, 2, path='api/workspaces/my-seqr-billing/anvil-project 1000 Genomes Demo/acl')
        # self.mock_list_workspaces.assert_not_called() self.mock_service_account.get.assert_not_called()

    def test_search_context(self):
        super(AnvilVariantSearchAPITest, self).test_search_context()
        assert_no_list_ws_has_acl(self, 15)

    def test_query_single_variant(self):
        super(AnvilVariantSearchAPITest, self).test_query_single_variant()
        assert_no_list_ws_has_acl(self, 3)

    def test_saved_search(self):
        super(AnvilVariantSearchAPITest, self).test_saved_search()
        self.mock_list_workspaces.assert_not_called()
        self.mock_service_account.get.assert_not_called()


# Test for permissions from AnVIL and local
class MixSavedVariantSearchAPITest(MixAuthenticationTestCase, VariantSearchAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'variant_searches']

    def test_query_variants(self):
        super(MixSavedVariantSearchAPITest, self).test_query_variants()
        assert_no_list_ws_has_acl(self, 1)

    def test_query_all_projects_variants(self):
        super(MixSavedVariantSearchAPITest, self).test_query_all_projects_variants()
        calls = [
            mock.call(self.no_access_user, fields=WORKSPACE_FIELDS),
            mock.call(self.collaborator_user, fields = WORKSPACE_FIELDS),
        ]
        self.mock_list_workspaces.assert_has_calls(calls)
        self.mock_service_account.get.assert_not_called()

    def test_query_all_project_families_variants(self):
        super(MixSavedVariantSearchAPITest, self).test_query_all_project_families_variants()
        assert_no_list_ws_has_acl(self, 1, path='api/workspaces/my-seqr-billing/anvil-project 1000 Genomes Demo/acl')

    def test_search_context(self):
        super(MixSavedVariantSearchAPITest, self).test_search_context()
        assert_no_list_ws_has_acl(self, 8)

    def test_query_single_variant(self):
        super(MixSavedVariantSearchAPITest, self).test_query_single_variant()
        assert_no_list_ws_has_acl(self, 2)

    def test_saved_search(self):
        super(MixSavedVariantSearchAPITest, self).test_saved_search()
        self.mock_list_workspaces.assert_not_called()
        self.mock_service_account.get.assert_not_called()
