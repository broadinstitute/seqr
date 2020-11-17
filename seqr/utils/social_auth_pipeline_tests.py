import mock
import responses
from unittest import TestCase

from social_core.backends.google import GoogleOAuth2
from seqr.utils.social_auth_pipeline import validate_anvil_registration, log_signed_in
from seqr.views.utils.test_utils import TEST_TERRA_API_ROOT_URL, REGISTER_RESPONSE


@mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL', TEST_TERRA_API_ROOT_URL)
class SocialAuthPipelineTest(TestCase):

    @responses.activate
    @mock.patch('seqr.utils.social_auth_pipeline.logger')
    def test_validate_anvil_registration(self, mock_logger):
        url = TEST_TERRA_API_ROOT_URL + 'register'
        responses.add(responses.GET, url, status=404)
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})
        mock_logger.warning.assert_called_with('User test@seqr.org is trying to login without registration on AnVIL. Warning: called Terra API: /register got status: 404 with a reason: Not Found')
        self.assertEqual(r.url, '/login?googleLoginFailed=true')

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status=200, body=REGISTER_RESPONSE)
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})
        mock_logger.warning.assert_not_called()
        self.assertIsNone(r)

    @mock.patch('seqr.utils.social_auth_pipeline.logger')
    def test_log_signed_in(self, mock_logger):
        log_signed_in('backend', {'email': 'test_user@test.com'})
        mock_logger.info.assert_called_with('Logged in test_user@test.com(AnVIL)')
