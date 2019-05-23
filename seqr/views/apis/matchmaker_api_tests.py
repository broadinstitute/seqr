import json
import responses
import mock

from django.test import TestCase
from django.urls.base import reverse

from seqr.models import MatchmakerResult
from seqr.views.apis.matchmaker_api import get_individual_mme_matches, search_individual_mme_matches, \
    update_mme_submission, delete_mme_submission, update_mme_result_status
from seqr.views.utils.test_utils import _check_login

INDIVIDUAL_GUID = 'I000001_na19675'


class VariantSearchAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    def test_get_individual_mme_matches(self):
        url = reverse(get_individual_mme_matches, args=[INDIVIDUAL_GUID])
        _check_login(self, url)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid', 'individualsByGuid', 'genesById'})

        self.assertSetEqual(
            set(response_json['mmeResultsByGuid'].keys()), {'MR0007228_VCGS_FAM50_156', 'MR0003552_SHE_1006P_1'}
        )
        self.assertDictEqual(response_json['mmeResultsByGuid']['MR0003552_SHE_1006P_1'], {
            'id': 'P0004515',
            'score': 0.5706712016939723,
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
                'matchmakerResultGuid': 'MR0003552_SHE_1006P_1',
                'comments': '',
                'weContacted': False,
                'hostContacted': True,
                'deemedIrrelevant': True,
                'flagForAnalysis': False,
                'createdDate': '2019-02-12T18:43:56.358Z',
            },
        })
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
            },
            'mmeSubmittedDate': '2018-05-23T09:07:49.719Z',
            'mmeDeletedDate': None,
        }})
        self.assertSetEqual(
            set(response_json['individualsByGuid'][INDIVIDUAL_GUID]['mmeResultGuids']),
            {'MR0007228_VCGS_FAM50_156', 'MR0003552_SHE_1006P_1'})

        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000186092', 'ENSG00000233750', 'ENSG00000223972'}
        )

    @mock.patch('seqr.views.apis.matchmaker_api.post_to_slack')
    @responses.activate
    def test_query_variants(self, mock_post_to_slack):
        url = reverse(search_individual_mme_matches, args=[INDIVIDUAL_GUID])
        _check_login(self, url)

        new_match_json = {
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
        responses.add(responses.POST, 'http://localhost:9020/match', body='Failed request', status=400)
        responses.add(responses.POST, 'http://localhost:9020/match', status=200, json={
            'results': [{'patient': {'id': 'P0004515'}}]
        })
        responses.add(responses.POST, 'http://localhost:9020/match/external', status=200, json={
            'results': [{'patient': {'id': '34301'}}, new_match_json]
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
        self.assertSetEqual(set(response_json.keys()), {'mmeResultsByGuid', 'individualsByGuid', 'genesById'})

        self.assertEqual(len(response_json['mmeResultsByGuid']), 3)
        self.assertTrue('MR0007228_VCGS_FAM50_156' in response_json['mmeResultsByGuid'])
        self.assertTrue('MR0003552_SHE_1006P_1' in response_json['mmeResultsByGuid'])
        new_result_guid = next(k for k in response_json['mmeResultsByGuid'].keys() if k not in {'MR0007228_VCGS_FAM50_156', 'MR0003552_SHE_1006P_1'})

        self.assertDictEqual(response_json['mmeResultsByGuid'][new_result_guid], {
            'id': '33845',
            'score': 0.92,
            'patient': new_match_json['patient'],
            'phenotypes': [{'observed': 'yes', 'id': 'HP:0012469', 'label': 'Infantile spasms'}],
            'geneVariants': [{'geneId': 'ENSG00000186092'}],
            'matchStatus': {
                'matchmakerResultGuid': new_result_guid,
                'comments': '',
                'weContacted': False,
                'hostContacted': False,
                'deemedIrrelevant': False,
                'flagForAnalysis': False,
                'createdDate': mock.ANY,
            },
        })
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

        # Test proxy calls
        assert len(responses.calls) == 3
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


        # Test slack notification
        slack_message = u"""
    A search from a seqr user from project 1kg project n\xe5me with uni\xe7\xf8de individual NA19675_1 had the following new match(es):
    
     - From Reza Maroofian at institution St Georges, University of London with genes OR4F5 with phenotypes HP:0012469 (Infantile spasms).
    
    https://seqr.broadinstitute.org/project/R0001_1kg/family_page/F000001_1/matchmaker_exchange
    """
        mock_post_to_slack.assert_called_with('matchmaker_seqr_match', slack_message)

        # Test new result model created
        result_model = MatchmakerResult.objects.get(guid=new_result_guid)
        self.assertDictEqual(result_model.result_data, new_match_json)