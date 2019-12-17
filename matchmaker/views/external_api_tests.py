import mock
import json

from datetime import datetime
from django.test import TestCase

from matchmaker.models import MatchmakerIncomingQuery

TEST_ACCESS_TOKEN = 'erjhtg3558324u82'
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
                'genomicFeatures': [{'gene': {'id': 'ENSG00000237613'}}, {'gene': {'id': 'OR4F5'}}],
                'features': [{'id': 'HP:0003273'}, {'id': 'HP:0001252'}]
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

        self.assertEqual(len(results), 2)
        self.assertDictEqual(results[0], {
            'patient': {
                'id': 'NA19675_1_01',
                'label': 'NA19675_1',
                'contact': {
                    'href': 'mailto:matchmaker@broadinstitute.org,test_user@broadinstitute.org',
                    'name': 'Sam Baxter',
                    'institution': 'Broad Center for Mendelian Genomics',
                },
                'species': 'NCBITaxon:9606',
                'sex': 'MALE',
                'features': [
                    {
                        'id': 'HP:0001252',
                        'observed': 'yes'
                    },
                    {
                        'id': 'HP:0001263',
                        'observed': 'no'
                    },
                    {
                        'id': 'HP:0012469',
                        'observed': 'yes'
                    }
                ],
                'genomicFeatures': [
                    {
                        'gene': {
                            'id': 'ENSG00000186092'
                        },
                        'variant': {
                            'end': 77027548,
                            'start': 77027549,
                            'assembly': 'GRCh38',
                            'referenceName': '14',
                            'alternateBases': 'C',
                            'referenceBases': 'CCACT'
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
        }),
        self.assertDictEqual(results[1], {
            'patient': {
                'id': 'P0004515',
                'label': 'P0004515',
                'contact': {
                    'href': 'mailto:UDNCC@hms.harvard.edu,matchmaker@phenomecentral.org',
                    'name': 'Baylor UDN Clinical Site',
                    'institution': 'Broad Center for Mendelian Genomics',
                },
                'species': 'NCBITaxon:9606',
                'sex': 'MALE',
                'features': [
                    {
                        'observed': 'yes',
                        'id': 'HP:0012469'
                    },
                    {
                        'observed': 'no',
                        'id': 'HP:0003273'
                    }
                ],
                'genomicFeatures': [
                    {
                        'gene': {
                            'id': 'ENSG00000186092'
                        }
                    },
                    {
                        'gene': {
                            'id': 'ENSG00000233750'
                        }
                    },
                    {
                        'gene': {
                            'id': 'ENSG00000223972'
                        }
                    }
                ],
            },
            'score': {
                '_genotypeScore': 0.35,
                '_phenotypeScore': 0.1,
                'patient': 0.035,
            }
        })

        self.assertEqual(MatchmakerIncomingQuery.objects.filter(patient_id='12345').count(), 1)

        message_template = u"""Dear collaborators,

    matchbox found a match between a patient from Test Institute and the following 2 case(s) 
    in matchbox. The following information was included with the query,

    genes: FAM138A, OR4F5
    phenotypes: HP:0001252 (Muscular hypotonia), HP:0003273 (Hip contracture)
    contact: PI
    email: test@test.com

    We sent back the following:

    {matches}

    We sent this email alert to: {emails}

Thank you for using the matchbox system for the Matchmaker Exchange at the Broad Center for Mendelian Genomics. 
Our website can be found at https://seqr.broadinstitute.org/matchmaker/matchbox and our legal disclaimers can 
be found found at https://seqr.broadinstitute.org/matchmaker/disclaimer."""
        match1 = u'seqr ID NA19675_1 from project 1kg project n\u00e5me with uni\u00e7\u00f8de in family 1 inserted into matchbox on May 23, 2018, with seqr link /project/R0001_1kg/family_page/F000001_1/matchmaker_exchange'
        match2 = 'seqr ID NA20888 from project Test Project in family 12 inserted into matchbox on Feb 05, 2019, with seqr link /project/R0003_test/family_page/F000012_12/matchmaker_exchange'

        mock_post_to_slack.assert_called_with('matchmaker_matches', message_template.format(
            matches=u'{}\n{}'.format(match1, match2),
            emails='test_user@broadinstitute.org, UDNCC@hms.harvard.edu, matchmaker@phenomecentral.org'
        ))

        mock_email.assert_has_calls([
            mock.call(
                subject='Received new MME match',
                body=message_template.format(matches=match1, emails='test_user@broadinstitute.org'),
                to=['test_user@broadinstitute.org'],
                from_email='matchmaker@broadinstitute.org',
            ),
            mock.call().send(),
            mock.call(
                subject='Received new MME match',
                body=message_template.format(matches=match2, emails='UDNCC@hms.harvard.edu, matchmaker@phenomecentral.org'),
                to=['UDNCC@hms.harvard.edu', 'matchmaker@phenomecentral.org'],
                from_email='matchmaker@broadinstitute.org',
            ),
            mock.call().send()])

        # Test receive same request again
        mock_post_to_slack.reset_mock()
        mock_email.reset_mock()
        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['results'], results)
        self.assertEqual(MatchmakerIncomingQuery.objects.filter(patient_id='12345').count(), 2)
        mock_post_to_slack.assert_called_with(
            'matchmaker_alerts',
            """A match request for 12345 came in from Test Institute today.
        The contact information given was: test@test.com.
        We found 2 existing matching individuals but no new ones, *so no results were sent back*."""
        )
        mock_email.assert_not_called()


