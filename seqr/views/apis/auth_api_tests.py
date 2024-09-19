import mock
import json

from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.auth_api import login_view, logout_view, login_required_error, policies_required_error
from django.contrib.auth.models import User

from seqr.views.utils.test_utils import TEST_OAUTH2_PROVIDER


class AuthAPITest(TestCase):
    fixtures = ['users']

    def setUp(self):
        User.objects.create_user('test_new_user', 'test_new_user@institute.com', 'password123')

    def test_login_view(self):
        url = reverse(login_view)

        # send login request without a password
        req_values = {
            'email': 'test_user_manager@test.com'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 400)

        # send login request without an email
        req_values = {
            'password': 'not_a_password'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 400)

        # send login request with a wrong email
        req_values = {
            'email': 'not_a_user@test.com',
            'password': 'not_a_password'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 401)

        # send login request with a wrong password
        req_values = {
            'email': 'test_user_manager@test.com',
            'password': 'not_a_password'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 401)

        # send login request with unicode character
        req_values = {
            'email': 'test_new_user@instıtute.com',
            'password': 'password123'
        }
        response = self.client.post(url, content_type='application/json', data=json.dumps(req_values))
        self.assertEqual(response.status_code, 401)

        # send login request with a correct password
        req_values = {
            'email': 'Test_New_User@institute.com',
            'password': 'password123'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertTrue(response_json['success'])

        # send login request with a privileged account (data manage or superuser) while Google auth is not enabled
        req_values = {
            'email': 'test_data_manager@test.com',
            'password': 'not-a-password'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.reason_phrase, 'Invalid credentials')

        req_values = {
            'email': 'test_superuser@test.com',
            'password': 'not-a-password'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.reason_phrase, 'Invalid credentials')

    @mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_PROVIDER', TEST_OAUTH2_PROVIDER)
    def test_login_view_with_google(self):
        url = reverse(login_view)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    def test_logout_view(self):
        url = reverse(login_view)
        req_values = {
            'email': 'test_new_user@institute.com',
            'password': 'password123'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)

        url = reverse(logout_view)
        # send logout request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        # no error when attempt to log out again
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    def test_login_required_error(self):
        url = reverse(login_required_error)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.reason_phrase, 'login required')
        self.assertDictEqual(response.json(), {'error': '/login'})

    def test_policies_required_error(self):
        url = reverse(policies_required_error)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        self.assertDictEqual(response.json(), {'error': '/accept_policies'})
