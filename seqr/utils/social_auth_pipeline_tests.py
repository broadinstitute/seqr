import mock
import responses
from unittest import TestCase

from social_core.backends.google import GoogleOAuth2
from seqr.utils.social_auth_pipeline import validate_anvil_registration, validate_user_exist, log_signed_in
from seqr.views.utils.test_utils import TEST_TERRA_API_ROOT_URL, REGISTER_RESPONSE


@mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL', TEST_TERRA_API_ROOT_URL)
class SocialAuthPipelineTest(TestCase):

    @responses.activate
    @mock.patch('seqr.utils.social_auth_pipeline.logger')
    def test_validate_anvil_registration(self, mock_logger):
        url = TEST_TERRA_API_ROOT_URL + 'register'
        responses.add(responses.GET, url, status=404)
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})
        mock_logger.warning.assert_called_with('User test@seqr.org is trying to login without registration on AnVIL. None called Terra API: GET /register got status 404 with reason: Not Found')
        self.assertEqual(r.url, '/login?anvilLoginFailed=true')
        self.assertEqual(len(mock_logger.method_calls), 1)

        backend = GoogleOAuth2()
        backend.strategy.session_set('next', '/foo/bar')
        r = validate_anvil_registration(backend, {'access_token': '', 'email': 'test@seqr.org'})
        self.assertEqual(r.url, '/login?anvilLoginFailed=true&next=%2Ffoo%2Fbar')

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status=200, body=REGISTER_RESPONSE)
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})
        mock_logger.warning.assert_not_called()
        self.assertIsNone(r)

    @mock.patch('seqr.utils.social_auth_pipeline.logger')
    def test_validate_user_exist(self, mock_logger):
        validate_user_exist(GoogleOAuth2(), {'email': 'test_user_manager@test.com'}, user='test')
        self.assertEqual(len(mock_logger.method_calls), 0)

        r = validate_user_exist(GoogleOAuth2(), {'email': 'test_user_manager@test.com'})
        mock_logger.warning.assert_called_with(
            'Google user test_user_manager@test.com is trying to login without an existing seqr account (google-oauth2).')
        self.assertEqual(r.url, '/login?googleLoginFailed=true')
        self.assertEqual(len(mock_logger.method_calls), 1)

        backend = GoogleOAuth2()
        backend.strategy.session_set('next', '/foo/bar')
        r = validate_user_exist(backend, {'email': 'test_user_manager@test.com'})
        self.assertEqual(r.url, '/login?googleLoginFailed=true&next=%2Ffoo%2Fbar')

    @mock.patch('seqr.utils.social_auth_pipeline.logger')
    def test_log_signed_in(self, mock_logger):
        log_signed_in(GoogleOAuth2(), {'email': 'test_user_manager@test.com'}, user='test')
        mock_logger.info.assert_called_with('Logged in test_user_manager@test.com (google-oauth2)')
        self.assertEqual(len(mock_logger.method_calls), 1)

        mock_logger.reset_mock()
        log_signed_in(GoogleOAuth2(), {'email': 'test_user_manager@test.com'}, is_new=True, user='test')
        mock_logger.info.assert_has_calls([
            mock.call('Logged in test_user_manager@test.com (google-oauth2)'),
            mock.call('Created user test_user_manager@test.com (google-oauth2)'),
        ])
        self.assertEqual(len(mock_logger.method_calls), 2)
