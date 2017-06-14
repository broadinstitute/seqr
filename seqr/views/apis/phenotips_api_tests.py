import json
import mock

from django.http.response import HttpResponse
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.phenotips_api import phenotips_edit, phenotips_pdf
from seqr.views.utils.test_utils import _check_login, create_send_requests_to_phenotips_stub


class PhenotipsAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.apis.phenotips_api._send_request_to_phenotips', create_send_requests_to_phenotips_stub())
    def test_phenotips_edit(self):
        url = reverse(phenotips_edit, args=['R0001_1kg', 'P0000001'])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'some_json': 'test'}))
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.apis.phenotips_api._send_request_to_phenotips', create_send_requests_to_phenotips_stub())
    def test_phenotips_pdf(self):
        url = reverse(phenotips_pdf, args=['R0001_1kg', 'P0000001'])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'some_json': 'test'}))
        self.assertEqual(response.status_code, 200)
