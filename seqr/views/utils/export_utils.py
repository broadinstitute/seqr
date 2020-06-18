from __future__ import unicode_literals
from builtins import str

from collections import OrderedDict
import json
import openpyxl as xl
from tempfile import NamedTemporaryFile
import zipfile

from django.http.response import HttpResponse

from seqr.views.utils.json_utils import _to_title_case

DELIMITERS = {
    'csv': ',',
    'tsv': '\t',
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
    def _to_str(s):
        return str(s, 'utf-8', errors = 'ignore') if not isinstance(s, str) else s

    for i, row in enumerate(rows):
        if len(header) != len(row):
            raise ValueError('len(header) != len(row): %s != %s\n%s\n%s' % (len(header), len(row), header, row))
        rows[i] = ['' if value is None else value for value in row]

    if file_format == "tsv":
        response = HttpResponse(content_type='text/tsv')
        response['Content-Disposition'] = 'attachment; filename="{}.tsv"'.format(filename_prefix)
        response.writelines(['\t'.join(header)+'\n'])
        response.writelines(('\t'.join(map(_to_str, row))+'\n' for row in rows))
        return response
    elif file_format == "json":
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="{}.json"'.format(filename_prefix)
        for row in rows:
            json_keys = [s.replace(" ", "_").lower() for s in header]
            json_values = list(map(_to_str, row))
            response.write(json.dumps(OrderedDict(zip(json_keys, json_values)))+'\n')
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
            response['Content-Disposition'] = 'attachment; filename="{}.xlsx"'.format(filename_prefix)
            return response
    else:
        raise ValueError("Invalid file_format: %s" % file_format)


def export_multiple_files(files, zip_filename, file_format='csv', add_header_prefix=False, blank_value=''):
    if file_format not in DELIMITERS:
        raise ValueError('Invalid file_format: {}'.format(file_format))
    with NamedTemporaryFile() as temp_file:
        with zipfile.ZipFile(temp_file, 'w') as zip_file:
            for filename, header, rows in files:
                header_display = header
                if add_header_prefix:
                    header_display = ['{}-{}'.format(str(header_tuple[0]).zfill(2), header_tuple[1]) for header_tuple in enumerate(header)]
                    header_display[0] = header[0]
                content = DELIMITERS[file_format].join(header_display) + '\n'
                content += '\n'.join([
                    DELIMITERS[file_format].join([row.get(key) or blank_value for key in header]) for row in rows
                ])
                if not isinstance(content, str):
                    content = str(content, 'utf-8', errors='ignore')
                zip_file.writestr('{}.{}'.format(filename, file_format), content)
        temp_file.seek(0)
        response = HttpResponse(temp_file, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="{}.zip"'.format(zip_filename)
        return response
