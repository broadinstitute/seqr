from django.db import connections
from django.test import TestCase
from django.urls.base import reverse
import mock
from requests import HTTPError

from seqr.views.status import status_view


@mock.patch('seqr.views.status.redis.StrictRedis')
@mock.patch('seqr.views.status.logger')
class StatusTest(TestCase):
    databases = '__all__'

    def _post_teardown(self):
        for conn in connections.all():
            conn.connection = None
            conn.ensure_connection()
            if hasattr(conn.connection, 'pool'):
                conn.connection.pool.closed = False
                conn.connection.is_closed = False

    def test_status_error(self, mock_logger, mock_redis):
        for conn in connections.all():
            conn.ensure_connection()
            conn.connection.close()
        mock_redis.return_value.ping.side_effect = HTTPError('Bad connection')

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
        mock_logger.error.assert_has_calls(calls)

    def test_status(self, mock_logger, mock_redis):
        url = reverse(status_view)

        mock_redis.return_value.ping.side_effect = HTTPError('Bad connection')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': True, 'secondary_services_ok': False})
        mock_logger.error.assert_called_with('Redis connection error: Bad connection')

        mock_logger.reset_mock()
        mock_redis.return_value.ping.side_effect = None

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(), {'version': 'v1.0', 'dependent_services_ok': True, 'secondary_services_ok': True})
        mock_logger.error.assert_not_called()
