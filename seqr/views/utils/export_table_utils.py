import datetime
from collections import OrderedDict
import json
import openpyxl as xl

from django.http.response import HttpResponse

from seqr.views.utils.json_utils import _to_title_case


def export_table(filename_prefix, header, rows, file_format, titlecase_header=True):
    """Generates an HTTP response for a table with the given header and rows, exported into the given file_format.

    Args:
        filename_prefix (string): Filename without the extension.
        header (list): List of column names
        rows (list): List of rows, where each row is a list of column values
        file_format (string): "tsv", "xls", or "json"
    Returns:
        Django HttpResponse object with the table data as an attachment.
    """
    if isinstance(header, dict):
        # it's a mapping of row keys to values
        column_keys = header.keys()
        header = list(header.values())
    else:
        column_keys = header

    for i, row in enumerate(rows):
        if isinstance(row, dict):
            for column_key in column_keys:
                if column_key not in row:
                    raise ValueError("row #%d doesn't have key '%s': %s" % (i, column_key, row))
        else:
            if len(header) != len(row):
                raise ValueError('len(header) != len(row): %s != %s\n%s\n%s' % (len(header), len(row), header, row))

        for i, value in enumerate(row):
            if value is None:
                row[i] = ""
            elif type(value) == datetime.datetime:
                row[i] = value.strftime("%m/%d/%Y %H:%M:%S %p %Z")

    if file_format == "tsv":
        response = HttpResponse(content_type='text/tsv')
        response['Content-Disposition'] = 'attachment; filename="{}.tsv"'.format(filename_prefix)
        response.writelines(['\t'.join(header)+'\n'])
        response.writelines(('\t'.join(map(unicode, row))+'\n' for row in rows))
        return response
    elif file_format == "json":
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="{}.json"'.format(filename_prefix)
        for row in rows:
            json_keys = map(lambda s: s.replace(" ", "_").lower(), header)
            json_values = map(unicode, row)
            response.write(json.dumps(OrderedDict(zip(json_keys, json_values)))+'\n')
        return response
    elif file_format == "xls":
        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename="{}.xlsx"'.format(filename_prefix)
        wb = xl.Workbook(write_only=True)
        ws = wb.create_sheet()
        if titlecase_header:
            header = map(_to_title_case, header)
        ws.append(header)
        for row in rows:
            try:
                if isinstance(row, dict):
                    row = [row[column_key] for column_key in column_keys]
                ws.append(row)
            except ValueError as e:
                raise ValueError("Unable to append row to xls writer: " + ','.join(row))

        wb.save(response)
        return response
    else:
        if not file_format:
            raise ValueError("file_format arg not specified")
        else:
            raise ValueError("Invalid file_format: %s" % file_format)


# def export_samples(filename_prefix, samples, file_format):
#     """Export Projects table.
#
#     Args:
#         filename_prefix (string): Filename wihtout
#         samples (list): List of Django Sample objects to include in the table
#         file_format (string): "xls" or "tsv"
#
#     Returns:
#         Django HttpResponse object with the table data as an attachment.
#     """
#     header = []
#     header.extend([
#         'sample_id',
#         'created_date',
#     ])

