import requests
from requests.auth import HTTPBasicAuth
from django.http import HttpResponse
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Hop-by-hop HTTP response headers shouldn't be forwarded.
# More info at: http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
EXCLUDE_HTTP_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate',
    'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
}


def proxy_request(request, url, host=None, scheme=None, method=None, session=None, headers=None, auth_tuple=None,
                  verify=True, filter_request_headers=False, stream=False, data=None, verbose=False):
    method = method if method is not None else request.method
    scheme = scheme if scheme is not None else request.scheme
    auth = HTTPBasicAuth(*auth_tuple) if auth_tuple is not None else None

    if not url.startswith("http"):
        if not url.startswith("/"):
            raise ValueError("%s url doesn't start with /" % url)
        if not host:
            raise ValueError("%s url is a path but no host is specified" % url)
        url = "%s://%s%s" % (scheme, host, url)

    if headers is None:
        # based on https://github.com/mjumbewu/django-proxy/blob/master/proxy/views.py
        # forward common HTTP headers after converting them from Django's all-caps syntax (eg. 'HTTP_RANGE') back to regular HTTP syntax (eg. 'Range')
        headers = {key[5:].replace('_', '-').title(): str(value) for key, value in request.META.iteritems()
                   if key.startswith('HTTP_') and key != 'HTTP_HOST' or
                   (key in ('CONTENT_LENGTH', 'CONTENT_TYPE') and value)}
    headers['Host'] = headers.get('Host', host)
    if filter_request_headers:
        headers = {k: v for k, v in headers.items() if not k.startswith("X-") and not k.lower() in EXCLUDE_HTTP_HEADERS}

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

    proxy_response = HttpResponse(
        content=response_content,
        status=response.status_code,
        reason=response.reason,
        charset=response.encoding
    )

    if verbose:
        from requests_toolbelt.utils import dump
        data = dump.dump_all(response)
        logger.info("===> dump - response_data:\n" + str(data))

        logger.info("  response: <Response: %s> %s" % (response.status_code, response.reason))
        logger.info("  response-headers:")
        for key, value in sorted(response.headers.items(), key=lambda i: i[0]):
            logger.info("<--- %(key)s: %(value)s" % locals())

    for key, value in response.headers.iteritems():
        if key.lower() not in EXCLUDE_HTTP_HEADERS:
            proxy_response[key.title()] = value

    return proxy_response
