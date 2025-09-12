from django.db import connections
from django.test import TestCase
from django.urls.base import reverse
import mock
from requests import HTTPError

from seqr.views.status import status_view
from seqr.utils.search.elasticsearch.es_utils_tests import urllib3_responses


@mock.patch('clickhouse_search.search.CLICKHOUSE_SERVICE_HOSTNAME', '')
@mock.patch('seqr.views.status.redis.StrictRedis')
@mock.patch('seqr.views.status.logger')
class ElasticsearchStatusTest(TestCase):
    databases = '__all__'

    SEARCH_BACKEND_ERROR = 'No response from elasticsearch ping'
    HAS_KIBANA = True
    ES_HOSTNAME = 'testhost'

    def setUp(self):
        patcher = mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', self.ES_HOSTNAME)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _post_teardown(self):
        for conn in connections.all():
            conn.connection = None
            conn.ensure_connection()
            if hasattr(conn.connection, 'pool'):
                conn.connection.pool.closed = False
                conn.connection.is_closed = False

    @urllib3_responses.activate
    def test_status_error(self, mock_logger, mock_redis):
        for conn in connections.all():
            conn.ensure_connection()
            conn.connection.close()
        mock_redis.return_value.ping.side_effect = HTTPError('Bad connection')
        urllib3_responses.add(urllib3_responses.HEAD, '/status', status=400)

        url = reverse(status_view)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': False, 'secondary_services_ok': False})
        calls = [
            mock.call('Database "default" connection error: the connection is closed'),
            mock.call('Database "reference_data" connection error: the connection is closed'),
            mock.call('Database "clickhouse_write" connection error: connection already closed'),
            mock.call('Database "clickhouse" connection error: connection already closed'),
            mock.call('Redis connection error: Bad connection'),
        ]
        if self.SEARCH_BACKEND_ERROR:
            calls.append(mock.call(f'Search backend connection error: {self.SEARCH_BACKEND_ERROR}'))
        if self.HAS_KIBANA:
            calls.append(mock.call('Search Admin connection error: Kibana Error 400: Bad Request'))
        mock_logger.error.assert_has_calls(calls)

    @urllib3_responses.activate
    def test_status(self, mock_logger, mock_redis):
        url = reverse(status_view)

        mock_redis.return_value.ping.side_effect = None
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

    def _assert_expected_requests(self):
        self.assertListEqual([call.request.url for call in urllib3_responses.calls], ['/', '/status', '/', '/status'])


class ClickhouseStatusTest(ElasticsearchStatusTest):

    SEARCH_BACKEND_ERROR = None
    HAS_KIBANA = False
    ES_HOSTNAME = ''

    def _assert_expected_requests(self):
        self.assertEqual(len(urllib3_responses.calls), 0)
