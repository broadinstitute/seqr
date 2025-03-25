from collections import OrderedDict
import json
import openpyxl as xl
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
import zipfile

from django.http.response import HttpResponse

from seqr.utils.file_utils import mv_file_to_gs, is_google_bucket_file_path
from seqr.views.utils.json_utils import _to_title_case

DELIMITERS = {
    'csv': ',',
    'tsv': '\t',
    'txt': '\t',
}


def export_table(filename_prefix, header, rows, file_format='tsv', titlecase_header=True):
    """Generates an HTTP response for a table with the given header and rows, exported into the given file_format.

    Args:
        filename_prefix (string): Filename without the extension.
        header (list): List of column names
        rows (list): List of rows, where each row is a list of column values
        file_format (string): "tsv", "xls", or "json"
    Returns:
        Django HttpResponse object with the table data as an attachment.
    """

    for i, row in enumerate(rows):
        if len(header) != len(row):
            raise ValueError('len(header) != len(row): %s != %s\n%s\n%s' % (
                len(header), len(row), ','.join(header), ','.join(row)))
        rows[i] = ['' if value is None else value for value in row]

    if file_format == "tsv":
        response = HttpResponse(content_type='text/tsv')
        response['Content-Disposition'] = 'attachment; filename="{}.tsv"'.format(filename_prefix).encode('ascii', 'ignore')
        response.writelines(['\t'.join(header)+'\n'])
        response.writelines(('\t'.join(map(str, row))+'\n' for row in rows))
        return response
    elif file_format == "xls":
        wb = xl.Workbook(write_only=True)
        ws = wb.create_sheet()
        if titlecase_header:
            header = list(map(_to_title_case, header))
        ws.append(header)
        for row in rows:
            ws.append(row)
        with NamedTemporaryFile() as temporary_file:
            wb.save(temporary_file.name)
            temporary_file.seek(0)
            response = HttpResponse(temporary_file.read(), content_type="application/ms-excel")
            response['Content-Disposition'] = 'attachment; filename="{}.xlsx"'.format(filename_prefix).encode('ascii', 'ignore')
            return response
    else:
        raise ValueError("Invalid file_format: %s" % file_format)


def _format_files_content(files, file_format='csv', add_header_prefix=False, blank_value='', file_suffixes=None):
    if file_format and file_format not in DELIMITERS:
        raise ValueError('Invalid file_format: {}'.format(file_format))
    parsed_files = []
    for filename, header, rows in files:
        header_display = header
        if add_header_prefix:
            header_display = ['{}-{}'.format(str(header_tuple[0]).zfill(2), header_tuple[1]) for header_tuple in
                              enumerate(header)]
            header_display[0] = header[0]
        content_rows = [[str(row.get(key) or blank_value) for key in header] for row in rows]
        content = '\n'.join([
            DELIMITERS[file_format].join(row) for row in [header_display] + content_rows
            if any(val != blank_value for val in row)
        ])
        content = str(content.encode('utf-8'), 'ascii', errors='ignore')  # Strip unicode chars in the content
        file_name = '{}.{}'.format(filename, (file_suffixes or {}).get(filename, file_format)) if file_format else filename
        parsed_files.append((file_name, content))
    return parsed_files


def export_multiple_files(files, zip_filename, **kwargs):
    with NamedTemporaryFile() as temp_file:
        with zipfile.ZipFile(temp_file, 'w') as zip_file:
            for filename, content in _format_files_content(files, **kwargs):
                zip_file.writestr(filename, content)
        temp_file.seek(0)
        response = HttpResponse(temp_file, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="{}.zip"'.format(zip_filename).encode('ascii', 'ignore')
        return response


def write_multiple_files(files, file_path, user, **kwargs):
    is_gs_path = is_google_bucket_file_path(file_path)
    if not is_gs_path:
        os.makedirs(file_path, exist_ok=True)
    with TemporaryDirectory() as temp_dir_name:
        dir_name = temp_dir_name if is_gs_path else file_path
        for filename, content in _format_files_content(files, **kwargs):
            with open(f'{dir_name}/{filename}', 'w') as f:
                f.write(content)
        if is_gs_path:
            mv_file_to_gs(f'{temp_dir_name}/*', f'{file_path}/', user)
