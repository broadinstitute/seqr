import json
import responses
import mock

from copy import deepcopy
from datetime import datetime
from django.test import TestCase
from django.urls.base import reverse

from seqr.models import MatchmakerResult, Project, MatchmakerContactNotes
from seqr.views.apis.matchmaker_api import get_individual_mme_matches, search_individual_mme_matches, \
    update_mme_submission, delete_mme_submission, update_mme_result_status, send_mme_contact_email, \
    update_mme_contact_note
from seqr.views.utils.test_utils import _check_login

INDIVIDUAL_GUID = 'I000001_na19675'
NO_SUBMISSION_INDIVIDUAL_GUID = 'I000006_hg00733'
RESULT_STATUS_GUID = 'MR0003552_SHE_1006P_1'

NEW_MATCH_JSON = {
    "score": {
        "patient": 0.92
    },
    "patient": {
        "genomicFeatures": [
            {
                "gene": {
                    "id": "ENSG00000186092"
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
    'individualGuid': INDIVIDUAL_GUID,
    'phenotypes': [{'observed': 'yes', 'id': 'HP:0012469', 'label': 'Infantile spasms'}],
    'geneVariants': [{'geneId': 'ENSG00000186092'}],
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
PARSED_NEW_MATCH_NEW_SUBMISSION_JSON['individualGuid'] = NO_SUBMISSION_INDIVIDUAL_GUID


class EmailException(Exception):

    def __init__(self, *args, **kwargs):
        self.response = mock.MagicMock()
        self.response.content = 'email error'
        self.response.json.return_value = {}
        self.status_code = 402


class MatchmakerAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    def test_get_individual_mme_matches(self):
        url = reverse(get_individual_mme_matches, args=[INDIVIDUAL_GUID])
        _check_login(self, url)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'savedVariantsByGuid', 'mmeContactNotes'})

        self.assertSetEqual(
            set(response_json['mmeResultsByGuid'].keys()), {'MR0007228_VCGS_FAM50_156', 'MR0004688_RGP_105_3', RESULT_STATUS_GUID}
        )
        self.assertDictEqual(response_json['mmeResultsByGuid'][RESULT_STATUS_GUID], {
            'id': 'P0004515',
            'score': 0.5706712016939723,
            'individualGuid': INDIVIDUAL_GUID,
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
        self.assertDictEqual(response_json['individualsByGuid'], {INDIVIDUAL_GUID: {
            'mmeResultGuids': mock.ANY,
            'mmeSubmittedData': {
                'individualGuid': INDIVIDUAL_GUID,
                'patient': {
                    'id': 'NA19675_1_01',
                    'label': 'NA19675_1',
                    'contact': {'href': 'mailto:matchmaker@broadinstitute.org', 'name': 'Sam Baxter', 'institution': 'Broad Center for Mendelian Genomics'},
                    'species': 'NCBITaxon:9606',
                    'features': [
                        {'id': 'HP:0001252', 'label': 'Muscular hypotonia', 'observed': 'yes'},
                        {'id': 'HP:0001263', 'label': 'Global developmental delay', 'observed': 'no'},
                        {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
                    ],
                    'genomicFeatures': [{
                        'gene': {'id': 'ENSG00000186092'},
                        'variant': {
                            'end': 77027548,
                            'start': 77027549,
                            'assembly': 'GRCh38',
                            'referenceName': '14',
                            'alternateBases': 'C',
                            'referenceBases': 'CCACT'
                        },
                        'zygosity': 1
                    }],
                },
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
                    'genomeVersion': 'GRCh38',
                }],
            },
            'mmeSubmittedDate': '2018-05-23T09:07:49.719Z',
            'mmeDeletedDate': None,
        }})
        self.assertSetEqual(
            set(response_json['individualsByGuid'][INDIVIDUAL_GUID]['mmeResultGuids']),
            {'MR0007228_VCGS_FAM50_156', 'MR0004688_RGP_105_3', RESULT_STATUS_GUID})

        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000186092', 'ENSG00000233750', 'ENSG00000223972', 'ENSG00000135953'}
        )
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000001_2103343353_r0390_100', 'SV0000003_2246859832_r0390_100'})
        self.assertDictEqual(response_json['mmeContactNotes'], {})

    @mock.patch('seqr.views.apis.matchmaker_api.EmailMessage')
    @mock.patch('seqr.views.apis.matchmaker_api.post_to_slack')
    @responses.activate
    def test_search_individual_mme_matches(self, mock_post_to_slack, mock_email):
        url = reverse(search_individual_mme_matches, args=[INDIVIDUAL_GUID])
        _check_login(self, url)

        responses.add(responses.POST, 'http://localhost:9020/match', body='Failed request', status=400)
        responses.add(responses.POST, 'http://localhost:9020/match', status=200, json={
            'results': [{'patient': {'id': 'P0004515'}}]
        })
        responses.add(responses.POST, 'http://localhost:9020/match/external', status=200, json={
            'results': [NEW_MATCH_JSON]
        })

        # Test invalid inputs
        response = self.client.get(reverse(search_individual_mme_matches, args=['I000002_na19678']))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.reason_phrase, 'No matchmaker submission found for NA19678')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Error in local match')

        # Test successful search
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'mmeContactNotes'})

        self.assertEqual(len(response_json['mmeResultsByGuid']), 3)
        self.assertTrue(RESULT_STATUS_GUID in response_json['mmeResultsByGuid'])
        new_result_guid = next(k for k in response_json['mmeResultsByGuid'].keys()
                               if k not in {'MR0007228_VCGS_FAM50_156', 'MR0004688_RGP_105_3', RESULT_STATUS_GUID})

        self.assertDictEqual(response_json['mmeResultsByGuid'][new_result_guid], PARSED_NEW_MATCH_JSON)
        self.assertTrue(response_json['mmeResultsByGuid']['MR0004688_RGP_105_3']['matchStatus']['matchRemoved'])
        self.assertDictEqual(response_json['individualsByGuid'], {INDIVIDUAL_GUID: {
            'mmeResultGuids': mock.ANY,
            'mmeSubmittedData': {
                'patient': {
                    'id': 'NA19675_1_01',
                    'label': 'NA19675_1',
                    'contact': {'href': 'mailto:matchmaker@broadinstitute.org', 'name': 'Sam Baxter', 'institution': 'Broad Center for Mendelian Genomics'},
                    'species': 'NCBITaxon:9606',
                    'features': [
                        {'id': 'HP:0001252', 'label': 'Muscular hypotonia', 'observed': 'yes'},
                        {'id': 'HP:0001263', 'label': 'Global developmental delay', 'observed': 'no'},
                        {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
                    ],
                    'genomicFeatures': [{
                        'gene': {'id': 'ENSG00000186092'},
                        'variant': {
                            'end': 77027548,
                            'start': 77027549,
                            'assembly': 'GRCh38',
                            'referenceName': '14',
                            'alternateBases': 'C',
                            'referenceBases': 'CCACT'
                        },
                        'zygosity': 1
                    }],
                },
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
                    'genomeVersion': 'GRCh38',
                }],
                'individualGuid': INDIVIDUAL_GUID,
            },
            'mmeSubmittedDate': '2018-05-23T09:07:49.719Z',
            'mmeDeletedDate': None,
        }})
        self.assertSetEqual(
            set(response_json['individualsByGuid'][INDIVIDUAL_GUID]['mmeResultGuids']),
            set(response_json['mmeResultsByGuid'].keys()))

        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000186092', 'ENSG00000233750', 'ENSG00000223972'}
        )

        self.assertDictEqual(response_json['mmeContactNotes'], {
            'st georges, university of london': {
                'institution': 'st georges, university of london',
                'comments': 'Some additional data about this institution',
            }})

        #  Test removed match is deleted
        self.assertEqual(MatchmakerResult.objects.filter(guid='MR0007228_VCGS_FAM50_156').count(), 0)

        # Test proxy calls
        self.assertEqual(len(responses.calls), 3)
        expected_body = json.dumps({
            'patient': {
                'id': 'NA19675_1_01',
                'label': 'NA19675_1',
                'contact': {'href': 'mailto:matchmaker@broadinstitute.org', 'name': 'Sam Baxter', 'institution': 'Broad Center for Mendelian Genomics'},
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
            }
        })
        self.assertEqual(responses.calls[1].request.url, 'http://localhost:9020/match')
        self.assertEqual(responses.calls[1].request.headers['X-Auth-Token'], 'abcd')
        self.assertEqual(responses.calls[1].request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[1].request.headers['Content-Type'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[1].request.body, expected_body)
        self.assertEqual(responses.calls[2].request.url, 'http://localhost:9020/match/external')
        self.assertEqual(responses.calls[2].request.headers['X-Auth-Token'], 'abcd')
        self.assertEqual(responses.calls[2].request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[2].request.headers['Content-Type'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[2].request.body, expected_body)


        # Test notification
        message = u"""
    A search from a seqr user from project 1kg project n\xe5me with uni\xe7\xf8de individual NA19675_1 had the following new match(es):
    
     - From Reza Maroofian at institution St Georges, University of London with genes OR4F5 with phenotypes HP:0012469 (Infantile spasms).
    
    /project/R0001_1kg/family_page/F000001_1/matchmaker_exchange
    """
        mock_post_to_slack.assert_called_with('matchmaker_seqr_match', message)
        mock_email.assert_called_with(
            subject=u'New matches found for MME submission NA19675_1 (project: 1kg project n\xe5me with uni\xe7\xf8de)',
            body=message,
            to=['test@broadinstitute.org'],
            from_email='matchmaker@broadinstitute.org')
        mock_email.return_value.send.assert_called()

        # Test new result model created
        result_model = MatchmakerResult.objects.get(guid=new_result_guid)
        self.assertDictEqual(result_model.result_data, NEW_MATCH_JSON)

    @responses.activate
    def test_update_mme_submission(self):
        responses.add(responses.POST, 'http://localhost:9020/match', status=200, json={'results': []})
        responses.add(responses.POST, 'http://localhost:9020/match/external', status=200, json={'results': [NEW_MATCH_JSON]})
        responses.add(responses.POST, 'http://localhost:9020/patient/add', status=403,  body='Failed request')
        responses.add(responses.POST, 'http://localhost:9020/patient/add', status=200)
        responses.add(responses.POST, 'http://localhost:9020/patient/add', status=409)

        url = reverse(update_mme_submission, args=[NO_SUBMISSION_INDIVIDUAL_GUID])
        _check_login(self, url)

        # Test invalid inputs
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Genotypes or phentoypes are required')

        response = self.client.post(url, content_type='application/json', data=json.dumps({'geneVariants': [{'pos': 123345}]}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Patient id is required')

        response = self.client.post(url, content_type='application/json', data=json.dumps(
            {'patient': {'id': 123}, 'geneVariants': [{'pos': 123345}]}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Gene id is required for genomic features')

        response = self.client.post(url, content_type='application/json', data=json.dumps(
            {'patient': {'id': 123}, 'phenotypes': [{'id': 'HP:0012469'}]}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.reason_phrase, 'Failed request')

        # Test successful creation
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
            'patient': {
                'id': 'HG00733',
                'label': 'HG00733',
                'contact': {'href': 'mailto:test@broadinstitute.org', 'name': 'PI',
                            'institution': 'Broad Center for Mendelian Genomics'},
                'species': 'NCBITaxon:9606',
            },
            'phenotypes': [
                {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
            ],
            'geneVariants': [{
                'geneId': 'ENSG00000186092',
                'alt': 'C',
                'ref': 'CCACT',
                'chrom': '14',
                'pos': 77027549,
                'genomeVersion': 'GRCh38',
                'numAlt': 2,
            }],
        }))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'mmeContactNotes'})

        self.assertEqual(len(response_json['mmeResultsByGuid']), 1)
        self.assertDictEqual(response_json['mmeResultsByGuid'].values()[0], PARSED_NEW_MATCH_NEW_SUBMISSION_JSON)
        self.assertDictEqual(response_json['individualsByGuid'], {NO_SUBMISSION_INDIVIDUAL_GUID: {
            'mmeResultGuids': response_json['mmeResultsByGuid'].keys(),
            'mmeSubmittedData': {
                'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
                'patient': {
                    'id': 'HG00733',
                    'label': 'HG00733',
                    'contact': {'href': 'mailto:test@broadinstitute.org', 'name': 'PI',
                                'institution': 'Broad Center for Mendelian Genomics'},
                    'species': 'NCBITaxon:9606',
                    'features': [
                        {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
                    ],
                    'genomicFeatures': [{
                        'gene': {'id': 'ENSG00000186092'},
                        'variant': {
                            'start': 77027549,
                            'assembly': 'GRCh38',
                            'referenceName': '14',
                            'alternateBases': 'C',
                            'referenceBases': 'CCACT'
                        },
                        'zygosity': 0
                    }],
                },
                'phenotypes': [
                    {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
                ],
                'geneVariants': [{
                    'geneId': 'ENSG00000186092',
                    'alt': 'C',
                    'ref': 'CCACT',
                    'chrom': '14',
                    'pos': 77027549,
                    'genomeVersion': 'GRCh38',
                }],
            },
            'mmeSubmittedDate': mock.ANY,
            'mmeDeletedDate': None,
        }})
        self.assertEqual(
            response_json['individualsByGuid'][NO_SUBMISSION_INDIVIDUAL_GUID]['mmeSubmittedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        self.assertListEqual(response_json['genesById'].keys(), ['ENSG00000186092'])

        self.assertDictEqual(response_json['mmeContactNotes'], {
            'st georges, university of london': {
                'institution': 'st georges, university of london',
                'comments': 'Some additional data about this institution',
            }})

        # Test proxy calls
        self.assertEqual(len(responses.calls), 4)
        expected_body = {
            'patient': {
                'id': 'HG00733',
                'label': 'HG00733',
                'contact': {'href': 'mailto:test@broadinstitute.org', 'name': 'PI',
                            'institution': 'Broad Center for Mendelian Genomics'},
                'species': 'NCBITaxon:9606',
                'features': [
                    {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'}
                ],
                'genomicFeatures': [{
                    'gene': {'id': 'ENSG00000186092'},
                    'variant': {
                        'start': 77027549,
                        'assembly': 'GRCh38',
                        'referenceName': '14',
                        'alternateBases': 'C',
                        'referenceBases': 'CCACT'
                    },
                    'zygosity': 0
                }],
            }
        }
        self.assertEqual(responses.calls[1].request.url, 'http://localhost:9020/patient/add')
        self.assertEqual(responses.calls[2].request.url, 'http://localhost:9020/match')
        self.assertEqual(responses.calls[3].request.url, 'http://localhost:9020/match/external')
        for call in responses.calls[1:]:
            self.assertEqual(call.request.headers['X-Auth-Token'], 'abcd')
            self.assertEqual(call.request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
            self.assertEqual(call.request.headers['Content-Type'],
                             'application/vnd.ga4gh.matchmaker.v1.0+json')
            self.assertDictEqual(json.loads(call.request.body), expected_body)

        # Test successful update
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
            'patient': {
                'id': 'HG00733',
                'label': 'HG00733',
                'contact': {'href': 'mailto:matchmaker@broadinstitute.org', 'name': 'Test Name',
                            'institution': 'Broad Center for Mendelian Genomics'},
                'species': 'NCBITaxon:9606',
            },
            'phenotypes': [
                {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'},
                {'id': 'HP:0001263', 'label': 'Global developmental delay', 'observed': 'no'},
            ],
        }))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid', 'individualsByGuid', 'genesById', 'mmeContactNotes'})

        self.assertEqual(len(response_json['mmeResultsByGuid']), 1)
        self.assertDictEqual(response_json['mmeResultsByGuid'].values()[0], PARSED_NEW_MATCH_NEW_SUBMISSION_JSON)
        self.assertDictEqual(response_json['individualsByGuid'], {NO_SUBMISSION_INDIVIDUAL_GUID: {
            'mmeResultGuids': response_json['mmeResultsByGuid'].keys(),
            'mmeSubmittedData': {
                'individualGuid': NO_SUBMISSION_INDIVIDUAL_GUID,
                'patient': {
                    'id': 'HG00733',
                    'label': 'HG00733',
                    'contact': {'href': 'mailto:matchmaker@broadinstitute.org', 'name': 'Test Name',
                                'institution': 'Broad Center for Mendelian Genomics'},
                    'species': 'NCBITaxon:9606',
                    'features': [
                        {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'},
                        {'id': 'HP:0001263', 'label': 'Global developmental delay', 'observed': 'no'},
                    ],
                    'genomicFeatures': [],
                },
                'phenotypes': [
                    {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'},
                    {'id': 'HP:0001263', 'label': 'Global developmental delay', 'observed': 'no'},
                ],
                'geneVariants': [],
            },
            'mmeSubmittedDate': mock.ANY,
            'mmeDeletedDate': None,
        }})
        self.assertEqual(
            response_json['individualsByGuid'][NO_SUBMISSION_INDIVIDUAL_GUID]['mmeSubmittedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        self.assertListEqual(response_json['genesById'].keys(), ['ENSG00000186092'])
        self.assertListEqual(response_json['mmeContactNotes'].keys(), ['st georges, university of london'])

        # Test proxy calls
        self.assertEqual(len(responses.calls), 7)
        expected_body = {
            'patient': {
                'id': 'HG00733',
                'label': 'HG00733',
                'contact': {'href': 'mailto:matchmaker@broadinstitute.org', 'name': 'Test Name',
                            'institution': 'Broad Center for Mendelian Genomics'},
                'species': 'NCBITaxon:9606',
                'features': [
                    {'id': 'HP:0012469', 'label': 'Infantile spasms', 'observed': 'yes'},
                    {'id': 'HP:0001263', 'label': 'Global developmental delay', 'observed': 'no'},
                ],
                'genomicFeatures': [],
            }
        }
        self.assertEqual(responses.calls[4].request.url, 'http://localhost:9020/patient/add')
        self.assertEqual(responses.calls[4].request.headers['X-Auth-Token'], 'abcd')
        self.assertEqual(responses.calls[4].request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[4].request.headers['Content-Type'],
                         'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertDictEqual(json.loads(responses.calls[4].request.body), expected_body)
        self.assertEqual(responses.calls[4].response.status_code, 409)

    @responses.activate
    def test_delete_mme_submission(self):
        url = reverse(delete_mme_submission, args=[INDIVIDUAL_GUID])
        _check_login(self, url)

        responses.add(responses.DELETE, 'http://localhost:9020/patient/delete', body='Failed request', status=400)
        responses.add(responses.DELETE, 'http://localhost:9020/patient/delete', status=200)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Failed request')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(
            response_json['individualsByGuid'][INDIVIDUAL_GUID]['mmeDeletedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )

        self.assertEqual(MatchmakerResult.objects.filter(individual__guid=INDIVIDUAL_GUID).count(), 2)

        # Test proxy calls
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[1].request.url, 'http://localhost:9020/patient/delete')
        self.assertEqual(responses.calls[1].request.headers['X-Auth-Token'], 'abcd')
        self.assertEqual(responses.calls[1].request.headers['Accept'], 'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[1].request.headers['Content-Type'],
                         'application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(responses.calls[1].request.body, json.dumps({'id': 'NA19675_1_01'}))

        # Test do not delete if already deleted
        response = self.client.post(url)
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.reason_phrase, 'Matchmaker submission has already been deleted for NA19675_1')

    def test_update_mme_result_status(self):
        url = reverse(update_mme_result_status, args=[RESULT_STATUS_GUID])
        _check_login(self, url)

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

    @mock.patch('seqr.views.apis.matchmaker_api.EmailMessage')
    def test_send_mme_contact_email(self, mock_email):
        url = reverse(send_mme_contact_email, args=[RESULT_STATUS_GUID])
        _check_login(self, url)

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

        mock_email.return_value.send.side_effect = EmailException
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'to': 'test@test.com , other_test@gmail.com',
            'body': 'some email content',
            'subject': 'some email subject'
        }))

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.reason_phrase, 'email error')

    def test_update_mme_contact_note(self):
        url = reverse(update_mme_contact_note, args=['GeneDx'])
        _check_login(self, url)

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

