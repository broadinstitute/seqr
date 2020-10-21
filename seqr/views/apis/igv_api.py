import re
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required

from seqr.utils.file_utils import file_iter, does_file_exist
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from settings import API_LOGIN_REQUIRED_URL

import logging
logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def fetch_igv_track(request, project_guid, igv_track_path):

    get_project_and_check_permissions(project_guid, request.user)

    if igv_track_path.endswith('.bam.bai') and not does_file_exist(igv_track_path):
        igv_track_path = igv_track_path.replace('.bam.bai', '.bai')

    return _stream_file(request, igv_track_path)


def _stream_file(request, path):
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
            file_iter(path, byte_range=(first_byte, last_byte), raw_content=True), status=206, content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s' % (first_byte, last_byte)
    else:
        resp = StreamingHttpResponse(file_iter(path, raw_content=True), content_type=content_type)
    resp['Accept-Ranges'] = 'bytes'
    return resp
