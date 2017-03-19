# Utilities used for unit and integration tests.
from django.contrib.auth.models import User

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