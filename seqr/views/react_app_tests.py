from datetime import datetime
from django.urls.base import reverse
import mock

from seqr.views.react_app import main_app, no_login_main_app
from seqr.views.utils.terra_api_utils import TerraRefreshTokenFailedException
from seqr.views.utils.test_utils import TEST_OAUTH2_PROVIDER, AuthenticationTestCase, AnvilAuthenticationTestCase, USER_FIELDS

MOCK_GA_TOKEN = 'mock_ga_token' # nosec

@mock.patch('seqr.views.react_app.DEBUG', False)
class AppPageTest(object):
    databases = '__all__'
    fixtures = ['users']

    def _check_page_html(self, response,  user, user_key='user', vlm_enabled=False, user_email=None, user_fields=None, ga_token_id=None, anvil_loading_date=None):
        user_fields = user_fields or USER_FIELDS
        self.assertEqual(response.status_code, 200)
        initial_json = self.get_initial_page_json(response)
        self.assertSetEqual(set(initial_json.keys()), {'meta', user_key})
        self.assertSetEqual(set(initial_json[user_key].keys()), user_fields)
        self.assertEqual(initial_json[user_key]['username'], user)
        self.assertDictEqual(initial_json['meta'], {
            'version': mock.ANY,
            'hijakEnabled': False,
            'oauthLoginProvider': self.OAUTH_PROVIDER,
            'elasticsearchEnabled': bool(self.ES_HOSTNAME),
            'vlmEnabled': vlm_enabled,
            'warningMessages': [{'id': 1, 'header': 'Warning!', 'message': 'A sample warning'}],
            'anvilLoadingDelayDate': anvil_loading_date,
        })

        self.assertEqual(self.get_initial_page_window('gaTrackingId', response), ga_token_id)
        self.assertEqual(self.get_initial_page_window('userEmail', response), user_email)
        nonce = self.get_initial_page_window('__webpack_nonce__', response)
        self.assertIn('nonce-{}'.format(nonce), response.get('Content-Security-Policy'))

        # test static assets are correctly loaded
        content = response.content.decode('utf-8')
        self.assertEqual(content.count('<script type="text/javascript" nonce="{}">'.format(nonce)), 6)

    @mock.patch('seqr.views.react_app.VLM_CLIENT_ID', 'abc123')
    @mock.patch('seqr.views.react_app.GA_TOKEN_ID', MOCK_GA_TOKEN)
    def test_react_page(self):
        url = reverse(main_app)
        self.check_require_login_no_policies(url, login_redirect_url='/login')

        response = self.client.get(url)
        self._check_page_html(response, 'test_user_no_policies', user_email='test_user_no_policy@test.com', ga_token_id=MOCK_GA_TOKEN, vlm_enabled=True)

    def test_local_react_page(self):
        url = reverse(no_login_main_app)
        response = self.client.get(url, HTTP_HOST='localhost:3000')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertNotRegex(content, r'src="/static/app(-.*)js"')
        self.assertContains(response, 'src="/app.js"')
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
        self._check_page_html(
            response, 'test_user_manager', user_key='newUser',
            user_fields={'id', 'firstName', 'lastName', 'username', 'email'},
        )

        response = self.client.get('/login/set_password/invalid_pwd')
        self.assertEqual(response.status_code, 404)

        # Even if page does not require login, include user metadata if logged in
        self.login_analyst_user()
        response = self.client.get(url)
        self._check_page_html(response, 'test_user')

    @mock.patch('seqr.views.react_app.ANVIL_LOADING_DELAY_EMAIL_START_DATE', '2022-12-01')
    @mock.patch('seqr.views.react_app.datetime')
    def test_react_page_additional_configs(self, mock_datetime):
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.return_value = datetime(2022, 11, 1, 0, 0, 0)

        url = reverse(main_app)
        self.check_require_login_no_policies(url, login_redirect_url='/login')

        response = self.client.get(url)
        self._check_page_html(response, 'test_user_no_policies')

        mock_datetime.now.return_value = datetime(2022, 12, 30, 0, 0, 0)
        response = self.client.get(url)
        self._check_page_html(response, 'test_user_no_policies', anvil_loading_date='2022-12-01')


class LocalAppPageTest(AuthenticationTestCase, AppPageTest):
    fixtures = ['users']
    OAUTH_PROVIDER = ''


class AnvilAppPageTest(AnvilAuthenticationTestCase, AppPageTest):
    fixtures = ['users']
    OAUTH_PROVIDER = TEST_OAUTH2_PROVIDER

    def test_react_page(self, *args, **kwargs):
        super(AnvilAppPageTest, self).test_react_page(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_group_members.assert_not_called()

        self.mock_get_groups.assert_called_with(self.no_policy_user)

        # check behavior if AnVIL API calls fail
        self.mock_get_groups.side_effect = TerraRefreshTokenFailedException('Refresh Error')
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login?next=/dashboard')
