import json
import responses
import mock

from copy import deepcopy
from datetime import datetime
from django.urls.base import reverse

from matchmaker.models import MatchmakerResult, MatchmakerContactNotes, MatchmakerSubmission
from matchmaker.matchmaker_utils import MME_DISCLAIMER
from matchmaker.views.matchmaker_api import get_individual_mme_matches, search_individual_mme_matches, \
    update_mme_submission, delete_mme_submission, update_mme_result_status, send_mme_contact_email, \
    get_mme_nodes, search_local_individual_mme_matches, finalize_mme_search, \
    update_mme_contact_note, update_mme_project_contact
from seqr.views.utils.test_utils import AuthenticationTestCase

INDIVIDUAL_GUID = 'I000001_na19675'
SUBMISSION_GUID = 'MS000001_na19675'
INVALID_PROJECT_SUBMISSION_GUID = 'MS000016_P0004515'
NO_SUBMISSION_INDIVIDUAL_GUID = 'I000006_hg00733'
RESULT_STATUS_GUID = 'MR0003552_SHE_1006P_1'

SUBMISSION_DATA = {
    'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
    'contactHref': 'mailto:test@broadinstitute.org',
    'contactName': 'PI',
    'phenotypes': [
        {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
    ],
    'geneVariants': [{
        'geneId': 'ENSG00000235249',
        'variantGuid': 'SV0000002_1248367227_r0390_100',
    }, {
        'geneId': 'ENSG00000135953',
        'variantGuid': 'SV0000002_1248367227_r0390_100',
    }],
}

PARSED_RESULT = {
    'id': 'P0004515',
    'score': 0.5706712016939723,
    'submissionGuid': SUBMISSION_GUID,
    'patient': {
        'genomicFeatures': [
            {'gene': {'id': 'OR4F5'}, 'variant': {
                'alternateBases': 'A', 'assembly': 'GRCh37', 'referenceBases': 'G', 'referenceName': '2', 'start': 100379086,
            }},
            {'gene': {'id': 'CICP27'}},
            {'gene': {'id': 'DDX11L1'}},
        ],
        'contact': {
            'href': 'mailto:UDNCC@hms.harvard.edu,matchmaker@phenomecentral.org',
            'name': 'Baylor UDN Clinical Site'
        },
        'id': 'P0004515',
        'features': [
            {'id': 'HP:0012469', 'observed': 'yes'},
            {'id': 'HP:0003273', 'observed': 'no'},
        ],
    },
    'phenotypes': [
        {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'},
        {'id': 'HP:0003273', 'label': 'Hip contracture', 'observed': 'no'},
    ],
    'geneVariants': [
        {'geneId': 'ENSG00000186092', 'variant': {
            'alt':  'A',
            'ref': 'G',
            'chrom': '2',
            'pos': 100379086,
            'end': None,
            'genomeVersion': 'GRCh37'
        }},
        {'geneId': 'ENSG00000233750'},
        {'geneId': 'ENSG00000223972'},
    ],
    'matchStatus': {
        'matchmakerResultGuid': RESULT_STATUS_GUID,
        'comments': 'AMBRA1 c.2228G>C p.(Ser743Thr) missense variant. Maternally inherited, both have epilepsy',
        'weContacted': False,
        'hostContacted': True,
        'deemedIrrelevant': True,
        'flagForAnalysis': False,
        'matchRemoved': False,
        'createdDate': '2019-02-12T18:43:56.358Z',
    },
    'originatingSubmission': {
        'originatingSubmissionGuid': 'MS000016_P0004515',
        'familyGuid': 'F000012_12',
        'projectGuid': 'R0003_test',
    }
}

NEW_MATCH_JSON = {
    "score": {
        "patient": 0.92
    },
    "patient": {
        "genomicFeatures": [
            {
                "gene": {
                    "id": "RP11"
                }
            }
        ],
        'features': [{'observed': 'yes', 'id': 'HP:0012469', 'label': 'Infantile spasms'}],
        "contact": {
            "href": "mailto:Rmaroofian@gmail.com",
            "name": "Reza Maroofian",
            "institution": "St Georges, University of London"
        },
        "id": "33845",
        "label": "ADARB1-AR-EE"
    }
}

REMOVED_MATCH_JSON = deepcopy(NEW_MATCH_JSON)
REMOVED_MATCH_JSON['patient']['id'] = '10509'

PARSED_NEW_MATCH_JSON = {
    'id': '33845',
    'score': 0.92,
    'patient': NEW_MATCH_JSON['patient'],
    'submissionGuid': SUBMISSION_GUID,
    'phenotypes': [{'observed': 'yes', 'id': 'HP:0012469', 'label': 'Infantile spasms'}],
    'geneVariants': [{'geneId': 'ENSG00000135953'}],
    'matchStatus': {
        'matchmakerResultGuid': mock.ANY,
        'comments': None,
        'weContacted': False,
        'hostContacted': False,
        'deemedIrrelevant': False,
        'flagForAnalysis': False,
        'matchRemoved': False,
        'createdDate': mock.ANY,
    },
}
PARSED_NEW_MATCH_NEW_SUBMISSION_JSON = deepcopy(PARSED_NEW_MATCH_JSON)
PARSED_NEW_MATCH_NEW_SUBMISSION_JSON['submissionGuid'] = mock.ANY

INVALID_NEW_MATCH_JSON = deepcopy(NEW_MATCH_JSON)
INVALID_NEW_MATCH_JSON['patient'] = {}

INVALID_GENE_NEW_MATCH_JSON = deepcopy(NEW_MATCH_JSON)
INVALID_GENE_NEW_MATCH_JSON['patient']['genomicFeatures'][0]['gene'] = {}
INVALID_GENE_NEW_MATCH_JSON['patient']['id'] = '123'

INVALID_FEATURES_NEW_MATCH_JSON = deepcopy(NEW_MATCH_JSON)
INVALID_FEATURES_NEW_MATCH_JSON['patient']['features'][0] = {}
INVALID_FEATURES_NEW_MATCH_JSON['patient']['id'] = '456'

MISMATCHED_GENE_NEW_MATCH_JSON = deepcopy(NEW_MATCH_JSON)
MISMATCHED_GENE_NEW_MATCH_JSON['patient']['genomicFeatures'][0]['gene']['id'] = 'ENSG00000227232'
MISMATCHED_GENE_NEW_MATCH_JSON['patient']['id'] = '987'

MOCK_SLACK_TOKEN = 'xoxp-123'  # nosec

MOCK_NODES_BY_NAME = {
    'Node A': {'name': 'Node A', 'token': 'abc', 'url': 'http://node_a.com/match'},
    'Node B': {'name': 'Node B', 'token': 'xyz', 'url': 'http://node_b.mme.org/api'},
}

class EmailException(Exception):

    def __init__(self, json=None):
        self.response = mock.MagicMock()
        self.response.content = 'email error'
        if json:
            self.response.json.return_value = json
        else:
            self.response.json.side_effect = Exception
        self.status_code = 402


class MatchmakerAPITest(AuthenticationTestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def test_get_individual_mme_matches(self):
        url = reverse(get_individual_mme_matches, args=[SUBMISSION_GUID])
        self.check_collaborator_login(url)

        # test MME disabled project
        invalid_url = reverse(get_individual_mme_matches, args=[INVALID_PROJECT_SUBMISSION_GUID])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'mmeResultsByGuid', 'genesById', 'savedVariantsByGuid', 'variantTagsByGuid',
            'variantNotesByGuid', 'variantFunctionalDataByGuid', 'mmeContactNotes',
            'mmeSubmissionsByGuid',
        })

        self.assertSetEqual(
            set(response_json['mmeResultsByGuid'].keys()), {'MR0007228_VCGS_FAM50_156', 'MR0004688_RGP_105_3', RESULT_STATUS_GUID}
        )
        self.assertSetEqual({r['submissionGuid'] for r in response_json['mmeResultsByGuid'].values()}, {SUBMISSION_GUID})

        self.assertDictEqual(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID], PARSED_RESULT)
        self.assertFalse('originatingSubmission' in response_json['mmeResultsByGuid']['MR0007228_VCGS_FAM50_156'])
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {SUBMISSION_GUID: {
            'submissionGuid': SUBMISSION_GUID,
            'individualGuid': INDIVIDUAL_GUID,
            'createdDate': '2018-05-23T09:07:49.719Z',
            'lastModifiedDate': '2018-05-23T09:07:49.719Z',
            'deletedDate': None,
            'contactName': 'Sam Baxter',
            'contactHref': 'mailto:matchmaker@broadinstitute.org,test_user@broadinstitute.org',
            'submissionId': 'NA19675_1_01',
            'phenotypes': [
                {'id': 'HP:0001252', 'label': 'Muscular hypotonia', 'observed': 'yes'},
                {'id': 'HP:0001263', 'label': 'Global developmental delay', 'observed': 'no'},
                {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
            ],
            'geneVariants': [{
                'geneId': 'ENSG00000135953',
                'variantGuid': 'SV0000001_2103343353_r0390_100',
            }],
        }})

        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000186092', 'ENSG00000233750', 'ENSG00000223972', 'ENSG00000135953'}
        )
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000001_2103343353_r0390_100', 'SV0059957_11562437_f019313_1', 'SV0059956_11560662_f019313_1'}
        )
        self.assertDictEqual(response_json['mmeContactNotes'], {})

        # users should see originating query for results if the have correct project permissions
        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID], PARSED_RESULT)
        self.assertDictEqual(response_json['mmeResultsByGuid']['MR0007228_VCGS_FAM50_156']['originatingSubmission'], {
            'originatingSubmissionGuid': 'MS000018_P0004517',
            'familyGuid': 'F000014_14',
            'projectGuid': 'R0004_non_analyst_project',
        })

        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID], PARSED_RESULT)
        self.assertFalse('originatingSubmission' in response_json['mmeResultsByGuid']['MR0007228_VCGS_FAM50_156'])

    @mock.patch('matchmaker.views.matchmaker_api.MME_NODES_BY_NAME', MOCK_NODES_BY_NAME)
    def test_get_mme_nodes(self):
        url = reverse(get_mme_nodes)
        self.check_require_login(url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'mmeNodes': ['Node A', 'Node B']})

    @mock.patch('seqr.utils.communication_utils.SLACK_TOKEN', MOCK_SLACK_TOKEN)
    @mock.patch('matchmaker.views.matchmaker_api.MME_NODES_BY_NAME', MOCK_NODES_BY_NAME)
    @mock.patch('seqr.utils.middleware.logger')
    @mock.patch('seqr.utils.communication_utils.logger')
    @mock.patch('seqr.utils.communication_utils.Slacker')
    @mock.patch('matchmaker.views.matchmaker_api.logger')
    @mock.patch('matchmaker.views.matchmaker_api.EmailMessage')
    @responses.activate
    def test_search_individual_mme_matches(self, mock_email, mock_logger, mock_slacker, mock_communication_logger, mock_exception_logger):
        mock_slacker.return_value.chat.post_message.side_effect = ValueError('Unable to connect to slack')
        mock_email.return_value.send.side_effect = Exception('Email error')

        local_search_url = reverse(search_local_individual_mme_matches, args=[SUBMISSION_GUID])
        self.check_collaborator_login(local_search_url)

        responses.add(responses.POST, 'http://node_a.com/match', body='Failed request', status=400)
        invalid_results = [INVALID_NEW_MATCH_JSON, INVALID_FEATURES_NEW_MATCH_JSON, INVALID_GENE_NEW_MATCH_JSON]
        results = [NEW_MATCH_JSON, MISMATCHED_GENE_NEW_MATCH_JSON] + invalid_results
        responses.add(responses.POST, 'http://node_b.mme.org/api', status=200, json={'results': results})

        # Test successful local match search
        response = self.client.get(local_search_url)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'mmeResultsByGuid', 'genesById', 'mmeContactNotes', 'incomingQueryGuid',
        })
        incoming_query_guid = response_json['incomingQueryGuid']

        self.assertEqual(len(response_json['mmeResultsByGuid']), 2)
        self.assertSetEqual({r['submissionGuid'] for r in response_json['mmeResultsByGuid'].values()}, {SUBMISSION_GUID})
        self.assertTrue(RESULT_STATUS_GUID in response_json['mmeResultsByGuid'])
        new_internal_match_guid = next(k for k in response_json['mmeResultsByGuid'].keys() if k != RESULT_STATUS_GUID)
        self.assertFalse(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID]['matchStatus']['matchRemoved'])
        self.assertDictEqual(response_json['mmeResultsByGuid'][new_internal_match_guid], {
            'id': 'P0004517',
            'score': 0.425,
            'patient': {
                'genomicFeatures': [{
                    'gene': {'id': 'ENSG00000135953'},
                    'variant': {
                        'referenceName': '1',
                        'start': 248367227,
                        'referenceBases': 'TC',
                        'alternateBases': 'T',
                        'assembly': 'GRCh38',
                    },
                    'zygosity': 1,
                }],
                'features': None,
                'contact': {
                    'href': 'mailto:matchmaker@broadinstitute.org',
                    'name': 'Sam Baxter',
                    'institution': 'Broad Center for Mendelian Genomics'
                },
                'id': 'P0004517',
                'label': 'P0004517',
                'species': 'NCBITaxon:9606',
                'sex': 'FEMALE',
            },
            'submissionGuid': SUBMISSION_GUID,
            'phenotypes': [],
            'geneVariants': [
                {
                    'geneId': 'ENSG00000135953',
                    'variant': {
                        'chrom': '1',
                        'pos': 248367227,
                        'ref': 'TC',
                        'alt': 'T',
                        'end': None,
                        'genomeVersion': 'GRCh38',
                    }
                }
            ],
            'matchStatus': {
                'matchmakerResultGuid': new_internal_match_guid,
                'comments': None,
                'weContacted': False,
                'hostContacted': False,
                'deemedIrrelevant': False,
                'flagForAnalysis': False,
                'matchRemoved': False,
                'createdDate': mock.ANY,
            },
        })

        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000135953', 'ENSG00000240361', 'ENSG00000223972'}
        )
        self.assertDictEqual(response_json['mmeContactNotes'], {})

        # Test external matches
        node_a_match_url = reverse(search_individual_mme_matches, args=[SUBMISSION_GUID, 'Node A'])
        response = self.client.get(node_a_match_url, {'incomingQueryGuid': incoming_query_guid})
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'],  ['Error searching in Node A: Failed request (400)'])

        node_b_match_url = reverse(search_individual_mme_matches, args=[SUBMISSION_GUID, 'Node B'])
        response = self.client.get(node_b_match_url, {'incomingQueryGuid': incoming_query_guid})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid', 'genesById', 'mmeContactNotes'})

        self.assertEqual(len(response_json['mmeResultsByGuid']), 1)
        new_result_guid = next(k for k in response_json['mmeResultsByGuid'].keys())
        self.assertDictEqual(response_json['mmeResultsByGuid'][new_result_guid], PARSED_NEW_MATCH_JSON)
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953'})
        # non-analyst users can't see contact notes
        self.assertDictEqual(response_json['mmeContactNotes'], {'st georges, university of london': {}})

        # Test notifications and removed result cleanup
        finalize_search_url = reverse(finalize_mme_search, args=[SUBMISSION_GUID])
        response = self.client.get(finalize_search_url, {'incomingQueryGuid': incoming_query_guid})

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid'})
        self.assertDictEqual(response_json['mmeResultsByGuid'], {
            'MR0004688_RGP_105_3': {'matchStatus': mock.ANY},
            'MR0007228_VCGS_FAM50_156': None,
        })
        self.assertTrue(response_json['mmeResultsByGuid']['MR0004688_RGP_105_3']['matchStatus']['matchRemoved'])

        #  Test removed match is deleted
        self.assertEqual(MatchmakerResult.objects.filter(guid='MR0007228_VCGS_FAM50_156').count(), 0)

        # Test proxy calls
        self.assertEqual(len(responses.calls), 2)
        expected_patient_body = {
            'patient': {
                'id': 'NA19675_1_01',
                'label': 'NA19675_1',
                'contact': {
                    'href': 'mailto:matchmaker@broadinstitute.org,test_user@broadinstitute.org',
                    'name': 'Sam Baxter',
                    'institution': 'Broad Center for Mendelian Genomics',
                },
                'species': 'NCBITaxon:9606',
                'features': [
                    {'id': 'HP:0001252', 'observed': 'yes'},
                    {'id': 'HP:0001263', 'observed': 'no'},
                    {'id': 'HP:0012469', 'observed': 'yes'}
                ],
                'genomicFeatures': [{
                    'gene': {'id': 'ENSG00000135953'},
                    'variant': {
                        'referenceName': '21', 'start':  3343353, 'assembly': 'GRCh37',
                        'alternateBases': 'G', 'referenceBases': 'GAGA',
                    },
                    'zygosity': 1
                }],
                'sex': 'MALE',
            },
        }
        expected_body = json.dumps(dict(_disclaimer=MME_DISCLAIMER, **expected_patient_body))

        self.assertEqual(responses.calls[0].request.url, 'http://node_a.com/match')
        self.assertEqual(responses.calls[0].request.headers['X-Auth-Token'], 'abc')
        self.assertEqual(responses.calls[1].request.url, 'http://node_b.mme.org/api')
        self.assertEqual(responses.calls[1].request.headers['X-Auth-Token'], 'xyz')
        for call in responses.calls:
            self.assertEqual(call.request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
            self.assertEqual(call.request.headers['Content-Type'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
            self.assertEqual(call.request.headers['Content-Language'], 'en-US')
            self.assertEqual(call.request.body, expected_body)

        # Test notification
        message = """
    A search from a seqr user from project 1kg project n\xe5me with uni\xe7\xf8de individual NA19675_1 had the following new match(es):
    
     - From Sam Baxter at institution Broad Center for Mendelian Genomics with genes RP11.

 - From Reza Maroofian at institution St Georges, University of London with genes RP11 with phenotypes HP:0012469 (Infantile spasms).
    
    /project/R0001_1kg/family_page/F000001_1/matchmaker_exchange
    """
        self.assertEqual(mock_slacker.call_count, 3)
        mock_slacker.assert_called_with(MOCK_SLACK_TOKEN)
        slack_kwargs = {'as_user': False, 'icon_emoji': ':beaker:', 'username': 'Beaker (engineering-minion)'}
        alert_a_slack_message = 'Error searching in Node A: Failed request (400)\n```{}```'.format(
            json.dumps(expected_patient_body, indent=2))
        alert_b_slack_message = 'Error searching in Node B: Received invalid results for NA19675_1\n```{}```'.format(
            json.dumps(invalid_results, indent=2))
        mock_slacker.return_value.chat.post_message.assert_has_calls([
            mock.call('matchmaker_alerts', alert_a_slack_message, **slack_kwargs),
            mock.call('matchmaker_alerts', alert_b_slack_message, **slack_kwargs),
            mock.call('matchmaker_seqr_match', message, **slack_kwargs),
        ])
        mock_communication_logger.error.assert_has_calls([
            mock.call(
                'Slack error: Unable to connect to slack: Original message in channel ({}) - {}'.format(
                    'matchmaker_alerts', alert_a_slack_message
            )),
            mock.call(
                'Slack error: Unable to connect to slack: Original message in channel ({}) - {}'.format(
                    'matchmaker_alerts', alert_b_slack_message
                )),
            mock.call(
                'Slack error: Unable to connect to slack: Original message in channel ({}) - {}'.format(
                    'matchmaker_seqr_match', message
                )),
        ])
        mock_email.assert_called_with(
            subject='New matches found for MME submission NA19675_1 (project: 1kg project n\xe5me with uni\xe7\xf8de)',
            body=message,
            to=['test_user@broadinstitute.org'],
            from_email='matchmaker@broadinstitute.org')
        mock_email.return_value.send.assert_called()

        mock_logger.error.assert_called_with(
            'Unable to create notification for new MME match: Email error', self.collaborator_user)
        mock_exception_logger.warning.assert_called_with(
            'Error searching in Node A: Failed request (400)', self.collaborator_user, detail=expected_patient_body,
            http_request_json=mock.ANY, traceback=mock.ANY, request_body=mock.ANY,
        )
        mock_logger.warning.assert_has_calls([
            mock.call('Error searching in Node B: Received invalid results for NA19675_1', self.collaborator_user, detail=invalid_results),
            mock.call('Received 1 invalid matches from Node B', self.collaborator_user),
        ])
        mock_logger.info.assert_has_calls([mock.call(message, self.collaborator_user) for message in [
            'Found 2 matches in Broad MME for NA19675_1_01 (1 new)',
            'Found 5 matches from Node B',
            'Found 1 matches in Node B for NA19675_1_01 (1 new)',
            'Found 3 total matches for NA19675_1_01 (2 new)',
            'Removed 2 old matches for NA19675_1_01',
        ]])

        # Test new result model created
        result_model = MatchmakerResult.objects.get(guid=new_result_guid)
        self.assertDictEqual(result_model.result_data, NEW_MATCH_JSON)

        # The results for internal submissions should link to one another
        internal_result = MatchmakerResult.objects.get(guid=new_internal_match_guid)
        self.assertEqual(internal_result.submission.guid, SUBMISSION_GUID)
        self.assertEqual(internal_result.originating_submission.guid, 'MS000018_P0004517')
        matched_result = MatchmakerResult.objects.get(submission__guid='MS000018_P0004517')
        self.assertEqual(matched_result.originating_submission.guid, SUBMISSION_GUID)

        # analyst users should see contact notes
        self.login_analyst_user()
        results.append(REMOVED_MATCH_JSON)
        responses.replace(responses.POST, 'http://node_b.mme.org/api', status=200, json={'results': results})
        response = self.client.get(node_b_match_url, {'incomingQueryGuid': incoming_query_guid})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['mmeContactNotes'], {
            'st georges, university of london': {
                'institution': 'st georges, university of london',
                'comments': 'Some additional data about this institution',
            }})
        # if previously removed matches have been re-matched, they should no longer be marked as removed
        self.assertFalse(response_json['mmeResultsByGuid']['MR0004688_RGP_105_3']['matchStatus']['matchRemoved'])

        self.login_manager()
        response = self.client.get(local_search_url)
        result_response = response.json()['mmeResultsByGuid']
        # users should see originating query for results if the have correct project permissions
        self.assertDictEqual(result_response[new_internal_match_guid]['originatingSubmission'], {
            'originatingSubmissionGuid': 'MS000018_P0004517',
            'familyGuid': 'F000014_14',
            'projectGuid': 'R0004_non_analyst_project',
        })

    @mock.patch('matchmaker.views.matchmaker_api.logger')
    def test_update_mme_submission(self, mock_logger):
        url = reverse(update_mme_submission)
        self.check_collaborator_login(url, request_data=SUBMISSION_DATA)

        # Test invalid inputs
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Genotypes or phenotypes are required')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'geneVariants': [{'pos': 123345}],
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Gene and variant IDs are required for genomic features')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'geneVariants': [
                {'geneId': 'ENSG00000235249', 'variantGuid': 'SV0000002_1248367227_r0390_100'},
                {'geneId': 'ENSG00000135953', 'variantGuid': 'SV0000002_1248367227_r0390_100'},
                {'geneId': 'ENSG00000235249', 'variantGuid': 'SV0000003_1248367227_r0390_100'},
                {'geneId': 'ENSG00000135953', 'variantGuid': 'SV0000003_1248367227_r0390_100'},
                {'geneId': 'ENSG00000235249', 'variantGuid': 'SV0000004_1248367227_r0390_100'},
                {'geneId': 'ENSG00000135953', 'variantGuid': 'SV0000004_1248367227_r0390_100'},
            ],
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'No more than 5 variants can be submitted per individual')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'phenotypes': [{'id': 'HP:0012469'}]
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Individual is required for a new submission')

        # Test successful creation
        response = self.client.post(url, content_type='application/json', data=json.dumps(SUBMISSION_DATA))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeSubmissionsByGuid', 'individualsByGuid'})

        self.assertEqual(len(response_json['mmeSubmissionsByGuid']), 1)
        new_submission_guid = next(iter(response_json['mmeSubmissionsByGuid']))
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {new_submission_guid: {
            'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
            'submissionGuid': new_submission_guid,
            'createdDate': mock.ANY,
            'lastModifiedDate': mock.ANY,
            'deletedDate': None,
            'contactName': 'PI',
            'contactHref': 'mailto:test@broadinstitute.org',
            'submissionId': NO_SUBMISSION_INDIVIDUAL_GUID,
            'phenotypes': [
                {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
            ],
            'geneVariants': [{
                'geneId': 'ENSG00000135953',
                'variantGuid': 'SV0000002_1248367227_r0390_100',
            }, {
                'geneId': 'ENSG00000235249',
                'variantGuid': 'SV0000002_1248367227_r0390_100',
            }],
        }})
        self.assertEqual(
            response_json['mmeSubmissionsByGuid'][new_submission_guid]['createdDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        self.assertEqual(
            response_json['mmeSubmissionsByGuid'][new_submission_guid]['lastModifiedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )

        self.assertDictEqual(response_json['individualsByGuid'], {NO_SUBMISSION_INDIVIDUAL_GUID: {
            'mmeSubmissionGuid': new_submission_guid,
        }})

        # test model creation
        submission = MatchmakerSubmission.objects.get(guid=new_submission_guid)
        self.assertEqual(submission.individual.guid, NO_SUBMISSION_INDIVIDUAL_GUID)
        self.assertEqual(submission.submission_id, NO_SUBMISSION_INDIVIDUAL_GUID)
        self.assertEqual(submission.label, 'HG00733')
        self.assertEqual(submission.contact_name, 'PI')
        self.assertIsNone(submission.deleted_date)
        self.assertListEqual(submission.features, SUBMISSION_DATA['phenotypes'])
        submission_genes = submission.matchmakersubmissiongenes_set.all()
        self.assertEqual(submission_genes.count(), 2)
        self.assertSetEqual(
            set(submission_genes.values_list('gene_id', flat=True)), {'ENSG00000135953', 'ENSG00000235249'})

        # Test successful update
        url = reverse(update_mme_submission, args=[new_submission_guid])
        update_body = {
            'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
            'contactHref': 'mailto:matchmaker@broadinstitute.org',
            'contactName': 'Test Name',
            'phenotypes': [
                {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'no'},
                {'id': 'HP:0002017', 'label': 'Nausea and vomiting', 'observed': 'yes'},
            ],
        }
        response = self.client.post(url, content_type='application/json', data=json.dumps(update_body))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeSubmissionsByGuid'})
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {new_submission_guid: {
            'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
            'submissionGuid': new_submission_guid,
            'createdDate': mock.ANY,
            'lastModifiedDate': mock.ANY,
            'deletedDate': None,
            'contactName': 'Test Name',
            'contactHref': 'mailto:matchmaker@broadinstitute.org',
            'submissionId': NO_SUBMISSION_INDIVIDUAL_GUID,
            'phenotypes': [
                {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'no'},
                {'id': 'HP:0002017', 'label': 'Nausea and vomiting', 'observed': 'yes'},
            ],
            'geneVariants': [],
        }})
        self.assertEqual(
            response_json['mmeSubmissionsByGuid'][new_submission_guid]['createdDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        self.assertEqual(
            response_json['mmeSubmissionsByGuid'][new_submission_guid]['lastModifiedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        self.assertNotEqual(
            response_json['mmeSubmissionsByGuid'][new_submission_guid]['createdDate'],
            response_json['mmeSubmissionsByGuid'][new_submission_guid]['lastModifiedDate']
        )

        # test model update
        submission = MatchmakerSubmission.objects.get(guid=new_submission_guid)
        self.assertEqual(submission.contact_name, 'Test Name')
        self.assertEqual(submission.contact_href, 'mailto:matchmaker@broadinstitute.org')
        self.assertEqual(submission.label, 'HG00733')
        self.assertIsNone(submission.deleted_date)
        self.assertListEqual(submission.features, update_body['phenotypes'])
        submission_genes = submission.matchmakersubmissiongenes_set.all()
        self.assertEqual(submission_genes.count(), 0)

    def test_delete_mme_submission(self):
        url = reverse(delete_mme_submission, args=[SUBMISSION_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        today = datetime.today().strftime('%Y-%m-%d')
        self.assertEqual(response_json['mmeSubmissionsByGuid'][SUBMISSION_GUID]['deletedDate'][:10], today)

        self.assertEqual(MatchmakerResult.objects.filter(submission__guid=SUBMISSION_GUID).count(), 2)
        submission = MatchmakerSubmission.objects.get(guid=SUBMISSION_GUID)
        self.assertEqual(submission.deleted_date.strftime('%Y-%m-%d'), today)
        self.assertEqual(submission.deleted_by, self.collaborator_user)
        self.assertEqual(submission.matchmakersubmissiongenes_set.count(), 0)

        # Test do not delete if already deleted
        response = self.client.post(url)
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.reason_phrase, 'Matchmaker submission has already been deleted for NA19675_1')

        update_url = reverse(update_mme_submission, args=[SUBMISSION_GUID])
        response = self.client.post(update_url, content_type='application/json',  data=json.dumps({
            'geneVariants': [{'geneId': 'ENSG00000235249', 'variantGuid': 'SV0000001_2103343353_r0390_100'}]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {SUBMISSION_GUID: {
            'individualGuid': INDIVIDUAL_GUID,
            'submissionGuid': SUBMISSION_GUID,
            'createdDate': '2018-05-23T09:07:49.719Z',
            'lastModifiedDate': mock.ANY,
            'deletedDate': None,
            'contactName': 'Sam Baxter',
            'contactHref': 'mailto:matchmaker@broadinstitute.org,test_user@broadinstitute.org',
            'submissionId': 'NA19675_1_01',
            'phenotypes': [],
            'geneVariants': [{'geneId': 'ENSG00000235249', 'variantGuid': 'SV0000001_2103343353_r0390_100'}],
        }})
        self.assertEqual(response_json['mmeSubmissionsByGuid'][SUBMISSION_GUID]['lastModifiedDate'][:10], today)

        submission = MatchmakerSubmission.objects.get(guid=SUBMISSION_GUID)
        self.assertIsNone(submission.deleted_date)
        self.assertIsNone(submission.deleted_by)
        self.assertEqual(submission.matchmakersubmissiongenes_set.count(), 1)

    def test_update_mme_result_status(self):
        url = reverse(update_mme_result_status, args=[RESULT_STATUS_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'matchmakerResultGuid': RESULT_STATUS_GUID,
            'comments': 'test comment',
            'deemedIrrelevant': False,
            'flagForAnalysis': True,
            'originatingSubmission': {'originatingSubmissionGuid': 'MS000016_P0004515'},
        }))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {'mmeResultsByGuid': {RESULT_STATUS_GUID: {
            'matchStatus': {
                'matchmakerResultGuid': RESULT_STATUS_GUID,
                'comments': 'test comment',
                'weContacted': False,
                'hostContacted': True,
                'deemedIrrelevant': False,
                'flagForAnalysis': True,
                'matchRemoved': False,
                'createdDate': '2019-02-12T18:43:56.358Z',
            },
        }}})

        result_model = MatchmakerResult.objects.get(guid=RESULT_STATUS_GUID)
        self.assertEqual(result_model.comments, 'test comment')

    @mock.patch('matchmaker.views.matchmaker_api.EmailMessage')
    def test_send_mme_contact_email(self, mock_email):
        url = reverse(send_mme_contact_email, args=[RESULT_STATUS_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'to': 'test@test.com , other_test@gmail.com',
            'body': 'some email content',
            'subject': 'some email subject'
        }))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {'mmeResultsByGuid': {RESULT_STATUS_GUID: {
            'matchStatus': {
                'matchmakerResultGuid': RESULT_STATUS_GUID,
                'comments': 'AMBRA1 c.2228G>C p.(Ser743Thr) missense variant. Maternally inherited, both have epilepsy',
                'weContacted': True,
                'hostContacted': True,
                'deemedIrrelevant': True,
                'flagForAnalysis': False,
                'matchRemoved': False,
                'createdDate': '2019-02-12T18:43:56.358Z',
            },
        }}})

        mock_email.assert_called_with(
            subject='some email subject',
            body='some email content',
            to=['test@test.com', 'other_test@gmail.com'],
            from_email='matchmaker@broadinstitute.org')
        mock_email.return_value.send.assert_called()

        mock_email.return_value.send.side_effect = EmailException()
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'to': 'test@test.com , other_test@gmail.com',
            'body': 'some email content',
            'subject': 'some email subject'
        }))

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.reason_phrase, 'email error')
        self.assertDictEqual(response.json(), {'error': 'email error'})

        mock_email.return_value.send.side_effect = EmailException(json={'error': 'no connection'})
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'to': 'test@test.com , other_test@gmail.com',
            'body': 'some email content',
            'subject': 'some email subject'
        }))

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.reason_phrase, 'email error')
        self.assertDictEqual(response.json(), {'error': 'no connection'})

    def test_update_mme_contact_note(self):
        url = reverse(update_mme_contact_note, args=['GeneDx'])
        self.check_analyst_login(url)

        # Test create
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'institution': 'GeneDx',
            'comments': 'test comment',
        }))

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'mmeContactNotes': {'genedx': {
            'institution': 'genedx',
            'comments': 'test comment',
        }}})

        models = MatchmakerContactNotes.objects.filter(institution='genedx')
        self.assertEqual(models.count(), 1)
        self.assertEqual(models.first().comments, 'test comment')

        # Test update
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'institution': 'GeneDx',
            'comments': 'test comment update',
        }))

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'mmeContactNotes': {'genedx': {
            'institution': 'genedx',
            'comments': 'test comment update',
        }}})

        models = MatchmakerContactNotes.objects.filter(institution='genedx')
        self.assertEqual(models.count(), 1)
        self.assertEqual(models.first().comments, 'test comment update')

    def test_update_mme_project_contact(self):
        url = reverse(update_mme_project_contact, args=['R0003_test'])
        self.check_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Contact is required'})

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'contact': 'UDNCC@hms.harvard.edu'
        }))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {'mmeSubmissionsByGuid': {'MS000015_na20885': mock.ANY}})

        updated_submission = MatchmakerSubmission.objects.get(guid='MS000015_na20885')
        self.assertEqual(updated_submission.contact_href, 'mailto:matchmaker@broadinstitute.org,UDNCC@hms.harvard.edu')

        # test submission already with contact not updated
        existing_submission = MatchmakerSubmission.objects.get(guid='MS000016_P0004515')
        self.assertEqual(existing_submission.contact_href, 'mailto:UDNCC@hms.harvard.edu,matchmaker@phenomecentral.org')
