import mock
import json

from datetime import datetime
from django.test import TestCase

from matchmaker.models import MatchmakerIncomingQuery

TEST_ACCESS_TOKEN = 'erjhtg3558324u82'  # nosec
TEST_MME_NODES = {TEST_ACCESS_TOKEN: {'name': 'Test Node'}}


@mock.patch('matchmaker.views.external_api.MME_NODES', TEST_MME_NODES)
class ExternalAPITest(TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def _check_mme_authenticated(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 406)

        response = self.client.get(url, HTTP_ACCEPT='application/vnd.ga4gh.matchmaker.v1.0+json')
        self.assertEqual(response.status_code, 401)

        response = self.client.get(
            url, HTTP_ACCEPT='application/vnd.ga4gh.matchmaker.v1.0+json', HTTP_X_AUTH_TOKEN='invalid', # nosec
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
                'numberOfCases': 4,
                'numberOfSubmitters': 2,
                'numberOfUniqueGenes': 3,
                'numberOfUniqueFeatures': 4,
                'numberOfRequestsReceived': 3,
                'numberOfPotentialMatchesSent': 1,
                'dateGenerated': datetime.today().strftime('%Y-%m-%d'),
            }
        })

    @mock.patch('matchmaker.views.external_api.logger')
    @mock.patch('matchmaker.views.external_api.EmailMessage')
    @mock.patch('matchmaker.views.external_api.safe_post_to_slack')
    def test_mme_match_proxy(self, mock_post_to_slack, mock_email, mock_logger):
        mock_email.return_value.send.side_effect = [Exception('Email error'), True, True]
        url = '/api/matchmaker/v1/match'
        request_body = {
            'patient': {
                'id': '12345',
                'contact': {'institution': 'Test Institute', 'href': 'test@test.com', 'name': 'PI'},
                'genomicFeatures': [{'gene': {'id': 'ENSG00000237613'}}, {
                    'gene': {'id': 'RP11'},
                    'zygosity': 1,
                    'variant': {'start': 3343353, 'end': 3343355, 'referenceName': '21'},
                }],
                'features': [{'id': 'HP:0003273'}, {'id': 'HP:0001252'}]
            }}

        # Test invalid requests
        self._check_mme_authenticated(url)

        response = self._make_mme_request(url, 'post')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['error'])
        self.assertEqual(response_json['error'], 'No JSON object could be decoded')

        response = self._make_mme_request(url, 'post', content_type='application/json', data='Invalid body')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['error'])
        self.assertEqual(response_json['error'], 'No JSON object could be decoded')

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': '"patient" object is required'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': '"id" is required'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {'id': 123}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': '"contact" is required'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {'id': 123, 'contact': {'href': 'test@test.com'}}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': '"features" or "genomicFeatures" are required'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {'id': 123, 'contact': {'href': 'test@test.com'}, 'features': [{}]}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'all "features" require an id'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {'id': 123, 'contact': {'href': 'test@test.com'}, 'genomicFeatures': [{'variant': {}}]}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'all "genomicFeatures" require a gene id'})

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps({
            'patient': {'id': 123, 'contact': {'href': 'test@test.com'}, 'genomicFeatures': [{'gene': {}}]}
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'all "genomicFeatures" require a gene id'})

        # Test valid request
        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']

        self.assertEqual(len(results), 3)
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
                            'id': 'ENSG00000135953'
                        },
                        'variant': {
                            'start': 3343353,
                            'assembly': 'GRCh37',
                            'referenceName': '21',
                            'alternateBases': 'G',
                            'referenceBases': 'GAGA'
                        },
                        'zygosity': 1
                    }
                ],
            },
            'score': {
                '_genotypeScore': 0.5,
                '_phenotypeScore': 0.5,
                'patient': 0.25,
            }
        })
        self.assertDictEqual(results[2], {
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
                'features': None,
                'genomicFeatures': [
                    {
                        'gene': {
                            'id': 'ENSG00000135953'
                        }, 'variant': {
                            'referenceName': '1',
                            'start': 249045487,
                            'end': 249045898,
                            'assembly': 'GRCh37',
                        },
                    },
                    {
                        'gene': {
                            'id': 'ENSG00000223972'
                        }, 'variant': {
                            'referenceName': '1',
                            'start': 249045487,
                            'end': 249045898,
                            'assembly': 'GRCh37',
                        },
                    },
                    {
                        'gene': {
                            'id': 'ENSG00000240361'
                        }, 'variant': {
                            'referenceName': '1',
                            'start': 249045487,
                            'end': 249045898,
                            'assembly': 'GRCh37',
                        },
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

        message_template = """Dear collaborators,

    matchbox found a match between a patient from Test Institute and the following 3 case(s) 
    in matchbox. The following information was included with the query,

    genes: FAM138A, RP11
    phenotypes: HP:0001252 (Muscular hypotonia), HP:0003273 (Hip contracture)
    contact: PI
    email: test@test.com

    We sent back the following:

    {matches}

    We sent this email alert to: {emails}

Thank you for using the matchbox system for the Matchmaker Exchange at the Broad Center for Mendelian Genomics. 
Our website can be found at https://seqr.broadinstitute.org/matchmaker/matchbox and our legal disclaimers can 
be found found at https://seqr.broadinstitute.org/matchmaker/disclaimer."""
        match1 = 'seqr ID NA19675_1 from project 1kg project n\u00e5me with uni\u00e7\u00f8de in family 1 inserted into matchbox on May 23, 2018, with seqr link /project/R0001_1kg/family_page/F000001_1/matchmaker_exchange'
        match2 = 'seqr ID NA20888 from project Test Reprocessed Project in family 12 inserted into matchbox on Feb 05, 2019, with seqr link /project/R0003_test/family_page/F000012_12/matchmaker_exchange'
        match3 = 'seqr ID NA21234 from project Non-Analyst Project in family 14 inserted into matchbox on Feb 05, 2019, with seqr link /project/R0004_non_analyst_project/family_page/F000014_14/matchmaker_exchange'

        mock_post_to_slack.assert_called_with('matchmaker_matches', message_template.format(
            matches='\n'.join([match1, match2, match3]),
            emails='UDNCC@hms.harvard.edu, matchmaker@broadinstitute.org, matchmaker@phenomecentral.org, test_user@broadinstitute.org'
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
            mock.call().send(),
            mock.call(
                subject='Received new MME match',
                body=message_template.format(matches=match3, emails='matchmaker@broadinstitute.org'),
                to=['matchmaker@broadinstitute.org'],
                from_email='matchmaker@broadinstitute.org',
            ),
            mock.call().send(),
        ])

        mock_logger.error.assert_called_once_with(
            'Unable to send notification email for incoming MME match with NA19675_1_01: Email error')

        # Test receive same request again
        mock_post_to_slack.reset_mock()
        mock_email.reset_mock()
        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['results'], results)
        self.assertEqual(MatchmakerIncomingQuery.objects.filter(patient_id='12345').count(), 2)
        mock_post_to_slack.assert_called_with(
            'matchmaker_matches',
            """A match request for 12345 came in from Test Institute today.
        The contact information given was: test@test.com.
        We found 3 existing matching individuals but no new ones, *so no results were sent back*."""
        )
        mock_email.assert_not_called()

    @mock.patch('matchmaker.views.external_api.EmailMessage')
    @mock.patch('matchmaker.views.external_api.safe_post_to_slack')
    def test_mme_match_proxy_phenotype_only(self, mock_post_to_slack, mock_email):
        url = '/api/matchmaker/v1/match'
        request_body = {
            'patient': {
                'id': '12345',
                'contact': {'institution': 'Test Institute', 'href': 'test@test.com', 'name': 'PI'},
                'features': [
                    {'id': 'HP:0002017'},
                    {'id': 'HP:0001252', 'observed': 'yes'},
                    {'id': 'HP:0001263', 'observed': 'yes'},
                    {'id': 'HP:0012469', 'observed': 'no'},
                ]
            }}

        self._check_mme_authenticated(url)

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
                'sex': 'FEMALE',
                'features': [
                    {'id': 'HP:0001252', 'label': 'Muscular hypotonia', 'observed': 'yes'},
                    {'id': 'HP:0002017',  'label': 'Nausea and vomiting', 'observed': 'yes'},
                ],
                'genomicFeatures': [
                    {
                        'gene': {
                            'id': 'ENSG00000240361'
                        },
                        'variant': {
                            'start': 248367227,
                            'assembly': 'GRCh37',
                            'referenceName': '1',
                            'alternateBases': 'T',
                            'referenceBases': 'TC'
                        },
                        'zygosity': 1
                    }
                ],
            },
            'score': {
                '_genotypeScore': 0,
                '_phenotypeScore': 0.6666666666666666,
                'patient': 0.0,
            }
        })

        self.assertEqual(MatchmakerIncomingQuery.objects.filter(patient_id='12345').count(), 1)

        match = 'seqr ID NA20889 from project Test Reprocessed Project in family 12 inserted into matchbox on Feb 05, 2019, ' \
                'with seqr link /project/R0003_test/family_page/F000012_12/matchmaker_exchange'
        message = f"""Dear collaborators,

    matchbox found a match between a patient from Test Institute and the following 1 case(s) 
    in matchbox. The following information was included with the query,

    genes: 
    phenotypes: HP:0002017 (Nausea and vomiting), HP:0012469 (Infantile spasms), HP:0001252 (Muscular hypotonia), HP:0001263 (Global developmental delay)
    contact: PI
    email: test@test.com

    We sent back the following:

    {match}

    We sent this email alert to: matchmaker@broadinstitute.org

Thank you for using the matchbox system for the Matchmaker Exchange at the Broad Center for Mendelian Genomics. 
Our website can be found at https://seqr.broadinstitute.org/matchmaker/matchbox and our legal disclaimers can 
be found found at https://seqr.broadinstitute.org/matchmaker/disclaimer."""

        mock_post_to_slack.assert_called_with('matchmaker_matches', message)

        mock_email.assert_has_calls([
            mock.call(
                subject='Received new MME match',
                body=message,
                to=['matchmaker@broadinstitute.org'],
                from_email='matchmaker@broadinstitute.org',
            ),
            mock.call().send(),
        ])

    @mock.patch('seqr.utils.communication_utils.logger')
    @mock.patch('matchmaker.views.external_api.EmailMessage')
    @mock.patch('seqr.utils.communication_utils._post_to_slack')
    def test_mme_match_proxy_no_results(self, mock_post_to_slack, mock_email, mock_logger):
        url = '/api/matchmaker/v1/match'
        request_body = {
            'patient': {
                'id': '12345',
                'contact': {'institution': 'Test Institute', 'href': 'test@test.com', 'name': 'PI'},
                'genomicFeatures': [{'gene': {'id': 'ABCD'}}],
                'features': []
            }}

        self._check_mme_authenticated(url)

        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']

        self.assertEqual(len(results), 0)

        incoming_query_q = MatchmakerIncomingQuery.objects.filter(institution='Test Institute')
        self.assertEqual(incoming_query_q.count(), 1)
        self.assertIsNone(incoming_query_q.first().patient_id)

        slack_message = """A match request for 12345 came in from Test Institute today.
        The contact information given was: test@test.com.
        We didn't find any individuals in matchbox that matched that query well, *so no results were sent back*."""
        mock_post_to_slack.assert_called_with(
            'matchmaker_matches',
            slack_message
        )
        mock_email.assert_not_called()

        # Test receive same request again and notification exception
        mock_post_to_slack.reset_mock()
        mock_post_to_slack.side_effect = Exception('Slack connection error')
        response = self._make_mme_request(url, 'post', content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['results'], [])
        self.assertEqual(MatchmakerIncomingQuery.objects.filter(institution='Test Institute').count(), 2)
        mock_logger.error.assert_called_with(
            f'Slack error: Slack connection error: Original message in channel (matchmaker_matches) - {slack_message}')


