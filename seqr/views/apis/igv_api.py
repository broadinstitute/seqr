import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from seqr.views.utils.proxy_request_utils import proxy_request

import logging
logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def fetch_igv_track(request, project_guid, igv_track_path):

    get_project_and_check_permissions(project_guid, request.user)

    logger.info("Proxy Request: %s %s" % (request.method, igv_track_path))

    return proxy_to_igv(igv_track_path, request.GET, request)


def proxy_to_igv(igv_track_path, params, request=None, **request_kwargs):
    is_cram = igv_track_path.split('?')[0].endswith('.cram')
    if is_cram:
        absolute_path = "/alignments?reference=igvjs/static/data/public/Homo_sapiens_assembly38.fasta&file=igvjs/static/data/readviz-mounts/{0}&options={1}&region={2}".format(
            igv_track_path, params.get('options', ''), params.get('region', ''))
        request_kwargs.update({'host': 'localhost:5000', 'stream': True})
    else:
        absolute_path = os.path.join('https://localhost', igv_track_path)
        request_kwargs.update({'auth_tuple': ('xbrowse-bams', 'xbrowse-bams'), 'verify': False})

    return proxy_request(request, absolute_path, **request_kwargs)