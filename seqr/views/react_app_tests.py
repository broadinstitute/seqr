from django.urls.base import reverse
from seqr.views.react_app import main_app
from seqr.views.utils.test_utils import AuthenticationTestCase


class DashboardPageTest(AuthenticationTestCase):
    fixtures = ['users']

    def test_react_page(self):
        url = reverse(main_app)
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


