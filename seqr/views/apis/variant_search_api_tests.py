import json
import mock
import responses
from copy import deepcopy

from django.db import transaction
from django.urls.base import reverse

from seqr.models import LocusList, Project, VariantSearch
from seqr.views.apis.variant_search_api import vlm_lookup_handler, search_context_handler, get_saved_search_handler, \
    create_saved_search_handler, update_saved_search_handler, delete_saved_search_handler
from seqr.views.utils.test_utils import AuthenticationTestCase, LOCUS_LIST_FIELDS, PA_LOCUS_LIST_FIELDS, \
    ANALYSIS_GROUP_FIELDS, DYNAMIC_ANALYSIS_GROUP_FIELDS

LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'
SEARCH_HASH = 'd380ed0fd28c3127d07a64ea2ba907d7'
SEARCH = {'filters': {}, 'inheritance': None}
PROJECT_FAMILIES = [{'projectGuid': PROJECT_GUID, 'familyGuids': ['F000001_1', 'F000002_2']}]

PROJECT_CONTEXT_FIELDS = {'locusListGuids', 'datasetTypes', 'analysisGroupsLoaded', 'projectGuid', 'name'}

EXPECTED_SEARCH_CONTEXT_RESPONSE = {
    'savedSearchesByGuid': {
        'VS0079516_': mock.ANY, 'VS0079525_': mock.ANY, 'VS0079517_': mock.ANY, 'VS0145435_': mock.ANY,
    },
    'projectsByGuid': {PROJECT_GUID: mock.ANY},
    'familiesByGuid': mock.ANY,
    'analysisGroupsByGuid': {'AG0000183_test_group': mock.ANY, 'AG0000185_accepted': mock.ANY, 'DAG0000001_unsolved': mock.ANY, 'DAG0000002_my_new_cases': mock.ANY},
    'locusListsByGuid': {LOCUS_LIST_GUID: mock.ANY, 'LL00005_retina_proteome': mock.ANY},
}

MOCK_TOKEN = 'mock_token' # nosec
MOCK_CLIENT_ID = 'mock_client_id'
VLM_CLIENTS_RESPONSE = [
    {'client_id': MOCK_CLIENT_ID, 'name': 'Self', 'client_metadata': {'match_url': 'https://self.com'}},
    {'client_id': 'client1', 'name': 'Node 1', 'client_metadata': {'match_url': 'https://node1.com'}},
    {'client_id': 'client2', 'name': 'Node 2', 'client_metadata': {'match_url': 'https://node2.com'}},
    {'client_id': 'client1', 'name': 'Node 3', 'client_metadata': {'other_url': 'https://node3.com'}},
    {'client_id': 'client1', 'name': 'Node 4'},
]
VLM_MATCH_URL = 'https://node1.com/variant_lookup/1-10439-AC-A'
VLM_MATCH_RESPONSE = {
    'beaconHandovers': [
        {
            'handoverType': {'id': 'Test Node', 'label': 'Test Node browser'},
            'url': VLM_MATCH_URL,
        },
        {
            'handoverType': {'id': 'Test SecondaryDB', 'label': 'Test secondary database'},
            'url': f'{VLM_MATCH_URL}/secondarydb',
        }
    ],
    'meta': {
        'apiVersion': 'v1.0',
        'beaconId': 'com.gnx.beacon.v2',
        'returnedSchemas': [
            {
                'entityType': 'genomicVariant',
                'schema': 'ga4gh-beacon-variant-v2.0.0',
            }
        ]
    },
    'responseSummary': {
        'exists': True,
        'total': 30,
    },
    'response': {
        'resultSets': [
            {
                'exists': True,
                'id': 'Test Node Homozygous',
                'results': [],
                'resultsCount': 7,
                'setType': 'genomicVariant'
            },
            {
                'exists': True,
                'id': 'Test Node Heterozygous',
                'results': [],
                'resultsCount': 23,
                'setType': 'genomicVariant'
            },
            {
                'exists': False,
                'id': 'Test SecondaryDB Homozygous',
                'results': [],
                'resultsCount': 0,
                'setType': 'genomicVariant'
            },
            {
                'exists': True,
                'id': 'Test SecondaryDB Heterozygous',
                'results': [],
                'resultsCount': 2,
                'setType': 'genomicVariant'
            },
        ],
    }
}
VLM_MATCH_RESPONSE_2 = {
    'beaconHandovers': [
        {
            'handoverType': {'id': 'Node2', 'label': ''},
            'url': None,
            'email': 'vlm_test@node2.org',
        }
    ],
    'meta': {
        'apiVersion': 'v1.0',
        'beaconId': 'com.gnx.beacon.v2',
        'returnedSchemas': [
            {
                'entityType': 'genomicVariant',
                'schema': 'ga4gh-beacon-variant-v2.0.0',
            }
        ]
    },
    'responseSummary': {
        'exists': True,
        'total': 30,
    },
    'response': {
        'resultSets': [
            {
                'exists': True,
                'id': 'Homozygous',
                'results': [],
                'resultsCount': 1,
                'setType': 'genomicVariant'
            },
            {
                'exists': False,
                'id': 'Heterozygous',
                'results': [],
                'resultsCount': 0,
                'setType': 'genomicVariant'
            },
        ],
    }
}


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
class VariantSearchAPITest(AuthenticationTestCase):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'variant_searches', 'clickhouse_saved_variants']

    def _assert_expected_search_context(self, response_json):
        self.assertSetEqual(set(response_json), set(EXPECTED_SEARCH_CONTEXT_RESPONSE))
        self.assertDictEqual(response_json, EXPECTED_SEARCH_CONTEXT_RESPONSE)

        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_CONTEXT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID]['datasetTypes']), {'SNV_INDEL', 'SV', 'MITO'})

        locus_list_fields = deepcopy(LOCUS_LIST_FIELDS)
        locus_list_fields.update(PA_LOCUS_LIST_FIELDS)
        locus_list_fields.remove('numEntries')
        locus_list_fields.remove('canEdit')
        self.assertSetEqual(set(response_json['locusListsByGuid'][LOCUS_LIST_GUID].keys()), locus_list_fields)
        self.assertSetEqual(set(response_json['analysisGroupsByGuid']['AG0000183_test_group'].keys()), ANALYSIS_GROUP_FIELDS)
        self.assertSetEqual(set(response_json['analysisGroupsByGuid']['DAG0000001_unsolved'].keys()), DYNAMIC_ANALYSIS_GROUP_FIELDS)

        self.assertEqual(len(response_json['familiesByGuid']), 11)
        self.assertSetEqual(set(response_json['familiesByGuid']['F000001_1'].keys()), {
            'projectGuid', 'familyGuid', 'displayName', 'analysisStatus', 'analysedBy', 'assignedAnalyst', 'sampleTypes',
        })
        self.assertDictEqual(response_json['familiesByGuid']['F000001_1'], {
            'projectGuid': PROJECT_GUID, 'familyGuid': 'F000001_1', 'displayName': '1', 'analysisStatus': 'Q',
            'assignedAnalyst': None, 'sampleTypes': [{'datasetType': 'SNV_INDEL', 'sampleType': 'WES', 'isActive': True}],
            'analysedBy': [{'createdBy': 'Test No Access User', 'dataType': 'SNP', 'lastModifiedDate': '2022-07-22T19:27:08.563+00:00'}],
        })

    def test_search_context(self):
        search_context_url = reverse(search_context_handler)
        self.check_collaborator_login(search_context_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'foo': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"foo": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"familyGuid": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectGuid': PROJECT_GUID}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'F000001_1'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'analysisGroupGuid': 'AG0000183_test_group'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        # Test fetching multiple projects where a locus list is contained in a non-included project
        LocusList.objects.get(guid=LOCUS_LIST_GUID).projects.add(Project.objects.get(id=2))

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectCategoryGuid': 'PC000003_test_category_name'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        expected_response = {
            'savedSearchesByGuid': mock.ANY,
            'projectCategoriesByGuid': {'PC000003_test_category_name': mock.ANY},
        }
        expected_response.update(deepcopy(EXPECTED_SEARCH_CONTEXT_RESPONSE))
        expected_response['projectsByGuid']['R0003_test'] = mock.ANY
        self.assertSetEqual(set(response_json), set(expected_response))
        self.assertDictEqual(response_json, expected_response)
        self.assertEqual(len(response_json['savedSearchesByGuid']), 4)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_CONTEXT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID]['datasetTypes']), {'SNV_INDEL', 'SV', 'MITO'})
        self.assertSetEqual(set(response_json['projectsByGuid']['R0003_test']['datasetTypes']), {'SNV_INDEL'})
        self.assertEqual(len(response_json['familiesByGuid']), 13)

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
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        # Test all project search context
        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': 'djd29394hfw2njr2hod2', 'searchParams': {'allGenomeProjectFamilies': '37', 'search': SEARCH}}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)


    @mock.patch('seqr.views.utils.vlm_utils.VLM_CLIENT_SECRET', 'abc123')
    @mock.patch('seqr.views.utils.vlm_utils.VLM_CLIENT_ID', MOCK_CLIENT_ID)
    @mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
    @responses.activate
    def test_vlm_lookup(self, mock_redis):
        mock_cache = {}
        mock_redis.return_value.get.side_effect = mock_cache.get
        mock_redis.return_value.set.side_effect = lambda key, val, **kwargs: mock_cache.update({key: val})
        responses.add(
            responses.POST, 'https://vlm-auth.us.auth0.com/oauth/token', json={'access_token': MOCK_TOKEN},
        )
        responses.add(
            responses.GET, 'https://vlm-auth.us.auth0.com/api/v2/clients?fields=client_id,name,client_metadata&is_global=false',
            json=VLM_CLIENTS_RESPONSE,
        )
        match_url_template = 'https://{}.com/?assemblyId=GRCh38&referenceName=1&start=10439&referenceBases=C&alternateBases=A'
        node_1_url = match_url_template.format('node1')
        responses.add(responses.GET, node_1_url, json=VLM_MATCH_RESPONSE)
        node_2_url = match_url_template.format('node2')
        responses.add(responses.GET, node_2_url, status=400)

        base_url = reverse(vlm_lookup_handler)
        url = f'{base_url}?variantId=1-10439-C-A&genomeVersion=38'
        self.check_require_login(url)

        response = self.client.get(f'{base_url}?variantId=phase2_DEL_chr14_464')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'VLM lookup is not supported for SVs'})

        response = self.client.get(f'{base_url}?variantId=8-10439--ATGS')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Unable to search VLM for invalid allele(s): "", "ATGS"'})

        response = self.client.get(f'{base_url}?variantId=1-10439-AC-A')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'VLM lookup is not supported for InDels'})

        self.reset_logs()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        expected_body = {'vlmMatches': {
            'Node 1': {
                'Test Node': {'url': VLM_MATCH_URL, 'counts': {'Heterozygous': 23, 'Homozygous': 7}},
                'Test SecondaryDB': {'url': f'{VLM_MATCH_URL}/secondarydb', 'counts': {'Heterozygous': 2, 'Homozygous': 0}},
            }
        }}
        self.assertDictEqual(response.json(), expected_body)

        self.assertEqual(len(responses.calls), 4)
        self.assertFalse('Authorization' in responses.calls[0].request.headers, {})
        self.assertSetEqual({call.request.headers['Authorization'] for call in responses.calls[1:]}, {'Bearer mock_token'})

        expected_params = {
            'assemblyId': 'GRCh38',
            'alternateBases': 'A',
            'referenceBases': 'C',
            'referenceName': '1',
            'start': 10439,
        }
        expected_logs = [
            ('VLM match request to Node 1', {'detail': expected_params}),
            ('VLM match request to Node 2', {'detail': expected_params}),
            (f'VLM Node 2 match error: 400 Client Error: Bad Request for url: {node_2_url}', {
                'severity': 'ERROR',
                '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
                'detail': expected_params,
            }),
        ]
        self.assert_json_logs(self.no_access_user, expected_logs)

        # test with cached token and clients
        self.reset_logs()
        responses.calls.reset()
        responses.add(responses.GET, node_2_url, json=VLM_MATCH_RESPONSE_2)
        expected_body['vlmMatches']['Node 2'] = {
            'Node2': {'url': 'mailto:vlm_test@node2.org', 'counts': {'Heterozygous': 0, 'Homozygous': 1}}
        }
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), expected_body)
        self.assertEqual(len(responses.calls), 2)
        self.assertListEqual([call.request.url for call in responses.calls], [node_1_url, node_2_url])
        self.assertSetEqual({call.request.headers['Authorization'] for call in responses.calls}, {'Bearer mock_token'})
        self.assert_json_logs(None, [
            ('Loaded VLM_TOKEN from redis', None),
            ('Loaded VLM_CLIENTS from redis', None),
        ])
        self.assert_json_logs(self.no_access_user, expected_logs[:2], offset=2)


    def test_saved_search(self):
        get_saved_search_url = reverse(get_saved_search_handler)
        self.check_require_login(get_saved_search_url)

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)

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
            'savedSearchGuid': search_guid, 'name': 'Test Search', 'search': SEARCH, 'createdById': 13, 'order': None,
        })

        # Test no errors if duplicate searches get created
        dup_search_guid = VariantSearch.objects.create(search=SEARCH, created_by=self.no_access_user).guid
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json()['savedSearchesByGuid'].keys()), [search_guid])
        self.assertIsNone(VariantSearch.objects.filter(guid=dup_search_guid).first())

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 5)

        # Test cannot save different searches with the same name
        body['filters'] = {'test': 'filter'}
        with transaction.atomic():
            response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Saved search with name "Test Search" already exists')

        # Test update endpoint
        update_saved_search_url = reverse(update_saved_search_handler, args=[search_guid])
        body['name'] = None
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body['name'] = 'Updated Test Search'
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json()['savedSearchesByGuid'][search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Updated Test Search', 'search': SEARCH, 'createdById': 13, 'order': None,
        })

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedSearchesByGuid': {search_guid: None}})

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)

        global_saved_search_guid = next(iter(response.json()['savedSearchesByGuid']))

        update_saved_search_url = reverse(update_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 403)

    def test_search_results_redirect(self):
        response = self.client.get('/report/custom_search/6ebb895dfca0f63c34be1ca59d950205?page=2&sort=cadd')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/variant_search/results/6ebb895dfca0f63c34be1ca59d950205?page=2&sort=cadd')
