from anymail.exceptions import AnymailError
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.handlers.exception import get_exception_response
from django.http import Http404
from django.http.request import RawPostDataException
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin
from django.urls import get_resolver, get_urlconf
import elasticsearch.exceptions
from requests import HTTPError
from social_core.exceptions import AuthException
import json
import traceback

from seqr.utils.elasticsearch.utils import InvalidIndexException, InvalidSearchException
from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.terra_api_utils import TerraAPIException
from settings import DEBUG, LOGIN_URL

logger = SeqrLogger()


class ErrorsWarningsException(Exception):
    def __init__(self, errors, warnings=None):
        """Custom Exception to capture errors and warnings."""
        Exception.__init__(self, str(errors))
        self.errors = errors
        self.warnings = warnings


EXCEPTION_ERROR_MAP = {
    PermissionDenied: 403,
    ObjectDoesNotExist: 404,
    Http404: 404,
    InvalidIndexException: 400,
    InvalidSearchException: 400,
    ErrorsWarningsException: 400,
    AuthException: 401,
    elasticsearch.exceptions.ConnectionError: 504,
    elasticsearch.exceptions.TransportError: lambda e: int(e.status_code) if e.status_code != 'N/A' else 400,
    HTTPError: lambda e: int(e.response.status_code),
    TerraAPIException: lambda e: e.status_code,
    AnymailError: lambda e: getattr(e, 'status_code', None) or 400,
}

EXCEPTION_JSON_MAP = {
    ErrorsWarningsException: lambda e: {'errors': e.errors, 'warnings': e.warnings}
}

EXCEPTION_MESSAGE_MAP = {
    elasticsearch.exceptions.ConnectionError: str,
    elasticsearch.exceptions.TransportError: lambda e: '{}: {} - {} - {}'.format(e.__class__.__name__, e.status_code, repr(e.error), _get_transport_error_type(e.info)),
    TerraAPIException: lambda e: LOGIN_URL if e.status_code == 401 else str(e),
}

ERROR_LOG_EXCEPTIONS = {InvalidIndexException}

def _get_transport_error_type(error):
    error_type = 'no detail'
    if isinstance(error, dict):
        root_cause = error.get('root_cause')
        error_info = error.get('error')
        if (not root_cause) and isinstance(error_info, dict):
            root_cause = error_info.get('root_cause')

        if root_cause:
            error_type = root_cause[0].get('type') or root_cause[0].get('reason')
        elif error_info and not isinstance(error_info, dict):
            error_type = repr(error_info)
    return error_type

def _get_exception_status_code(exception):
    status = next((code for exc, code in EXCEPTION_ERROR_MAP.items() if isinstance(exception, exc)), 500)
    if isinstance(status, int):
        return status

    try:
        return status(exception)
    except Exception:
        return 500

def _get_core_exception_json(exception):
    exception_json_formatter = next((f for exc, f in EXCEPTION_JSON_MAP.items() if isinstance(exception, exc)), None)
    if exception_json_formatter:
        return exception_json_formatter(exception)

    message_func = next((f for exc, f in EXCEPTION_MESSAGE_MAP.items() if isinstance(exception, exc)), str)
    return {'error': message_func(exception)}


class JsonErrorMiddleware(MiddlewareMixin):

    @staticmethod
    def process_exception(request, exception):
        exception_json =  _get_core_exception_json(exception)
        status = _get_exception_status_code(exception)
        if exception.__class__ in ERROR_LOG_EXCEPTIONS:
            exception_json['log_error'] = True
        if DEBUG or status == 500:
            traceback_message = traceback.format_exc()
            exception_json['traceback'] = traceback_message
        detail = getattr(exception, 'info', None)
        if isinstance(detail, dict):
            exception_json['detail'] = detail

        if isinstance(exception, PermissionDenied):
            logger.warning('PermissionDenied: {}'.format(exception_json['error']), request.user)
            exception_json['error'] = 'Permission Denied'

        if request.path.startswith('/api'):
            return create_json_response(exception_json, status=status)

        response = get_exception_response(request, get_resolver(get_urlconf()), status, exception)
        response.data = exception_json
        # LogRequestMiddleware will handle logging for this so do not use standard request logging
        response._has_been_logged = True
        return response

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
                password_keys = [k for k in request_body.keys() if k.startswith('password')]
                for key in password_keys:
                    request_body[key] = '***'
        except (ValueError, AttributeError, RawPostDataException):
            pass

        error = ''
        log_error = False
        traceback = None
        detail = None
        try:
            try:
                response_json = json.loads(response.content)
            except ValueError:
                response_json = response.data

            error = response_json.get('error')
            if response_json.get('errors'):
                error = '; '.join(response_json['errors'])
            traceback = response_json.get('traceback')
            detail = response_json.get('detail')
            log_error = response_json.get('log_error')
        except (ValueError, AttributeError):
            pass

        message = ''
        if log_error or (response.status_code >= 500 and response.status_code != 504):
            level = logger.error
            message = error
        elif response.status_code >= 400:
            level = logger.warning
            message = error
        else:
            level = logger.info
        level(message, request.user, http_request_json=http_json, request_body=request_body, traceback=traceback,
            detail=detail)

        return response


class CacheControlMiddleware(MiddlewareMixin):

    @staticmethod
    def process_response(request, response):
        add_never_cache_headers(response)
        response['Pragma'] = 'no-cache'
        return response
