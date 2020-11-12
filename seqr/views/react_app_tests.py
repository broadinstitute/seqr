from django.core.exceptions import ObjectDoesNotExist
from django.urls.base import reverse
import json
import re

from seqr.views.react_app import main_app, no_login_main_app
from seqr.views.utils.test_utils import AuthenticationTestCase, USER_FIELDS

INITIAL_JSON_REGEX = r'\(window\.initialJSON=(?P<initial_json>[^)]+)'

MAIN_APP_USER_FIELDS = {'currentPolicies'}
MAIN_APP_USER_FIELDS.update(USER_FIELDS)

class DashboardPageTest(AuthenticationTestCase):
    fixtures = ['users']

    def get_initial_page_json(self, response):
        content = response.content.decode('utf-8')
        self.assertRegex(content, INITIAL_JSON_REGEX)
        m = re.search(INITIAL_JSON_REGEX, content)
        return json.loads(m.group('initial_json'))

    def test_react_page(self):
        url = reverse(main_app)
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertSetEqual(set(initial_json.keys()), {'meta', 'user'})
        self.assertSetEqual(set(initial_json['user'].keys()), MAIN_APP_USER_FIELDS)
        self.assertEqual(initial_json['user']['username'], 'test_user_no_access')
        self.assertFalse(initial_json['user']['currentPolicies'])

        # test static assets are correctly loaded
        content = response.content.decode('utf-8')
        self.assertRegex(content, r'static/app(-.*)js')
        self.assertRegex(content, r'<link\s+href="/static/app.*css"[^>]*>')

    def test_local_react_page(self):
        url = reverse(no_login_main_app)
        response = self.client.get(url, HTTP_HOST='localhost:3000')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertNotRegex(content, r'static/app(-.*)js')
        self.assertContains(response, 'app.js')
        self.assertNotRegex(content, r'<link\s+href="/static/app.*css"[^>]*>')

    def test_no_login_react_page(self):
        url = reverse(no_login_main_app)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertListEqual(list(initial_json.keys()), ['meta'])

        # test set password page correctly includes user from token
        response = self.client.get(
            '/users/set_password/pbkdf2_sha256$30000$y85kZgvhQ539$jrEC343555Itp+14w/T7U6u5XUxtpBZXKv8eh4=')
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertSetEqual(set(initial_json.keys()), {'meta', 'newUser'})
        self.assertSetEqual(set(initial_json['newUser'].keys()), MAIN_APP_USER_FIELDS)
        self.assertEqual(initial_json['newUser']['username'], 'test_user_manager')
        self.assertFalse(initial_json['newUser']['currentPolicies'])

        with self.assertRaises(ObjectDoesNotExist):
            self.client.get('/users/set_password/invalid_pwd')

        # Even if page does not require login, include user metadata if logged in
        self.login_staff_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertSetEqual(set(initial_json.keys()), {'meta', 'user'})
        self.assertSetEqual(set(initial_json['user'].keys()), MAIN_APP_USER_FIELDS)
        self.assertEqual(initial_json['user']['username'], 'test_user')
        self.assertTrue(initial_json['user']['currentPolicies'])
