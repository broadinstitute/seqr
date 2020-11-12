from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http.request import RawPostDataException
from django.utils.deprecation import MiddlewareMixin
from requests import HTTPError
import json
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
            exception_json = {'error': str(exception)}
            if DEBUG:
                traceback_message = traceback.format_exc()
                logger.error(traceback_message)
                exception_json['traceback'] = traceback_message
            return create_json_response(exception_json, status=_get_exception_status_code(exception))
        return None

class LogRequestMiddleware(MiddlewareMixin):

    @staticmethod
    def process_response(request, response):
        # conforms to the httpRequest json spec for stackdriver: https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#HttpRequest
        http_json = {
            'requestMethod': request.method,
            'requestUrl': request.get_raw_uri(),
            'status': response.status_code,
            'responseSize': len(response.content) if hasattr(response, 'content') else request.META.get('CONTENT_LENGTH'),
            'userAgent': request.META.get('HTTP_USER_AGENT'),
            'remoteIp': request.META.get('REMOTE_ADDR'),
            'referer': request.META.get('HTTP_REFERER'),
            'protocol': request.META.get('SERVER_PROTOCOL'),
        }
        request_body = None
        try:
            if request.body:
                request_body = json.loads(request.body)
                # TODO update settings in stackdriver so this isn't neccessary
                if 'password' in request_body:
                    request_body['password'] = '***'
        except (ValueError, RawPostDataException):
            pass

        error = ''
        try:
            response_json = json.loads(response.content)
            error = response_json.get('error')
            if response_json.get('errors'):
                error = '; '.join(response_json['errors'])
        except (ValueError, AttributeError):
            pass

        message = ''
        if response.status_code >= 500:
            level = logger.error
            message = error
        elif response.status_code >= 400 or response.status_code == 504:
            level = logger.warning
            message = error
        else:
            level = logger.info
        level(message, extra={'http_request_json': http_json, 'request_body': request_body, 'user': request.user})

        return response
