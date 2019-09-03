from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from seqr.views.utils.proxy_request_utils import proxy_to_igv
from settings import API_LOGIN_REQUIRED_URL

import logging
logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def fetch_igv_track(request, project_guid, igv_track_path):

    get_project_and_check_permissions(project_guid, request.user)

    logger.info("Proxy Request: %s %s" % (request.method, igv_track_path))

    return proxy_to_igv(igv_track_path, request.GET, request)
