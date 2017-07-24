import datetime
from bs4 import BeautifulSoup
import openpyxl as xl

from django.http.response import HttpResponse

from seqr.views.utils.json_utils import _to_title_case


def export_table(filename_prefix, header, rows, file_format):
    """Generates an HTTP response for a table with the given header and rows, exported into the given file_format.

    Args:
        filename_prefix (string): Filename without the extension.
        header (list): List of column names
        rows (list): List of rows, where each row is a list of column values
        file_format (string): "tsv" or "xls"
    Returns:
        Django HttpResponse object with the table data as an attachment.
    """
    for row in rows:
        assert len(header) == len(row), 'len(header) != len(row): %s != %s' % (len(header), len(row))

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
    elif file_format == "xls":
        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename="{}.xlsx"'.format(filename_prefix)
        wb = xl.Workbook(write_only=True)
        ws = wb.create_sheet()
        ws.append(map(_to_title_case, header))
        for row in rows:
            try:
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


def _convert_html_to_plain_text(html_string, remove_line_breaks=False):
    """Returns string after removing all HTML markup.

    Args:
        html_string (str): string with HTML markup
        remove_line_breaks (bool): whether to also remove line breaks and extra white space from string
    """
    if not html_string:
        return ''

    text = BeautifulSoup(html_string, "html.parser").get_text()

    # remove empty lines as well leading and trailing space on non-empty lines
    if remove_line_breaks:
        text = ' '.join(line.strip() for line in text.splitlines() if line.strip())

    return text



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

