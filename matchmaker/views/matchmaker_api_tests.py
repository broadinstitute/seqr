import json
import responses
import mock

from copy import deepcopy
from datetime import datetime
from django.urls.base import reverse

from matchmaker.models import MatchmakerResult, MatchmakerContactNotes
from matchmaker.matchmaker_utils import MME_DISCLAIMER
from matchmaker.views.matchmaker_api import get_individual_mme_matches, search_individual_mme_matches, \
    update_mme_submission, delete_mme_submission, update_mme_result_status, send_mme_contact_email, \
    update_mme_contact_note
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
        'alt': 'C',
        'ref': 'CCACT',
        'chrom': '14',
        'pos': 77027549,
        'genomeVersion': '38',
        'numAlt': 2,
    }, {
        'geneId': 'ENSG00000235249',
        'alt': None,
        'ref': None,
        'chrom': '14',
        'pos': 77027623,
        'end': 77028137,
        'genomeVersion': '38',
        'numAlt': -1,
        'cn': 3,
    }],
}

NEW_MATCH_JSON = {
    "score": {
        "patient": 0.92
    },
    "patient": {
        "genomicFeatures": [
            {
                "gene": {
                    "id": "OR4F29"
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

PARSED_NEW_MATCH_JSON = {
    'id': '33845',
    'score': 0.92,
    'patient': NEW_MATCH_JSON['patient'],
    'submissionGuid': SUBMISSION_GUID,
    'phenotypes': [{'observed': 'yes', 'id': 'HP:0012469', 'label': 'Infantile spasms'}],
    'geneVariants': [{'geneId': 'ENSG00000235249'}],
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
INVALID_NEW_MATCH_JSON['patient']['genomicFeatures'][0]['gene'] = {}
INVALID_NEW_MATCH_JSON['patient']['id'] = '123'

MISMATCHED_GENE_NEW_MATCH_JSON = deepcopy(NEW_MATCH_JSON)
MISMATCHED_GENE_NEW_MATCH_JSON['patient']['genomicFeatures'][0]['gene']['id'] = 'ENSG00000227232'
MISMATCHED_GENE_NEW_MATCH_JSON['patient']['id'] = '987'

MOCK_SLACK_TOKEN = 'xoxp-123'


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
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    def test_get_individual_mme_matches(self):
        url = reverse(get_individual_mme_matches, args=[SUBMISSION_GUID])
        self.check_collaborator_login(url)

        # test MME disabled project
        invalid_url = reverse(get_individual_mme_matches, args=[INVALID_PROJECT_SUBMISSION_GUID])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Matchmaker is not enabled')

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'savedVariantsByGuid', 'variantTagsByGuid',
            'variantNotesByGuid', 'variantFunctionalDataByGuid', 'mmeContactNotes',
            'mmeSubmissionsByGuid',
        })

        self.assertSetEqual(
            set(response_json['mmeResultsByGuid'].keys()), {'MR0007228_VCGS_FAM50_156', 'MR0004688_RGP_105_3', RESULT_STATUS_GUID}
        )
        self.assertDictEqual(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID], {
            'id': 'P0004515',
            'score': 0.5706712016939723,
            'submissionGuid': SUBMISSION_GUID,
            'patient': {
                'genomicFeatures': [
                    {'gene': {'id': 'OR4F5'}},
                    {'gene': {'id': 'CICP27'}},
                    {'gene': {'id': 'DDX11L1'}},
                ],
                'contact': {
                    'href': 'mailto:UDNCC@hms.harvard.edu,matchmaker@phenomecentral.org',
                    'name': 'Baylor UDN Clinical Site'
                },
                'id': 'P0004515',
                'features': [
                    {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'},
                    {'id': 'HP:0003273', 'label': 'Hip contracture', 'observed': 'no'},
                ],
            },
            'phenotypes': [
                {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'},
                {'id': 'HP:0003273', 'label': 'Hip contracture', 'observed': 'no'},
            ],
            'geneVariants': [
                {'geneId': 'ENSG00000186092'},
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
        })
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {SUBMISSION_GUID: {
            'mmeResultGuids': mock.ANY,
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
                'geneId': 'ENSG00000186092',
                'alt': 'C',
                'ref': 'CCACT',
                'chrom': '14',
                'pos': 77027549,
                'end': 77027548,
                'genomeVersion': 'GRCh38',
            }],
        }})
        self.assertDictEqual(response_json['individualsByGuid'], {INDIVIDUAL_GUID: {
            'mmeSubmissionGuid': SUBMISSION_GUID,
        }})
        self.assertSetEqual(
            set(response_json['mmeSubmissionsByGuid'][SUBMISSION_GUID]['mmeResultGuids']),
            {'MR0007228_VCGS_FAM50_156', 'MR0004688_RGP_105_3', RESULT_STATUS_GUID})

        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000186092', 'ENSG00000233750', 'ENSG00000223972', 'ENSG00000135953'}
        )
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000001_2103343353_r0390_100', 'SV0059957_11562437_f019313_1', 'SV0059956_11560662_f019313_1'}
        )
        self.assertDictEqual(response_json['mmeContactNotes'], {})

        # staff users should see originating query for results
        self.login_staff_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID]['originatingSubmission'], {
            'originatingSubmissionGuid': 'MS000016_P0004515',
            'familyGuid': 'F000012_12',
            'projectGuid': 'R0003_test',
        })
        self.assertFalse('originatingSubmission' in response_json['mmeResultsByGuid']['MR0007228_VCGS_FAM50_156'])

    @mock.patch('seqr.utils.communication_utils.SLACK_TOKEN', MOCK_SLACK_TOKEN)
    @mock.patch('seqr.utils.communication_utils.Slacker')
    @mock.patch('matchmaker.views.matchmaker_api.EmailMessage')
    @mock.patch('matchmaker.views.matchmaker_api.MME_NODES')
    @responses.activate
    def test_search_individual_mme_matches(self, mock_nodes, mock_email, mock_slacker):
        url = reverse(search_individual_mme_matches, args=[SUBMISSION_GUID])
        self.check_collaborator_login(url)

        responses.add(responses.POST, 'http://node_a.com/match', body='Failed request', status=400)
        responses.add(responses.POST, 'http://node_b.mme.org/api', status=200, json={
            'results': [NEW_MATCH_JSON, INVALID_NEW_MATCH_JSON, MISMATCHED_GENE_NEW_MATCH_JSON]
        })

        # Test invalid inputs
        mock_nodes.values.return_value = []
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'No external MME nodes are configured')

        mock_nodes.values.return_value = [{'name': 'My node'}]
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'No external MME nodes are configured')

        # Test successful search
        mock_nodes.values.return_value = [
            {'name': 'My node'},
            {'name': 'Node A', 'token': 'abc', 'url': 'http://node_a.com/match'},
            {'name': 'Node B', 'token': 'xyz', 'url': 'http://node_b.mme.org/api'},
        ]
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'mmeContactNotes', 'mmeSubmissionsByGuid',
        })

        self.assertEqual(len(response_json['mmeResultsByGuid']), 3)
        self.assertTrue(RESULT_STATUS_GUID in response_json['mmeResultsByGuid'])
        self.assertTrue('MR0004688_RGP_105_3' in response_json['mmeResultsByGuid'])
        new_result_guid = next(k for k in response_json['mmeResultsByGuid'].keys()
                               if k not in {'MR0004688_RGP_105_3', RESULT_STATUS_GUID})

        self.assertDictEqual(response_json['mmeResultsByGuid'][new_result_guid], PARSED_NEW_MATCH_JSON)
        self.assertTrue(response_json['mmeResultsByGuid']['MR0004688_RGP_105_3']['matchStatus']['matchRemoved'])
        self.assertFalse(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID]['matchStatus']['matchRemoved'])
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {SUBMISSION_GUID: {
            'mmeResultGuids': mock.ANY,
            'individualGuid': INDIVIDUAL_GUID,
            'submissionGuid': SUBMISSION_GUID,
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
                'geneId': 'ENSG00000186092',
                'alt': 'C',
                'ref': 'CCACT',
                'chrom': '14',
                'pos': 77027549,
                'end': 77027548,
                'genomeVersion': 'GRCh38',
            }],
        }})
        self.assertDictEqual(response_json['individualsByGuid'], {INDIVIDUAL_GUID: {
            'mmeSubmissionGuid': SUBMISSION_GUID,
        }})
        self.assertSetEqual(
            set(response_json['mmeSubmissionsByGuid'][SUBMISSION_GUID]['mmeResultGuids']),
            set(response_json['mmeResultsByGuid'].keys()))

        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000186092', 'ENSG00000233750', 'ENSG00000223972', 'ENSG00000235249'}
        )
        # non-staff users can't see contact notes
        self.assertDictEqual(response_json['mmeContactNotes'], {'st georges, university of london': {}})

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
                    'gene': {'id': 'ENSG00000186092'},
                    'variant': {
                        'end': 77027548, 'start': 77027549, 'assembly': 'GRCh38', 'referenceName': '14',
                        'alternateBases': 'C', 'referenceBases': 'CCACT',
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
    
     - From Reza Maroofian at institution St Georges, University of London with genes OR4F29 with phenotypes HP:0012469 (Infantile spasms).
    
    /project/R0001_1kg/family_page/F000001_1/matchmaker_exchange
    """
        self.assertEqual(mock_slacker.call_count, 2)
        mock_slacker.assert_called_with(MOCK_SLACK_TOKEN)
        mock_slacker.return_value.chat.post_message.assert_has_calls([
            mock.call(
                'matchmaker_alerts', 'Error searching in Node A: Failed request (400)\n(Patient info: {})'.format(
                    json.dumps(expected_patient_body)
                ), as_user=False, icon_emoji=':beaker:', username='Beaker (engineering-minion)'),
            mock.call('matchmaker_seqr_match', message,
                      as_user=False, icon_emoji=':beaker:', username='Beaker (engineering-minion)'),
        ])
        mock_email.assert_called_with(
            subject='New matches found for MME submission NA19675_1 (project: 1kg project n\xe5me with uni\xe7\xf8de)',
            body=message,
            to=['test_user@broadinstitute.org'],
            from_email='matchmaker@broadinstitute.org')
        mock_email.return_value.send.assert_called()

        # Test new result model created
        result_model = MatchmakerResult.objects.get(guid=new_result_guid)
        self.assertDictEqual(result_model.result_data, NEW_MATCH_JSON)

        # staff users should see contact notes
        self.login_staff_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['mmeContactNotes'], {
            'st georges, university of london': {
                'institution': 'st georges, university of london',
                'comments': 'Some additional data about this institution',
            }})

    @mock.patch('matchmaker.views.matchmaker_api.EmailMessage', Exception('Email error'))
    @mock.patch('matchmaker.views.matchmaker_api.MME_NODES')
    @responses.activate
    def test_update_mme_submission(self, mock_mme_nodes):
        responses.add(responses.POST, 'http://node_a.com/match', status=200, json={'results': [NEW_MATCH_JSON]})
        mock_mme_nodes.values.return_value = [{'name': 'Node A', 'token': 'abc', 'url': 'http://node_a.com/match'}]

        url = reverse(update_mme_submission)
        self.check_collaborator_login(url, request_data=SUBMISSION_DATA)

        # Test invalid inputs
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Genotypes or phentoypes are required')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'geneVariants': [{'pos': 123345}],
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Gene id is required for genomic features')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'phenotypes': [{'id': 'HP:0012469'}]
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Individual is required for a new submission')

        # Test successful creation
        response = self.client.post(url, content_type='application/json', data=json.dumps(SUBMISSION_DATA))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'mmeContactNotes', 'mmeSubmissionsByGuid',
        })

        self.assertEqual(len(response_json['mmeSubmissionsByGuid']), 1)
        new_submission_guid = next(iter(response_json['mmeSubmissionsByGuid']))
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {new_submission_guid: {
            'mmeResultGuids': list(response_json['mmeResultsByGuid'].keys()),
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
                'geneId': 'ENSG00000235249',
                'alt': 'C',
                'ref': 'CCACT',
                'chrom': '14',
                'pos': 77027549,
                'end': None,
                'genomeVersion': 'GRCh38',
            }, {
                'geneId': 'ENSG00000235249',
                'alt': None,
                'ref': None,
                'chrom': '14',
                'pos': 77027623,
                'end': 77028137,
                'genomeVersion': 'GRCh38',
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
        self.assertEqual(len(response_json['mmeResultsByGuid']), 1)
        new_match_result_guid = next(iter(response_json['mmeResultsByGuid']))
        self.assertDictEqual(response_json['mmeResultsByGuid'][new_match_result_guid], PARSED_NEW_MATCH_NEW_SUBMISSION_JSON)
        self.assertEqual(next(iter(response_json['mmeResultsByGuid'].values()))['submissionGuid'], new_submission_guid)
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000186092', 'ENSG00000235249'})
        self.assertListEqual(list(response_json['mmeContactNotes'].keys()), ['st georges, university of london'])

        # Test proxy calls
        expected_body = {
            'patient': {
                'id': NO_SUBMISSION_INDIVIDUAL_GUID,
                'label': 'HG00733',
                'contact': {'href': 'mailto:test@broadinstitute.org', 'name': 'PI',
                            'institution': 'Broad Center for Mendelian Genomics'},
                'sex': 'FEMALE',
                'species': 'NCBITaxon:9606',
                'features': [
                    {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
                ],
                'genomicFeatures': [{
                    'gene': {'id': 'ENSG00000235249'},
                    'variant': {
                        'start': 77027549,
                        'assembly': 'GRCh38',
                        'referenceName': '14',
                        'alternateBases': 'C',
                        'referenceBases': 'CCACT'
                    },
                    'zygosity': 2
                }, {
                    'gene': {'id': 'ENSG00000235249'},
                    'variant': {
                        'start': 77027623,
                        'end': 77028137,
                        'assembly': 'GRCh38',
                        'referenceName': '14',
                    },
                }],
            },
            '_disclaimer': MME_DISCLAIMER,
        }
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, 'http://node_a.com/match')
        self.assertEqual(responses.calls[0].request.headers['X-Auth-Token'], 'abc')
        self.assertEqual(responses.calls[0].request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[0].request.headers['Content-Type'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertDictEqual(json.loads(responses.calls[0].request.body), expected_body)

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
        self.assertSetEqual(set(response_json.keys()), {
            'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'mmeContactNotes', 'mmeSubmissionsByGuid',
        })

        self.assertEqual(len(response_json['mmeResultsByGuid']), 2)
        self.assertDictEqual(response_json['mmeResultsByGuid'][new_match_result_guid], PARSED_NEW_MATCH_NEW_SUBMISSION_JSON)
        new_internal_match_guid = next(k for k in response_json['mmeResultsByGuid'].keys() if k != new_match_result_guid)
        self.assertDictEqual(response_json['mmeResultsByGuid'][new_internal_match_guid], {
            'id': 'NA20885',
            'score': 0,
            'patient': {
                'genomicFeatures': [
                    {
                        'gene': {
                            'id': 'ENSG00000227232'
                        },
                        'variant': {
                            'end': 38739601,
                            'start': 38739601,
                            'assembly': 'GRCh38',
                            'referenceName': '17',
                            'alternateBases': 'A',
                            'referenceBases': 'G'
                        },
                        'zygosity': 1
                    }
                ],
                'features': [
                    {
                        'id': 'HP:0001252',
                        'label': 'Muscular hypotonia',
                        'observed': 'yes'
                    },
                    {
                        'id': 'HP:0002017',
                        'label': 'Nausea and vomiting',
                        'observed': 'yes'
                    }
                ],
                'contact': {
                    'href': 'mailto:matchmaker@broadinstitute.org',
                    'name': 'Sam Baxter',
                    'institution': 'Broad Center for Mendelian Genomics'
                },
                'id': 'NA20885',
                'label': 'NA20885',
                'species': 'NCBITaxon:9606',
                'sex': 'MALE',
            },
            'submissionGuid': new_submission_guid,
            'phenotypes': [
                {
                    "id": "HP:0001252",
                    "label": "Muscular hypotonia",
                    "observed": "yes"
                },
                {
                    "id": "HP:0002017",
                    "label": "Nausea and vomiting",
                    "observed": "yes"
                }
            ],
            'geneVariants': [
                {
                    'geneId': 'ENSG00000227232',
                    'chrom': '17',
                    'genomeVersion': 'GRCh38',
                    'pos': 38739601,
                    'end': 38739601,
                    'alt': 'A',
                    'ref': 'G',
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
            }
        })

        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {new_submission_guid: {
            'mmeResultGuids': sorted(list(response_json['mmeResultsByGuid'].keys()), reverse = True),
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
        self.assertDictEqual(response_json['individualsByGuid'], {NO_SUBMISSION_INDIVIDUAL_GUID: {
            'mmeSubmissionGuid': new_submission_guid,
        }})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000186092', 'ENSG00000235249', 'ENSG00000227232'})
        self.assertListEqual(list(response_json['mmeContactNotes'].keys()), ['st georges, university of london'])

        # Test proxy calls
        self.assertEqual(len(responses.calls), 2)
        expected_body = {
            'patient': {
                'id': NO_SUBMISSION_INDIVIDUAL_GUID,
                'label': 'HG00733',
                'contact': {'href': 'mailto:matchmaker@broadinstitute.org', 'name': 'Test Name',
                            'institution': 'Broad Center for Mendelian Genomics'},
                'species': 'NCBITaxon:9606',
                'sex': 'FEMALE',
                'features': [
                    {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'no'},
                    {'id': 'HP:0002017', 'label': 'Nausea and vomiting', 'observed': 'yes'},
                ],
                'genomicFeatures': [],
            },
            '_disclaimer': MME_DISCLAIMER,
        }
        self.assertEqual(responses.calls[1].request.url, 'http://node_a.com/match')
        self.assertEqual(responses.calls[1].request.headers['X-Auth-Token'], 'abc')
        self.assertEqual(responses.calls[1].request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[1].request.headers['Content-Type'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertDictEqual(json.loads(responses.calls[1].request.body), expected_body)

        # staff users should see originating query for results
        self.login_staff_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(update_body))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['mmeResultsByGuid'][new_internal_match_guid]['originatingSubmission'], {
            'originatingSubmissionGuid': 'MS000015_na20885',
            'familyGuid': 'F000011_11',
            'projectGuid': 'R0003_test',
        })
        self.assertFalse('originatingSubmission' in response_json['mmeResultsByGuid'][new_match_result_guid])

        # The results for each submission should link to one another
        result = MatchmakerResult.objects.get(guid=new_internal_match_guid)
        self.assertEqual(result.submission.guid, new_submission_guid)
        self.assertEqual(result.originating_submission.guid, 'MS000015_na20885')
        matched_result = MatchmakerResult.objects.get(originating_submission__guid=new_submission_guid)
        self.assertEqual(matched_result.submission.guid, 'MS000015_na20885')

    @mock.patch('matchmaker.views.matchmaker_api.MME_NODES')
    @responses.activate
    def test_delete_mme_submission(self, mock_mme_nodes):
        url = reverse(delete_mme_submission, args=[SUBMISSION_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(
            response_json['mmeSubmissionsByGuid'][SUBMISSION_GUID]['deletedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )

        self.assertEqual(MatchmakerResult.objects.filter(submission__guid=SUBMISSION_GUID).count(), 2)

        # Test do not delete if already deleted
        response = self.client.post(url)
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.reason_phrase, 'Matchmaker submission has already been deleted for NA19675_1')

        # Test submission un-deletes when updated
        responses.add(responses.POST, 'http://node_a.com/match', status=200, json={'results': []})
        mock_mme_nodes.values.return_value = [{'name': 'Node A', 'token': 'abc', 'url': 'http://node_a.com/match'}]

        update_url = reverse(update_mme_submission, args=[SUBMISSION_GUID])
        response = self.client.post(update_url, content_type='application/json',  data=json.dumps({
            'geneVariants': [{'geneId': 'ENSG00000235249', 'genomeVersion': '38'}]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {SUBMISSION_GUID: {
            'mmeResultGuids': mock.ANY,
            'individualGuid': INDIVIDUAL_GUID,
            'submissionGuid': SUBMISSION_GUID,
            'createdDate': '2018-05-23T09:07:49.719Z',
            'lastModifiedDate': mock.ANY,
            'deletedDate': None,
            'contactName': 'Sam Baxter',
            'contactHref': 'mailto:matchmaker@broadinstitute.org,test_user@broadinstitute.org',
            'submissionId': 'NA19675_1_01',
            'phenotypes': [],
            'geneVariants': [{'geneId': 'ENSG00000235249'}],
        }})
        self.assertEqual(
            response_json['mmeSubmissionsByGuid'][SUBMISSION_GUID]['lastModifiedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )

    def test_update_mme_result_status(self):
        url = reverse(update_mme_result_status, args=[RESULT_STATUS_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'matchmakerResultGuid': RESULT_STATUS_GUID,
            'comments': 'test comment',
            'deemedIrrelevant': False,
            'flagForAnalysis': True,
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
        self.check_staff_login(url)

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
