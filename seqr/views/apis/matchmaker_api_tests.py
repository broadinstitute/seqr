import json
import responses
import mock
from copy import deepcopy

from django.test import TestCase
from django.urls.base import reverse

from seqr.models import MatchmakerResult
from seqr.views.apis.matchmaker_api import get_individual_mme_matches, search_individual_mme_matches, \
    update_mme_submission, delete_mme_submission, update_mme_result_status
from seqr.views.utils.test_utils import _check_login


LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'
INDIVIDUAL_GUID = 'I000001_na19675'
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
EXPECTED_VARIANTS[0]['locusListGuids'] = []
EXPECTED_VARIANTS[1]['locusListGuids'] = [LOCUS_LIST_GUID]
EXPECTED_VARIANTS[2]['locusListGuids'] = []


def _get_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(VARIANTS), len(VARIANTS)


class VariantSearchAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    @mock.patch('seqr.views.apis.matchmaker_api.post_to_slack')
    @responses.activate
    def test_query_variants(self, mock_post_to_slack):
        url = reverse(search_individual_mme_matches, args=[INDIVIDUAL_GUID])
        _check_login(self, url)

        new_match_json = {
            "score": {
                "patient": 1.0
            },
            "patient": {
                "genomicFeatures": [
                    {
                        "gene": {
                            "id": "ENSG00000186092"
                        }
                    }
                ],
                'features': [{'observed': 'yes', 'id': 'HP:0012469'}],
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
        new_guid = next(k for k in response_json['mmeResultsByGuid'].keys() if k not in {'MR0007228_VCGS_FAM50_156', 'MR0003552_SHE_1006P_1'})
        result_model = MatchmakerResult.objects.get(guid=new_guid)
        self.assertDictEqual(result_model.result_data, new_match_json)