"""
Utility functions related to authentication.
"""

import logging

from seqr.views.json_utils import create_json_response


logger = logging.getLogger(__name__)

API_LOGIN_REQUIRED_URL = '/api/login-required-error'


def login_required_error(request):
    """Returns an HttpResponse with a 401 UNAUTHORIZED error message.

    This is used to redirect AJAX HTTP handlers to the login page.
    """
    assert not request.user.is_authenticated()

    return create_json_response({}, status=401, reason="login required")

