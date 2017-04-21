from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.awesomebar_api import awesomebar_autocomplete
from seqr.views.utils.test_utils import _check_login


class AwesomebarAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_project_categories_api(self):
        url = reverse(awesomebar_autocomplete)
        _check_login(self, url)

        #self.assertRaisesRegexp(ValueError, "missing", lambda:
        #    self.client.get(url)
        #)

        response = self.client.get(url+"?q=T")
        self.assertEqual(response.status_code, 200)
