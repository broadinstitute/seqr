from django.urls.base import reverse
import mock

from seqr.views.react_app import main_app, no_login_main_app
from seqr.views.utils.test_utils import AuthenticationTestCase, USER_FIELDS

MOCK_GA_TOKEN = 'mock_ga_token' # nosec

@mock.patch('seqr.views.react_app.DEBUG', False)
class DashboardPageTest(AuthenticationTestCase):
    databases = '__all__'
    fixtures = ['users']

    def _check_page_html(self, response,  user, google_enabled=False, user_key='user', ga_token_id=None):
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertSetEqual(set(initial_json.keys()), {'meta', user_key})
        self.assertSetEqual(set(initial_json[user_key].keys()), USER_FIELDS)
        self.assertEqual(initial_json[user_key]['username'], user)
        self.assertDictEqual(initial_json['meta'], {
            'version': mock.ANY,
            'hijakEnabled': False,
            'googleLoginEnabled': google_enabled,
            'warningMessages': [{'id': 1, 'header': 'Warning!', 'message': 'A sample warning'}],
        })

        self.assertEqual(self.get_initial_page_window('gaTrackingId', response), ga_token_id)
        nonce = self.get_initial_page_window('__webpack_nonce__', response)
        self.assertIn('nonce-{}'.format(nonce), response.get('Content-Security-Policy'))

        # test static assets are correctly loaded
        content = response.content.decode('utf-8')
        self.assertRegex(content, r'static/app(-.*)js')
        self.assertRegex(content, r'<link\s+href="/static/app.*css"[^>]*>')
        self.assertEqual(content.count('<script type="text/javascript" nonce="{}">'.format(nonce)), 4)

    @mock.patch('seqr.views.react_app.GA_TOKEN_ID', MOCK_GA_TOKEN)
    @mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
    def test_react_page(self, mock_oauth_key):
        mock_oauth_key.__bool__.return_value = False
        url = reverse(main_app)
        self.check_require_login_no_policies(url, login_redirect_url='/login')

        response = self.client.get(url)
        self._check_page_html(response, 'test_user_no_policies', ga_token_id=MOCK_GA_TOKEN)

        # test with google auth enabled
        mock_oauth_key.__bool__.return_value = True
        response = self.client.get(url)
        self._check_page_html(response, 'test_user_no_policies', google_enabled=True, ga_token_id=MOCK_GA_TOKEN)

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
            '/login/set_password/pbkdf2_sha256$30000$y85kZgvhQ539$jrEC343555Itp+14w/T7U6u5XUxtpBZXKv8eh4=')
        self.assertEqual(response.status_code, 200)
        self._check_page_html(response, 'test_user_manager', user_key='newUser')

        response = self.client.get('/login/set_password/invalid_pwd')
        self.assertEqual(response.status_code, 404)

        # Even if page does not require login, include user metadata if logged in
        self.login_analyst_user()
        response = self.client.get(url)
        self._check_page_html(response, 'test_user')
