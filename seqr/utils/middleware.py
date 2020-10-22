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

class LogRequestMiddleware(MiddlewareMixin):

    @staticmethod
    def process_response(request, response):
        # conforms to the httpRequest json spec for stackdriver: https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#HttpRequest
        http_json = {
            'requestMethod': request.method,
            # 'requestUrl': request_env.get('PATH_INFO'),
            # 'requestSize': size,
            'status': response.status_code,
            # 'responseSize': request_env.get('CONTENT_LENGTH'),
            # 'userAgent': request_env.get('HTTP_USER_AGENT'),
            # 'remoteIp': request_env.get('REMOTE_ADDR'),
            # 'serverIp': request_env.get(''),
            # 'referer': request_env.get('HTTP_REFERER'),
            # 'latency': '',
            # 'protocol': request_env.get('SERVER_PROTOCOL'),
        }
        additional_json = {
            'user': request.user.email if request.user else '',
            #'post_body': {},
        }

        if response.status_code >= 500:
            level = logger.error
        elif response.status_code >= 400:
            level = logger.warning
        else:
            level = logger.info
        level('', extra={'http_request_json': http_json, 'additional_http_request_json': additional_json})

        return response
