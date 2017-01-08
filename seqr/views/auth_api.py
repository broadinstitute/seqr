import logging

from seqr.views.utils import create_json_response


logger = logging.getLogger(__name__)

API_LOGIN_REDIRECT_URL = '/api/not-logged-in-error'

def not_logged_in_error(request):
    """Returns an HttpResponse with a 401 UNAUTHORIZED error message."""
    assert not request.user.is_authenticated()

    logger.info("NOT LOGGED IN")
    return create_json_response({}, status=401, reason="not logged in")

