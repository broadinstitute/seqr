import mock
import json

from datetime import datetime
from django.test import TestCase

from matchmaker.models import MatchmakerIncomingQuery

TEST_ACCESS_TOKEN = 'abc123'
TEST_MME_NODES = {TEST_ACCESS_TOKEN: {'name': 'Test Node'}}


@mock.patch('matchmaker.views.external_api.MME_NODES', TEST_MME_NODES)
class ExternalAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    def _check_mme_authenticated(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 406)

        response = self.client.get(url, HTTP_ACCEPT='application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(response.status_code, 401)

        response = self.client.get(
            url, HTTP_ACCEPT='application/vnd.ga4gh.matchmaker.v1.0+json', HTTP_X_AUTH_TOKEN='invalid',
        )
        self.assertEqual(response.status_code, 401)

    def _make_mme_request(self, url, method, **kwargs):
        call_func = getattr(self.client, method)
        return call_func(
            url, HTTP_ACCEPT='application/vnd.ga4gh.matchmaker.v1.0+json', HTTP_X_AUTH_TOKEN=TEST_ACCESS_TOKEN, **kwargs
        )

    def test_mme_metrics_proxy(self):
        url = '/api/matchmaker/v1/metrics'

        self._check_mme_authenticated(url)

        response = self._make_mme_request(url, 'get')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'metrics': {
                'numberOfCases': 3,
                'numberOfSubmitters': 2,
                'numberOfUniqueGenes': 4,
                'numberOfUniqueFeatures': 5,
                'numberOfRequestsReceived': 3,
                'numberOfPotentialMatchesSent': 1,
                'dateGenerated': datetime.today().strftime('%Y-%m-%d'),
            }
        })

    @mock.patch('matchmaker.views.external_api.EmailMessage')
    @mock.patch('matchmaker.views.external_api.post_to_slack')
    def test_mme_match_proxy(self, mock_post_to_slack, mock_email):
        url = '/api/matchmaker/v1/match'
        request_body = {
            'patient': {
                'id': '12345',
                'contact': {'institution': 'Test Institute', 'href': 'test@test.com', 'name': 'PI'},
                'genomicFeatures': [{'gene': {'id': 'ENSG00000237613'}}, {'gene': {'id': 'WASH7P'}}],
                'features': [{'id': 'HP:0003273'}, {'id': 'HP:0002017'}]
            }}

        # Test invalid requests
        self._check_mme_authenticated(url)

        response = self._make_mme_request(url, 'post')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'message': 'No JSON object could be decoded'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data='Invalid body')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'message': 'No JSON object could be decoded'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'message': '"patient" object is required'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'message': '"id" is required'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {'id': 123}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'message': '"contact" is required'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {'id': 123, 'contact': {'href': 'test@test.com'}}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'message': '"features" or "genomicFeatures" are required'})

        # Test valid request
        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']

        self.assertEqual(len(results), 1)
        self.assertDictEqual(results[0], {
            'patient': {
                'id': 'NA20885',
                'label': 'NA20885',
                'contact': {
                    'href': 'mailto:matchmaker@broadinstitute.org',
                    'name': 'Sam Baxter',
                    'institution': 'Broad Center for Mendelian Genomics',
                },
                'species': 'NCBITaxon:9606',
                'sex': 'MALE',
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
            },
            'score': {
                '_genotypeScore': 0.35,
                '_phenotypeScore': 0.5,
                'patient': 0.175,
            }
        })

        self.assertEqual(MatchmakerIncomingQuery.objects.filter(patient_id='12345').count(), 1)

        message = u"""Dear collaborators,

        matchbox found a match between a patient from Test Institute and the following 1 case(s) 
        in matchbox. The following information was included with the query,

        genes: FAM138A, WASH7P
        phenotypes: HP:0003273 (Hip contracture), HP:0002017 (Nausea and vomiting)
        contact: PI
        email: test@test.com

        We sent back:

        seqr ID NA20885 from project Test Project in family 11 inserted into matchbox on Feb 05, 2019, with seqr link /project/R0003_test/family_page/F000011_11/matchmaker_exchange

        We sent this email alert to: seqr-test@gmail.com, test@broadinstitute.org

        Thank you for using the matchbox system for the Matchmaker Exchange at the Broad Center for Mendelian Genomics. 
        Our website can be found at https://seqr.broadinstitute.org/matchmaker/matchbox and our legal disclaimers can 
        be found found at https://seqr.broadinstitute.org/matchmaker/disclaimer."""
        mock_post_to_slack.assert_called_with('matchmaker_matches', message)
        # mock_email.assert_called_with(
        #     subject='Received new MME match',
        #     body=message,
        #     to=['seqr-test@gmail.com', 'test@broadinstitute.org'],
        #     from_email='matchmaker@broadinstitute.org')
        # mock_email.return_value.send.assert_called()

        # Test receive same request again
        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['results'], results)
        self.assertEqual(MatchmakerIncomingQuery.objects.filter(patient_id='12345').count(), 2)

