from django.urls.base import reverse
import mock

from seqr.views.apis.superuser_api import get_all_users
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, USER_FIELDS

SUPERUSER_FIELDS = {'hasGoogleAuth'}
SUPERUSER_FIELDS.update(USER_FIELDS)
SUPERUSER_FIELDS -= {'firstName', 'lastName', 'isAnvil'}

EXPECTED_USERS = {
    'test_user_manager', 'test_user_collaborator', 'test_user_no_access', 'test_user', 'test_local_user',
    'test_superuser', 'test_data_manager', 'test_pm_user', 'test_user_inactive', 'test_user_no_policies',
}


class SuperusersAPITest(object):

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    def test_get_all_users(self, mock_analyst_group, mock_pm_group):
        url = reverse(get_all_users)
        self.check_superuser_login(url)

        response = self.client.get(url)
        self._test_superuser_response(response, analyst_enabled=False)

        mock_analyst_group.resolve_expression.return_value = 'analysts'
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        response = self.client.get(url)
        self._test_superuser_response(response, analyst_enabled=True)

    def _test_superuser_response(self, response, analyst_enabled):
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'users'})
        users_by_username = {user['username']: user for user in response_json['users']}
        self.assertSetEqual(set(users_by_username.keys()), EXPECTED_USERS)

        pm_user = users_by_username['test_pm_user']
        self.assertSetEqual(set(pm_user.keys()), SUPERUSER_FIELDS)
        self.assertEqual(pm_user['hasGoogleAuth'], self.HAS_GOOGLE_AUTH)
        self.assertEqual(pm_user['isPm'], analyst_enabled)
        self.assertEqual(pm_user['isAnalyst'], analyst_enabled)

    def test_admin(self):
        url = 'http://localhost/admin/'
        self.check_superuser_login(url, login_redirect_url='/admin/login/', policy_redirect_url='/admin/login/',
                                   permission_denied_error=302)

        response = self.client.get(url)
        self.assertContains(response, 'Django administration', status_code=200)


class LocalSuperusersAPITest(AuthenticationTestCase, SuperusersAPITest):
    fixtures = ['users']
    HAS_GOOGLE_AUTH = False


class AnvilSuperusersAPITest(AnvilAuthenticationTestCase, SuperusersAPITest):
    fixtures = ['users', 'social_auth']
    HAS_GOOGLE_AUTH = True

