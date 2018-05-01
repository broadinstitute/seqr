import os
import requests
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.permissions_utils import get_project_and_check_permissions

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import logging
logger = logging.getLogger(__name__)

# Hop-by-hop HTTP response headers shouldn't be forwarded.
# More info at: http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
EXCLUDE_HTTP_HEADERS = set([
    'connection', 'keep-alive', 'proxy-authenticate',
    'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
])


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def fetch_igv_track(request, project_guid, igv_track_path):

    get_project_and_check_permissions(project_guid, request.user)

    logger.info("Proxy Request: %s %s" % (request.method, igv_track_path))

    # based on https://github.com/mjumbewu/django-proxy/blob/master/proxy/views.py
    # forward common HTTP headers after converting them from Django's all-caps syntax (eg. 'HTTP_RANGE') back to regular HTTP syntax (eg. 'Range')
    headers = {key[5:].replace('_', '-').title(): value for key, value in request.META.iteritems() if key.startswith('HTTP_') and key != 'HTTP_HOST'}

    is_cram = igv_track_path.endswith('.cram')
    if is_cram:
        headers = {key: value for key, value in headers.items() if not key.startswith("X-") and not key.lower() in EXCLUDE_HTTP_HEADERS}
        headers['Host'] = headers.get('Host', settings.READ_VIZ_CRAM_PATH)
        absolute_path = "http://{0}/alignments?reference=igvjs/static/data/public/Homo_sapiens_assembly38.fasta&file=igvjs/static/data/readviz-mounts/{1}&options={2}&region={3}".format(
            settings.READ_VIZ_CRAM_PATH, igv_track_path, request.GET.get('options', ''), request.GET.get('region', ''))
        request_kwargs = {'stream': True}
    else:
        absolute_path = os.path.join(settings.READ_VIZ_BAM_PATH, igv_track_path)
        request_kwargs = {'auth': ('xbrowse-bams', 'xbrowse-bams'), 'verify': False}

    response = requests.request(request.method, absolute_path, headers=headers, **request_kwargs)
    response_content = response.raw.read() if is_cram else response.content

    proxy_response = HttpResponse(response_content, status=response.status_code)
    for key, value in response.headers.iteritems():
        if key.lower() not in EXCLUDE_HTTP_HEADERS:
            proxy_response[key.title()] = value

    return proxy_response
