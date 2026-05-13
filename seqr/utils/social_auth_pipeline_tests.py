import mock
import responses

from social_core.backends.google import GoogleOAuth2
from seqr.utils.social_auth_pipeline import validate_anvil_registration, validate_user_exist, log_signed_in
from seqr.views.utils.test_utils import AuthenticationTestCase, TEST_TERRA_API_ROOT_URL, REGISTER_RESPONSE


@mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL', TEST_TERRA_API_ROOT_URL)
class SocialAuthPipelineTest(AuthenticationTestCase):

    fixtures = ['users']

    @responses.activate
    def test_validate_anvil_registration(self):
        url = TEST_TERRA_API_ROOT_URL + 'register'
        responses.add(responses.GET, url, status=404)
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})  # nosec
        self.assert_json_logs(None, [
            ('User test@seqr.org is trying to login without registration on AnVIL. None called Terra API: GET /register got status 404 with reason: Not Found', {
                'severity': 'WARNING', 'user': 'test@seqr.org',
            })
        ])
        self.assertEqual(r.url, '/login/error/anvil_registration')

        backend = GoogleOAuth2()
        backend.strategy.session_set('next', '/foo/bar')
        r = validate_anvil_registration(backend, {'access_token': '', 'email': 'test@seqr.org'})  # nosec
        self.assertEqual(r.url, '/login/error/anvil_registration?next=%2Ffoo%2Fbar')

        self.reset_logs()
        responses.replace(responses.GET, url, status=200, body=REGISTER_RESPONSE)
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})
        self.assert_json_logs(None, [('GET https://terra.api/register 200 127', None)])
        self.assertIsNone(r)

    def test_validate_user_exist(self):
        validate_user_exist(GoogleOAuth2(), {'email': 'test_user_manager@test.com'}, user='test')
        self.assert_no_logs()

        r = validate_user_exist(GoogleOAuth2(), {'email': 'test_user_manager@test.com'})
        self.assert_json_logs(None, [
            ('Google user test_user_manager@test.com is trying to login without an existing seqr account (google-oauth2).', {
                'severity': 'WARNING', 'user': 'test_user_manager@test.com',
            })
        ])
        self.assertEqual(r.url, '/login/error/no_account')

        backend = GoogleOAuth2()
        backend.strategy.session_set('next', '/foo/bar')
        r = validate_user_exist(backend, {'email': 'test_user_manager@test.com'})
        self.assertEqual(r.url, '/login/error/no_account?next=%2Ffoo%2Fbar')

    def test_log_signed_in(self):
        log_signed_in(GoogleOAuth2(), {'email': 'test_user_manager@test.com'}, user='test')
        self.assert_json_logs(None, [
            ('Logged in test_user_manager@test.com (google-oauth2)', {'user': 'test_user_manager@test.com'})
        ])

        self.reset_logs()
        log_signed_in(GoogleOAuth2(), {'email': 'test_user_manager@test.com'}, is_new=True, user='test')
        self.assert_json_logs(None, [
            ('Logged in test_user_manager@test.com (google-oauth2)', {'user': 'test_user_manager@test.com'}),
            ('Created user test_user_manager@test.com (google-oauth2)', {'user': 'test_user_manager@test.com'})
        ])
