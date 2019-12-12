import mock
import responses

from datetime import datetime
from django.test import TestCase

TEST_ACCESS_TOKEN = 'abc123'
TEST_MME_NODES = {TEST_ACCESS_TOKEN: {'name': 'Test Node'}}


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

    def _make_mme_request(self, url, method):
        call_func = getattr(self.client, method)
        return call_func(
            url, HTTP_ACCEPT='application/vnd.ga4gh.matchmaker.v1.0+json', HTTP_X_AUTH_TOKEN=TEST_ACCESS_TOKEN,
        )

    @mock.patch('matchmaker.views.external_api.MME_NODES', TEST_MME_NODES)
    def test_mme_metrics_proxy(self):
        url = '/api/matchmaker/v1/metrics'

        self._check_mme_authenticated(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 406)

        response = self.client.get(url, HTTP_ACCEPT='application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(response.status_code, 401)

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
    @responses.activate
    def test_mme_match_proxy(self, mock_post_to_slack, mock_email):
        responses.add(responses.POST, 'http://localhost:9020/match', status=200, json={'results': [
            {'patient': {'id': 'NA19675_1_01'}},
            {'patient': {'id': 'NA20885'}},
        ]})

        url = '/api/matchmaker/v1/match'
        request_body = """{
            "patient": {
                "id": "12345", 
                "contact": {"institution": "Test Institute", "href": "test@test.com", "name": "PI"},
                "genomicFeatures": [{"gene": {"id": "ENSG00000223972"}}, {"gene": {"id": "WASH7P"}}],
                "features": [{"id": "HP:0003273"}, {"id": "HP:0002017"}]
            }}"""

        response = self.client.post(url, content_type='application/json', data=request_body)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.body, ' ' + request_body.replace('\n', '\n '))

        message = u"""Dear collaborators,

        matchbox found a match between a patient from Test Institute and the following 2 case(s) 
        in matchbox. The following information was included with the query,

        genes: DDX11L1, WASH7P
        phenotypes: HP:0003273 (Hip contracture), HP:0002017 (Nausea and vomiting)
        contact: PI
        email: test@test.com

        We sent back:

        seqr ID NA19675_1 from project 1kg project n\xe5me with uni\xe7\xf8de in family 1 inserted into matchbox on May 23, 2018, with seqr link /project/R0001_1kg/family_page/F000001_1/matchmaker_exchange
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

