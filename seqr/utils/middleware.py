from django.utils.deprecation import MiddlewareMixin
from seqr.views.utils.json_utils import create_json_response
import settings, traceback


class JsonErrorMiddleware(MiddlewareMixin):

    @staticmethod
    def process_exception(request, exception):
        if request.path.startswith('/api'):
            exception_json = {'message': exception.message}
            if settings.DEBUG:
                exception_json['traceback'] = traceback.format_exc().split('\n')
            return create_json_response(exception_json, status=500)
        return None