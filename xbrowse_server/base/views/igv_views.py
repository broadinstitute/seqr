import os
import re
import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, StreamingHttpResponse
from django.core.servers.basehttp import FileWrapper
from django.conf import settings

from xbrowse_server.base.models import Project, Individual
from xbrowse_server.decorators import log_request


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



@login_required
@log_request('fetch_igv_track')
def fetch_igv_track(request, project_id, igv_track_name):

    # make sure user has permissions to access the project
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    print('------')
    print("fetch_igv_track " + project_id + " for indiv: " + igv_track_name)

    individual_id = igv_track_name.split('.')[0]
    individuals = Individual.objects.filter(project=project, indiv_id=individual_id)
    if not individuals:
        return HttpResponse("invalid")
    individual = individuals[0]
    if not individual.bam_file_path:
        return HttpResponse("reads not available for " + individual)

    absolute_path = os.path.join(settings.READ_VIZ_BAM_PATH, individual.bam_file_path)
    if igv_track_name.endswith(".bai"):
        absolute_path += ".bai"

    if absolute_path.startswith('http:'):
        return fetch_proxy(request, absolute_path)
    else:
        return fetch_local_file(request, absolute_path)


def fetch_proxy(request, path):

    # based on https://github.com/mjumbewu/django-proxy/blob/master/proxy/views.py
    headers = request.META
    params = request.GET.copy()

    response = requests.request(request.method, path)
    proxy_response = HttpResponse(response.content, status=response.status_code)

    excluded_headers = set([
        # Hop-by-hop headers
        # ------------------
        # Certain response headers should NOT be tunneled through.
        # For more info, see:
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
        'connection', 'keep-alive', 'proxy-authenticate',
        'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
        'upgrade',
    ])
    for key, value in response.headers.iteritems():
        if key.lower() in excluded_headers:
            del proxy_response[key]

    return proxy_response


range_re = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)


def fetch_local_file(request, path):
    # based on https://gist.github.com/dcwatson/cb5d8157a8fa5a4a046e

    size = os.path.getsize(path)
    content_type = 'application/octet-stream'
    range_header = request.META.get('HTTP_RANGE', None)
    if range_header:
        print("Range request received: " + range_header + " for local file " + path)
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
        print("Loading entire file: " + path)
        resp = StreamingHttpResponse(FileWrapper(open(path, 'rb')), content_type=content_type)
        resp['Content-Length'] = str(size)
    resp['Accept-Ranges'] = 'bytes'
    return resp



