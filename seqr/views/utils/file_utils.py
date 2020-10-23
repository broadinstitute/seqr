from io import TextIOWrapper

import csv
import gzip
import hashlib
import json
import logging
import os
import tempfile
import openpyxl as xl

from django.contrib.auth.decorators import login_required

from settings import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def save_temp_file(request):

    try:
        uploaded_file_id, filename, json_records = save_uploaded_file(request)
    except Exception as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    response = {'uploadedFileId': uploaded_file_id}
    if request.GET.get('parsedData'):
        response['parsedData'] = json_records
    else:
        response['info'] = ['Parsed {num_rows} rows from {filename}'.format(num_rows=len(json_records), filename=filename)]

    return create_json_response(response)


def parse_file(filename, stream):
    if filename.endswith('.tsv') or filename.endswith('.fam') or filename.endswith('.ped'):
        return [[s.strip().strip('"') for s in line.rstrip('\n').split('\t')] for line in stream]

    elif filename.endswith('.csv'):
        return [row for row in csv.reader(stream)]

    elif filename.endswith('.xls') or filename.endswith('.xlsx'):
        wb = xl.load_workbook(stream, read_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = [[_parse_excel_string_cell(cell) for cell in row] for row in ws.iter_rows()]
        # trim trailing empty rows
        last_row_index = max(i for i, row in enumerate(rows) if any(val for val in row))
        rows = rows[:last_row_index+1]
        # all rows should have same column count
        last_col_index = max(max(i for i, val in enumerate(row) if val) for row in rows)
        padding = [''] * last_col_index
        rows = [(row + padding)[:last_col_index+1] for row in rows]

        return rows

    elif filename.endswith('.json'):
        return json.loads(stream.read())

    raise ValueError("Unexpected file type: {}".format(filename))


def _parse_excel_string_cell(cell):
    cell_value = cell.value
    if cell_value is not None and cell.data_type == 'n' and int(cell_value) == cell_value:
        cell_value = '{:.0f}'.format(cell_value)
    return cell_value or ''


def _compute_serialized_file_path(uploaded_file_id):
    """Compute local file path, and make sure the directory exists"""

    upload_directory = os.path.join(tempfile.gettempdir(), 'temp_uploads')
    if not os.path.isdir(upload_directory):
        logger.info("Creating directory: " + upload_directory)
        os.makedirs(upload_directory)

    return os.path.join(upload_directory, "temp_upload_{}.json.gz".format(uploaded_file_id))


def save_uploaded_file(request, process_records=None):

    if len(request.FILES) != 1:
        raise ValueError("Received %s files instead of 1" % len(request.FILES))

    # parse file
    stream = next(iter(request.FILES.values()))
    filename = stream._name

    if not filename.endswith('.xls') and not filename.endswith('.xlsx'):
        stream = TextIOWrapper(stream.file, encoding = 'utf-8')

    json_records = parse_file(filename, stream)
    if process_records:
        json_records = process_records(json_records, filename=filename)

    # save json to temporary file
    uploaded_file_id = hashlib.md5(str(json_records).encode('utf-8')).hexdigest()
    serialized_file_path = _compute_serialized_file_path(uploaded_file_id)
    with gzip.open(serialized_file_path, "wt") as f:
        json.dump(json_records, f)

    return uploaded_file_id, filename, json_records


def load_uploaded_file(upload_file_id):
    serialized_file_path = _compute_serialized_file_path(upload_file_id)
    with gzip.open(serialized_file_path, "rt") as f:
        json_records = json.load(f)

    os.remove(serialized_file_path)

    return json_records
