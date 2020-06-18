from __future__ import unicode_literals
from builtins import str as unicode_str

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
            try:
                exception_json = {'message': str(exception)}
            except Exception:
                exception_json = {'message': unicode_str(exception)}
            traceback_message = traceback.format_exc()
            logger.error(traceback_message)
            if DEBUG:
                    exception_json['traceback'] = traceback_message
            return create_json_response(exception_json, status=_get_exception_status_code(exception))
        return None
