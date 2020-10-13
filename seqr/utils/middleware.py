from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.deprecation import MiddlewareMixin
from requests import HTTPError
import logging
import traceback

from seqr.views.utils.json_utils import create_json_response
from settings import DEBUG

logger = logging.getLogger()


EXCEPTION_ERROR_MAP = {
    PermissionDenied: 403,
    ObjectDoesNotExist: 404,
    HTTPError: lambda e: int(e.response.status_code),
}


def _get_exception_status_code(exception):
    status = next((code for exc, code in EXCEPTION_ERROR_MAP.items() if isinstance(exception, exc)), 500)
    if isinstance(status, int):
        return status

    try:
        return status(exception)
    except Exception:
        return 500


class JsonErrorMiddleware(MiddlewareMixin):

    @staticmethod
    def process_exception(request, exception):
        if request.path.startswith('/api'):
            exception_json = {'message': str(exception)}
            traceback_message = traceback.format_exc()
            logger.error(traceback_message)
            if DEBUG:
                    exception_json['traceback'] = traceback_message
            return create_json_response(exception_json, status=_get_exception_status_code(exception))
        return None


def AnvilSessionMiddleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if request.session.has_key('anvil') and request.user:
            request.user._session_pk=request.session.session_key

        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
