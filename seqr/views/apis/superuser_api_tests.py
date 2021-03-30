from django.urls.base import reverse

from seqr.views.apis.superuser_api import get_all_users
from seqr.views.utils.test_utils import AuthenticationTestCase, USER_FIELDS


class SuperusersAPITest(AuthenticationTestCase):
    fixtures = ['users']

    def test_get_all_users(self):
        url = reverse(get_all_users)
        self.check_superuser_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'users'})
        self.assertSetEqual(set(response_json['users'][0].keys()), USER_FIELDS)
        self.assertSetEqual({user['username'] for user in response_json['users']}, {
            'test_user_manager', 'test_user_collaborator', 'test_user_no_access', 'test_user', 'test_local_user',
            'test_superuser', 'test_data_manager', 'test_pm_user',
        })


    def test_admin(self):
        url = 'http://localhost/admin/'

        # test restricted access
        response = self.client.get(url, follow=True)
        self.assertListEqual(
            response.redirect_chain, [('/admin/login/?next=/admin/', 302), ('/login?next=%2Fadmin%2F', 301)])
        self.assertNotContains(response, 'Django administration')

        self.login_collaborator()
        response = self.client.get(url, follow=True)
        self.assertListEqual(
            response.redirect_chain, [('/admin/login/?next=/admin/', 302), ('/login?next=%2Fadmin%2F', 301)])
        self.assertNotContains(response, 'Django administration')

        self.login_data_manager_user()
        response = self.client.get(url, follow=True)
        self.assertListEqual(
            response.redirect_chain, [('/admin/login/?next=/admin/', 302), ('/login?next=%2Fadmin%2F', 301)])
        self.assertNotContains(response, 'Django administration')

        # test success
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertContains(response, 'Django administration', status_code=200)
