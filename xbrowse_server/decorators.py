from functools import wraps
import datetime
from django.conf import settings


def log_request(viewname):

    def decorator(f):

        @wraps(f)
        def wrapper(request, *args, **kwargs):

            d = {
                'date': datetime.datetime.now(),
                'page': viewname,
                'ip_addr': request.META['REMOTE_ADDR'],
            }
            if request.user.is_authenticated():
                d['username'] = request.user.username
                d['email'] = request.user.email

            if request.method == 'POST':
                request_data = request.POST
            elif request.method == 'GET':
                request_data = request.GET
            else:
                request_data = None

            if request_data:
                for key in ['project_id', 'family_id', 'search_mode', 'variant_filter',
                            'quality_filter', 'inheritance_mode', 'burden_filter', 'genotype_filter', 'search_hash']:
                    if key in request_data:
                        d[key] = request_data.get(key)

            settings.LOGGING_DB.pageviews.insert(d)

            return f(request, *args, **kwargs)

        return wrapper

    return decorator