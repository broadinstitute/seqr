from django.urls.base import reverse

from seqr.views.apis.superuser_api import get_all_users
from seqr.views.utils.test_utils import AuthenticationTestCase, USER_FIELDS

SUPERUSER_FIELDS = {'hasGoogleAuth'}
SUPERUSER_FIELDS.update(USER_FIELDS)

class SuperusersAPITest(AuthenticationTestCase):
    fixtures = ['users']

    def test_get_all_users(self):
        url = reverse(get_all_users)
        self.check_superuser_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'users'})
        self.assertSetEqual(set(response_json['users'][0].keys()), SUPERUSER_FIELDS)
        self.assertSetEqual({user['username'] for user in response_json['users']}, {
            'test_user_manager', 'test_user_collaborator', 'test_user_no_access', 'test_user', 'test_local_user',
            'test_superuser', 'test_data_manager', 'test_pm_user', 'test_user_inactive', 'test_user_no_policies',
        })


    def test_admin(self):
        url = 'http://localhost/admin/'
        self.check_superuser_login(url, login_redirect_url='/admin/login/', policy_redirect_url='/admin/login/',
                                   permission_denied_error=302)

        response = self.client.get(url)
        self.assertContains(response, 'Django administration', status_code=200)
