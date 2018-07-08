import gzip
import hashlib
import json
import logging
import os
import tempfile
import xlrd


from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def save_temp_file(request):

    try:
        uploaded_file_id, filename, json_records = save_uploaded_file(request, _parse_file)
    except Exception as e:
        return create_json_response({'errors': [e.message]}, status=400)

    return create_json_response({
        'uploadedFileId': uploaded_file_id,
        'info': ['Parsed {num_rows} rows from {filename}'.format(num_rows=len(json_records), filename=filename)],
    })


def _parse_file(filename, stream):
    if filename.endswith('.tsv'):
        return [map(lambda s: s.strip(), line.rstrip('\n').split('\t')) for line in stream]

    elif filename.endswith('.xls') or filename.endswith('.xlsx'):
        wb = xlrd.open_workbook(file_contents=stream.read())
        ws = wb.sheet_by_index(0)
        return [[ws.cell(rowx=i, colx=j).value for j in range(ws.ncols)] for i in iter(range(ws.nrows))]

    raise ValueError("Unexpected file type: {}".format(filename))


def _compute_serialized_file_path(uploaded_file_id):
    """Compute local file path, and make sure the directory exists"""

    upload_directory = os.path.join(tempfile.gettempdir(), 'temp_uploads')
    if not os.path.isdir(upload_directory):
        logger.info("Creating directory: " + upload_directory)
        os.makedirs(upload_directory)

    return os.path.join(upload_directory, "temp_upload_{}.json.gz".format(uploaded_file_id))


def save_uploaded_file(request, parse_file):

    if len(request.FILES) != 1:
        raise ValueError("Received %s files instead of 1" % len(request.FILES))

    # parse file
    stream = request.FILES.values()[0]
    filename = stream._name

    json_records = parse_file(filename, stream)

    # save json to temporary file
    uploaded_file_id = hashlib.md5(str(json_records)).hexdigest()
    serialized_file_path = _compute_serialized_file_path(uploaded_file_id)
    with gzip.open(serialized_file_path, "w") as f:
        json.dump(json_records, f)

    return uploaded_file_id, filename, json_records


def load_uploaded_file(upload_file_id):
    serialized_file_path = _compute_serialized_file_path(upload_file_id)
    with gzip.open(serialized_file_path) as f:
        json_records = json.load(f)

    os.remove(serialized_file_path)

    return json_records
