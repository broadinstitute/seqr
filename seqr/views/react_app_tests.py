from django.test import TestCase
from django.urls.base import reverse
from seqr.views.react_app import main_app
from seqr.views.utils.test_utils import _check_login


class DashboardPageTest(TestCase):
    fixtures = ['users']

    def test_react_page(self):
        url = reverse(main_app)
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


