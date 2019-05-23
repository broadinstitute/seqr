# Utilities used for unit and integration tests.
from django.contrib.auth.models import User
from django.http.response import HttpResponse


def _check_login(test_case, url):
    """For integration tests of django views that can only be accessed by a logged-in user,
    the 1st step is to authenticate. This function checks that the given url redirects requests
    if the user isn't logged-in, and then authenticates a test user.

    Args:
        test_case (object): the django.TestCase or unittest.TestCase object
        url (string): The url of the django view being tested.
     """
    response = test_case.client.get(url)
    test_case.assertEqual(response.status_code, 302)  # check that it redirects if you don't login

    test_user = User.objects.get(username='test_user')
    test_case.client.force_login(test_user)


def create_proxy_request_stub(response_status=200, reason="OK"):

    """Factory for creating a PhenoTips mock function to replace _send_request_to_phenotips.
    This allows unit tests to be decoupled from communicating with PhenoTips.

    The python mock module allows this to be done using this decorator:

    @mock.patch('seqr.views.apis.phenotips_api._send_request_to_phenotips', create_send_requests_to_phenotips_stub())
    """

    def _proxy_request_stub(*args, **kwargs):
        """Function that stubs out sending a request to PhenoTips."""

        http_response = HttpResponse(
            content='text content',
            status=response_status,
            reason=reason,
            charset='UTF-8'
        )

        return http_response

    return _proxy_request_stub
