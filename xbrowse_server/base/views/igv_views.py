import os
import re
import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, StreamingHttpResponse, QueryDict
from wsgiref.util import FileWrapper
from django.conf import settings

from django.core.exceptions import PermissionDenied
from xbrowse_server.base.models import Project, Individual
from xbrowse_server.decorators import log_request

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import logging
logger = logging.getLogger()

# Hop-by-hop HTTP response headers shouldn't be forwarded.
# More info at: http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
EXCLUDE_HTTP_HEADERS = set([
        'connection', 'keep-alive', 'proxy-authenticate',
        'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
        'upgrade', 'content-encoding'
])


@login_required
@log_request('fetch_igv_track')
def fetch_igv_track(request, project_id, igv_track_name):

    # make sure user has permissions to access the project
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    individual_id = igv_track_name.split('.')[0]
    individuals = Individual.objects.filter(project=project, indiv_id=individual_id)
    if not individuals:
        return HttpResponse("invalid")
    individual = individuals[0]
    if not individual.bam_file_path:
        return HttpResponse("reads not available for " + individual)

    logger.info("Request: %s %s" % (request.method, request.path))
    absolute_path = os.path.join(settings.READ_VIZ_BAM_PATH, individual.bam_file_path)
    if igv_track_name.endswith(".bai"):
        absolute_path += ".bai"

    logger.info("Proxy Request: %s %s" % (request.method, absolute_path))
    if absolute_path.startswith('http'):
        return fetch_proxy(request, absolute_path)
    else:
        return fetch_local_file(request, absolute_path)


def fetch_proxy(request, path):
    """
    Retrieve the HTTP headers from a WSGI environment dictionary.  See
    https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpRequest.META
    """
    # based on https://github.com/mjumbewu/django-proxy/blob/master/proxy/views.py
    # forward common HTTP headers after converting them from Django's all-caps syntax (eg. 'HTTP_RANGE') back to regular HTTP syntax (eg. 'Range')
    headers = { key[5:].replace('_', '-').title() : value for key, value in request.META.iteritems() if key.startswith('HTTP_') and key != 'HTTP_HOST'}
    response = requests.request(request.method, path, auth=('xbrowse-bams', 'xbrowse-bams'), headers=headers, verify=False)

    proxy_response = HttpResponse(response.content, status=response.status_code)

    for key, value in response.headers.iteritems():
        if key.lower() not in EXCLUDE_HTTP_HEADERS:
            proxy_response[key.title()] = value

    return proxy_response


range_re = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)

def fetch_local_file(request, path):
    # based on https://gist.github.com/dcwatson/cb5d8157a8fa5a4a046e
    size = os.path.getsize(path)
    content_type = 'application/octet-stream'
    range_header = request.META.get('HTTP_RANGE', None)
    if range_header:
        logger.info("Loading range: " + range_header + " from local file " + path)
        range_match = range_re.match(range_header)
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else size - 1
        if last_byte >= size:
            last_byte = size - 1
        length = last_byte - first_byte + 1
        resp = StreamingHttpResponse(RangeFileWrapper(open(path, 'rb'), offset=first_byte, length=length), status=206, content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s/%s' % (first_byte, last_byte, size)
    else:
        logger.info("Loading entire file: " + path)
        resp = StreamingHttpResponse(FileWrapper(open(path, 'rb')), content_type=content_type)
        resp['Content-Length'] = str(size)
    resp['Accept-Ranges'] = 'bytes'
    return resp


class RangeFileWrapper(object):
    def __init__(self, filelike, blksize=8192, offset=0, length=None):
        self.filelike = filelike
        self.filelike.seek(offset, os.SEEK_SET)
        self.remaining = length
        self.blksize = blksize

    def close(self):
        if hasattr(self.filelike, 'close'):
            self.filelike.close()

    def __iter__(self):
        return self

    def next(self):
        if self.remaining is None:
            # If remaining is None, we're reading the entire file.
            data = self.filelike.read(self.blksize)
            if data:
                return data
            raise StopIteration()
        else:
            if self.remaining <= 0:
                raise StopIteration()
            data = self.filelike.read(min(self.remaining, self.blksize))
            if not data:
                raise StopIteration()
            self.remaining -= len(data)
            return data
