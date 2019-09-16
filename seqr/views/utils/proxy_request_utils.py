import os
import re
import requests
from requests.auth import HTTPBasicAuth
from requests_toolbelt.utils import dump
from django.http import HttpResponse, StreamingHttpResponse
import logging
import urllib3

from settings import READ_VIZ_CRAM_PATH, READ_VIZ_BAM_PATH
from seqr.utils.gcloud.google_bucket_file_utils import is_google_bucket_file_path, google_bucket_file_iter, \
    does_google_bucket_file_exist

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

EXCLUDE_HTTP_REQUEST_HEADERS = {
    'connection', 'x-real-ip', 'x-forwarded-host',
}

# Hop-by-hop HTTP response headers shouldn't be forwarded.
# More info at: http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
EXCLUDE_HTTP_RESPONSE_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate',
    'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade',
}


def proxy_request(request, url, host=None, scheme=None, method=None, session=None, headers=None, auth_tuple=None,
                  verify=True, filter_request_headers=False, stream=False, data=None, verbose=False):
    """
    Proxy a django request to another HTTP server.

    Args:
        request (object): Django request object
        url (string): either a full url or a path relative to 'host'
        host (string): "hostname:port" or "ip-address:port" of target server
        scheme (string): "http" or "https"
        method (string): HTTP request method. Currently supports "GET", "POST", "PUT", "HEAD", "DELETE"
        session (object): requests library Session object
        headers (dict): a dictionary of HTTP request headers to submit instead of the headers in request.META
        auth_tuple (2-tuple): ("username", "password") tuple for basic auth
        verify (bool): whether to validate SSL certificates (setting this to False is not recommended, but can be done
            for backend servers that require https, but use self-signed certificates.
        filter_request_headers (bool): if True, the follow request headers will not be proxied: 'Connection', 'X-Real-Ip', 'X-Forwarded-Host'
        stream (bool): whether the request library should stream the response (see: http://docs.python-requests.org/en/master/user/advanced/#body-content-workflow)
        data (string): request body - used for POST, PUT, etc.
        verbose (bool)

    Returns:
        django.http.HttpResponse: The response returned by the target http server, wrapped in a Django HttpResponse object.

    """
    method = method if method is not None else request.method
    scheme = scheme if scheme is not None else request.scheme
    auth = HTTPBasicAuth(*auth_tuple) if auth_tuple is not None else None

    headers = headers if headers is not None else _convert_django_META_to_http_headers(request.META)
    headers['Host'] = host if host is not None else headers.get('Host')
    if filter_request_headers:
        headers = {k: v for k, v in headers.items() if k.lower() not in EXCLUDE_HTTP_REQUEST_HEADERS}

    if not url.startswith("http"):
        if not url.startswith("/"):
            raise ValueError("%s url doesn't start with /" % url)
        if not host:
            raise ValueError("%s url is a path but no host is specified" % url)
        url = "%s://%s%s" % (scheme, host, url)

    if verbose:
        logger.info("Sending %(method)s request to %(url)s" % locals())
        if headers:
            logger.info("  headers:")
            for key, value in sorted(headers.items(), key=lambda i: i[0]):
                logger.info("---> %(key)s: %(value)s" % locals())
        if data:
            logger.info("  data: %(data)s" % locals())
        if auth_tuple:
            logger.info("  auth: %(auth_tuple)s" % locals())

    r = session if session is not None else requests.Session()
    if method == "GET":
        method_impl = r.get
    elif method == "POST":
        method_impl = r.post
    elif method == "PUT":
        method_impl = r.put
    elif method == "HEAD":
        method_impl = r.head
    elif method == "DELETE":
        method_impl = r.delete
    else:
        raise ValueError("Unexpected HTTP method: %s. %s" % (method, url))

    response = method_impl(url, headers=headers, data=data, auth=auth, stream=stream, verify=verify)
    response_content = response.raw.read() if stream else response.content
    if stream:
        # make sure the connection is released back to the connection pool
        # (based on http://docs.python-requests.org/en/master/user/advanced/#body-content-workflow)
        response.close()

    proxy_response = HttpResponse(
        content=response_content,
        status=response.status_code,
        reason=response.reason,
        charset=response.encoding
    )

    if verbose:
        if not stream:
            data = dump.dump_all(response)
            logger.info("===> dump - response_data:\n" + str(data))

        logger.info("  response: <Response: %s> %s" % (response.status_code, response.reason))
        logger.info("  response-headers:")
        for key, value in sorted(response.headers.items(), key=lambda i: i[0]):
            logger.info("<--- %(key)s: %(value)s" % locals())

    for key, value in response.headers.iteritems():
        if key.lower() not in EXCLUDE_HTTP_RESPONSE_HEADERS:
            proxy_response[key.title()] = value

    return proxy_response


def proxy_to_igv(igv_track_path, params, request=None, **request_kwargs):
    is_cram = igv_track_path.split('?')[0].endswith('.cram')
    if is_google_bucket_file_path(igv_track_path):
        if igv_track_path.endswith('.bam.bai') and not does_google_bucket_file_exist(igv_track_path):
            igv_track_path = igv_track_path.replace('.bam.bai', '.bai')

        return _stream_google_file(request, igv_track_path)
    elif is_cram:
        absolute_path = "/alignments?reference=igvjs/static/data/public/Homo_sapiens_assembly38.fasta&file=igvjs/static/data/readviz-mounts/{0}&options={1}&region={2}".format(
            igv_track_path, params.get('options', ''), params.get('region', ''))
        request_kwargs.update({'host': READ_VIZ_CRAM_PATH, 'stream': True})
    else:
        absolute_path = os.path.join(READ_VIZ_BAM_PATH, igv_track_path)
        request_kwargs.update({'auth_tuple': ('xbrowse-bams', 'xbrowse-bams'), 'verify': False})

    return proxy_request(request, absolute_path, **request_kwargs)


def _convert_django_META_to_http_headers(request_meta_dict):
    """Converts django request.META dictionary into a dictionary of HTTP headers"""

    def convert_key(key):
        # converting Django's all-caps keys (eg. 'HTTP_RANGE') to regular HTTP header keys (eg. 'Range')
        return key.replace("HTTP_", "").replace('_', '-').title()

    http_headers = {
        convert_key(key): str(value)
        for key, value in request_meta_dict.items()
        if key.startswith("HTTP_") or (key in ('CONTENT_LENGTH', 'CONTENT_TYPE') and value)
    }

    return http_headers


def _stream_google_file(request, path):
    # based on https://gist.github.com/dcwatson/cb5d8157a8fa5a4a046e
    content_type = 'application/octet-stream'
    range_header = request.META.get('HTTP_RANGE', None)
    if range_header:
        range_match = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I).match(range_header)
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte)
        length = last_byte - first_byte + 1
        resp = StreamingHttpResponse(
            google_bucket_file_iter(path, byte_range=(first_byte, last_byte)), status=206, content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s' % (first_byte, last_byte)
    else:
        resp = StreamingHttpResponse(google_bucket_file_iter(path), content_type=content_type)
    resp['Accept-Ranges'] = 'bytes'
    return resp
