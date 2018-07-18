import json
import mock

from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.phenotips_api import phenotips_edit_handler, phenotips_pdf_handler
from seqr.views.utils.test_utils import _check_login, create_proxy_request_stub


class PhenotipsAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.apis.phenotips_api.proxy_request', create_proxy_request_stub())
    def test_phenotips_edit(self):
        url = reverse(phenotips_edit_handler, args=['R0001_1kg', 'I000001_na19675'])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'some_json': 'test'}))
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.apis.phenotips_api.proxy_request', create_proxy_request_stub())
    def test_phenotips_pdf(self):
        url = reverse(phenotips_pdf_handler, args=['R0001_1kg', 'I000001_na19675'])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'some_json': 'test'}))
        self.assertEqual(response.status_code, 200)
