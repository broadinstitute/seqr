import mock
import responses
from unittest import TestCase

from social_core.backends.google import GoogleOAuth2
from seqr.utils.social_auth_pipeline import validate_anvil_registration

TERRA_API_ROOT_URL = 'https://terra.api/'


@mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL', TERRA_API_ROOT_URL)
class SocialAuthPipelineTest(TestCase):

    @responses.activate
    @mock.patch('seqr.utils.social_auth_pipeline.logger')
    def test_validate_anvil_registration(self, mock_logger):
        url = TERRA_API_ROOT_URL + 'register'
        responses.add(responses.GET, url, status = 404)
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})
        mock_logger.info.assert_called_with('User test@seqr.org is trying to login without registration on AnVIL.')
        self.assertEqual(r.url, '/login?googleLoginFailed=true')

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status = 200,
                      body = '{"enabled":{"ldap":True,"allUsersGroup":True,"google":True},"userInfo": {"userEmail":"sf-seqr@my-seqr.iam.gserviceaccount.com","userSubjectId":"108344681601016521986"}}')
        r = validate_anvil_registration(GoogleOAuth2(), {'access_token': '', 'email': 'test@seqr.org'})
        mock_logger.info.assert_not_called()
        self.assertIsNone(r)
