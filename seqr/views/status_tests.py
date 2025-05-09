from django.test import TestCase
from django.urls.base import reverse
import mock
from requests import HTTPError

from seqr.views.status import status_view
from seqr.utils.search.elasticsearch.es_utils_tests import urllib3_responses


@mock.patch('clickhouse_search.search.CLICKHOUSE_SERVICE_HOSTNAME', '')
class StatusTest(object):

    def _test_status_error(self, url, mock_logger):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': False, 'secondary_services_ok': False})
        calls = [
            mock.call('Database "default" connection error: No connection'),
            mock.call('Database "reference_data" connection error: No connection'),
            mock.call('Database "clickhouse" connection error: No connection'),
            mock.call('Redis connection error: Bad connection'),
            mock.call(f'Search backend connection error: {self.SEARCH_BACKEND_ERROR}'),
        ]
        if self.HAS_KIBANA:
            calls.append(mock.call('Search Admin connection error: Kibana Error 400: Bad Request'))
        mock_logger.error.assert_has_calls(calls)
        mock_logger.reset_mock()

    @mock.patch('seqr.views.status.redis.StrictRedis')
    @mock.patch('seqr.views.status.connections')
    @mock.patch('seqr.views.status.logger')
    @urllib3_responses.activate
    def test_status(self, mock_logger, mock_db_connections, mock_redis):
        url = reverse(status_view)

        mock_db_connections.__getitem__.return_value.cursor.side_effect = Exception('No connection')
        mock_redis.return_value.ping.side_effect = HTTPError('Bad connection')
        urllib3_responses.add(urllib3_responses.HEAD, '/status', status=400)

        self._test_status_error(url, mock_logger)

        mock_db_connections.__getitem__.return_value.cursor.side_effect = None
        mock_redis.return_value.ping.side_effect = None
        urllib3_responses.reset()
        urllib3_responses.add(urllib3_responses.HEAD, '/', status=200)
        urllib3_responses.add(urllib3_responses.HEAD, '/status', status=500 if self.HAS_KIBANA else 200)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        if self.HAS_KIBANA:
            self.assertDictEqual(
                response.json(), {'version': 'v1.0', 'dependent_services_ok': True, 'secondary_services_ok': False})
            mock_logger.error.assert_has_calls([
                mock.call('Search Admin connection error: Kibana Error 500: Internal Server Error'),
            ])

            mock_logger.reset_mock()
            urllib3_responses.replace_json('/status', {'success': True}, method=urllib3_responses.HEAD, status=200)

            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': True, 'secondary_services_ok': True})
        mock_logger.error.assert_not_called()
        self._assert_expected_requests()


class ElasticsearchStatusTest(TestCase, StatusTest):

    SEARCH_BACKEND_ERROR = 'No response from elasticsearch ping'
    HAS_KIBANA = True

    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
    def test_status(self, *args):
        super(ElasticsearchStatusTest, self).test_status(*args)

    def _assert_expected_requests(self):
        self.assertListEqual([call.request.url for call in urllib3_responses.calls], ['/', '/status', '/', '/status'])


class HailSearchStatusTest(TestCase, StatusTest):

    SEARCH_BACKEND_ERROR = '400: Bad Request'
    HAS_KIBANA = False

    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', '')
    @mock.patch('seqr.utils.search.hail_search_utils.HAIL_BACKEND_SERVICE_HOSTNAME', 'test-hail')
    def test_status(self, *args):
        super(HailSearchStatusTest, self).test_status(*args)

    def _assert_expected_requests(self):
        self.assertEqual(len(urllib3_responses.calls), 1)
        self.assertEqual(urllib3_responses.calls[0].request.url, '/status')
