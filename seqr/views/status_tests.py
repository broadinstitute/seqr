from django.test import TestCase
from django.urls.base import reverse
import mock
from requests import HTTPError
import responses

from seqr.views.status import status_view
from seqr.views.utils.test_utils import urllib3_responses


class StatusTest(TestCase):

    @mock.patch('seqr.views.status.redis.StrictRedis')
    @mock.patch('seqr.views.status.connections')
    @mock.patch('seqr.views.status.logger')
    @responses.activate
    @urllib3_responses.activate
    def test_status(self, mock_logger, mock_db_connections, mock_redis):
        url = reverse(status_view)

        mock_db_connections.__getitem__.return_value.cursor.side_effect = Exception('No connection')
        mock_redis.return_value.ping.side_effect = HTTPError('Bad connection')
        responses.add(responses.HEAD, 'http://localhost:5601/status', status=500)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'version': 'v1.0', 'dependent_services_ok': False})
        mock_logger.error.assert_has_calls([
            mock.call('Unable to connect to database "default": No connection'),
            mock.call('Unable to connect to database "reference_data": No connection'),
            mock.call('Unable to connect to redis: Bad connection'),
            mock.call('Unable to connect to elasticsearch: No response from elasticsearch ping'),
            mock.call('Unable to connect to kibana: 500 Server Error: Internal Server Error for url: http://localhost:5601/status'),
        ])

        mock_logger.reset_mock()
        mock_db_connections.__getitem__.return_value.cursor.side_effect = None
        mock_redis.return_value.ping.side_effect = None
        urllib3_responses.add(responses.HEAD, '/', status=200)
        responses.replace(responses.HEAD, 'http://localhost:5601/status', status=200)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'version': 'v1.0', 'dependent_services_ok': True})
        mock_logger.error.assert_not_called()
