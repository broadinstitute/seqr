import json
import mock

from django.http.response import HttpResponse
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.phenotips_api import phenotips_edit_patient, phenotips_view_patient_pdf
from seqr.views.utils.test_utils import _check_login


def _send_request_to_phenotips_mock(method, url, http_headers=None, request_params=None, auth_tuple=None):
    http_response = HttpResponse(
        content='text content',
        status=200,
        reason='OK',
        charset='UTF-8'
    )

    return http_response


class PhenotipsAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.apis.phenotips_api._send_request_to_phenotips', _send_request_to_phenotips_mock)
    def test_phenotips_edit_patient(self):
        url = reverse(phenotips_edit_patient, args=['R0001_1kg', 'P0000001'])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'some_json': 'test'}))
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.apis.phenotips_api._send_request_to_phenotips', _send_request_to_phenotips_mock)
    def test_phenotips_view_patient_pdf(self):
        url = reverse(phenotips_view_patient_pdf, args=['R0001_1kg', 'P0000001'])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'some_json': 'test'}))
        self.assertEqual(response.status_code, 200)
