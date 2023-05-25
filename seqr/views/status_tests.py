from django.test import TestCase
from django.urls.base import reverse
import mock
from requests import HTTPError

from seqr.views.status import status_view
from seqr.utils.search.elasticsearch.es_utils_tests import urllib3_responses


class StatusTest(TestCase):

    def _test_status_error(self, url, mock_logger, es_error):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': False, 'secondary_services_ok': False})
        mock_logger.error.assert_has_calls([
            mock.call('Database "default" connection error: No connection'),
            mock.call('Database "reference_data" connection error: No connection'),
            mock.call('Redis connection error: Bad connection'),
            mock.call(f'Search backend connection error: {es_error}'),
            mock.call('Kibana connection error: Connection refused: HEAD /status'),
        ])
        mock_logger.reset_mock()

    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
    @mock.patch('seqr.views.status.redis.StrictRedis')
    @mock.patch('seqr.views.status.connections')
    @mock.patch('seqr.views.status.logger')
    @urllib3_responses.activate
    def test_status(self, mock_logger, mock_db_connections, mock_redis):
        url = reverse(status_view)

        mock_db_connections.__getitem__.return_value.cursor.side_effect = Exception('No connection')
        mock_redis.return_value.ping.side_effect = HTTPError('Bad connection')

        self._test_status_error(url, mock_logger, es_error='No response from elasticsearch ping')

        with mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', ''):
            self._test_status_error(url, mock_logger, es_error='Elasticsearch backend is disabled')

        mock_db_connections.__getitem__.return_value.cursor.side_effect = None
        mock_redis.return_value.ping.side_effect = None
        urllib3_responses.add(urllib3_responses.HEAD, '/', status=200)
        urllib3_responses.add(urllib3_responses.HEAD, '/status', status=500)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': True, 'secondary_services_ok': False})
        mock_logger.error.assert_has_calls([
            mock.call('Kibana connection error: Error 500: Internal Server Error'),
        ])

        mock_logger.reset_mock()
        urllib3_responses.replace_json('/status', {'success': True}, method=urllib3_responses.HEAD, status=200)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': True, 'secondary_services_ok': True})
        mock_logger.error.assert_not_called()
