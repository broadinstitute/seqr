import datetime
import json
from bs4 import BeautifulSoup
import openpyxl as xl

from django.http.response import HttpResponse

from seqr.models import Individual, Family
from seqr.views.utils.json_utils import _to_title_case


_SEX_TO_EXPORT_VALUE = dict(Individual.SEX_LOOKUP)
_SEX_TO_EXPORT_VALUE['U'] = ''

_AFFECTED_TO_EXPORT_VALUE = dict(Individual.AFFECTED_LOOKUP)
_AFFECTED_TO_EXPORT_VALUE['U'] = ''


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


def _user_to_string(user):
    """Takes a Django User object and returns a string representation"""
    if not user:
        return ''
    return user.email or user.username


def export_families(filename_prefix, families, file_format, include_project_column=False, include_case_review_columns=False):
    """Export Families table.

    Args:
        filename_prefix (string): Filename wihtout
        families (list): List of Django Family objects to include in the table
        file_format (string): "xls" or "tsv"
        include_project_column (bool): whether to add a column with the project name
        include_case_review_columns (bool): whether to include Case Review-related columns
    Returns:
        Django HttpResponse object with the table data as an attachment.
    """
    header = []

    if include_project_column:
        header.extend(['project'])

    header.extend([
        'family_id',
        'display_name',
        'created_date',
        'description',
        'analysis_status',
        'analysis_summary',
        'analysis_notes',
    ])

    if include_case_review_columns:
        header.extend([
            'internal_case_review_summary',
            'internal_case_review_notes',
        ])

    rows = []
    analysis_status_lookup = dict(Family.ANALYSIS_STATUS_CHOICES)
    for f in families:
        row = []
        if include_project_column:
            row.extend([f.project.name or f.project.project_id])

        row.extend([
            f.family_id,
            f.display_name,
            f.created_date,
            f.description,
            analysis_status_lookup.get(f.analysis_status, f.analysis_status),
            _convert_html_to_plain_text(f.analysis_summary, remove_line_breaks=(file_format == 'tsv')),
            _convert_html_to_plain_text(f.analysis_notes, remove_line_breaks=(file_format == 'tsv')),
        ])

        if include_case_review_columns:
            row.extend([
                _convert_html_to_plain_text(f.internal_case_review_summary, remove_line_breaks=(file_format == 'tsv')),
                _convert_html_to_plain_text(f.internal_case_review_notes, remove_line_breaks=(file_format == 'tsv')),
            ])

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)


def export_individuals(
        filename_prefix,
        individuals,
        file_format,
        include_project_column=False,
        include_display_name=False,
        include_dates=False,
        include_case_review_columns=False,
        include_phenotips_columns=False):
    """Export Individuals table.

    Args:
        filename_prefix (string): Filename without the file extension.
        individuals (list): List of Django Individual objects to include in the table
        file_format (string): "xls" or "tsv"
        include_project_column (bool):
        include_display_name (bool):
        include_dates (bool):
        include_case_review_columns (bool):
        include_phenotips_columns (bool):

    Returns:
        Django HttpResponse object with the table data as an attachment.
    """

    header = []
    if include_project_column:
        header.extend(['project'])

    header.extend([
        'family_id',
        'individual_id',
        'paternal_id',
        'maternal_id',
        'sex',
        'affected_status',
        'notes',
    ])

    if include_display_name:
        header.extend(['display_name'])

    if include_dates:
        header.extend(['created_date'])

    if include_case_review_columns:
        header.extend([
            'case_review_status',
            'case_review_status_last_modified_date',
            'case_review_status_last_modified_by',
            'case_review_discussion',
        ])

    if include_phenotips_columns:
        phenotips_columns_header = [
            'phenotips_features_present',
            'phenotips_features_absent',
            'paternal_ancestry',
            'maternal_ancestry',
            'age_of_onset'
        ]
        header.extend(phenotips_columns_header)

    rows = []
    for i in individuals:
        row = []
        if include_project_column:
            row.extend([i.family.project.name or i.family.project.project_id])

        row.extend([
            i.family.family_id,
            i.individual_id,
            i.paternal_id,
            i.maternal_id,
            _SEX_TO_EXPORT_VALUE.get(i.sex),
            _AFFECTED_TO_EXPORT_VALUE.get(i.affected),
            _convert_html_to_plain_text(i.notes),
        ])
        if include_display_name:
            row.extend([i.display_name])
        if include_dates:
            row.extend([i.created_date])

        if include_case_review_columns:
            row.extend([
                Individual.CASE_REVIEW_STATUS_LOOKUP.get(i.case_review_status, ''),
                i.case_review_status_last_modified_date,
                _user_to_string(i.case_review_status_last_modified_by),
                i.case_review_discussion,
            ])

        if include_phenotips_columns:
            if i.phenotips_data:
                phenotips_json = json.loads(i.phenotips_data)
                phenotips_fields = _parse_phenotips_data(phenotips_json)
                row.extend([phenotips_fields[h] for h in phenotips_columns_header])
            else:
                row.extend(['' for h in phenotips_columns_header])

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)


def _parse_phenotips_data(phenotips_json):
    """Takes the phenotips_json dictionary for a give Individual and converts it to a flat
    dictionary of key-value pairs for populating phenotips-related columns in a table.

    Args:
        phenotips_json (dict): The PhenoTips json from an Individual

    Returns:
        Dictionary of key-value pairs
    """

    result = {
        'phenotips_features_present': '',
        'phenotips_features_absent': '',
        'previously_tested_genes': '',
        'candidate_genes': '',
        'paternal_ancestry': '',
        'maternal_ancestry': '',
        'age_of_onset': '',
    }

    if phenotips_json.get('features'):
        result['phenotips_features_present'] = []
        result['phenotips_features_absent'] = []
        for feature in phenotips_json.get('features'):
            if feature.get('observed') == 'yes':
                result['phenotips_features_present'].append(feature.get('label'))
            elif feature.get('observed') == 'no':
                result['phenotips_features_absent'].append(feature.get('label'))
        result['phenotips_features_present'] = ', '.join(result['phenotips_features_present'])
        result['phenotips_features_absent'] = ', '.join(result['phenotips_features_absent'])

    if phenotips_json.get('rejectedGenes'):
        result['previously_tested_genes'] = []
        for gene in phenotips_json.get('rejectedGenes'):
            result['previously_tested_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        result['previously_tested_genes'] = ', '.join(result['previously_tested_genes'])

    if phenotips_json.get('genes'):
        result['candidate_genes'] = []
        for gene in phenotips_json.get('genes'):
            result['candidate_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        result['candidate_genes'] =  ', '.join(result['candidate_genes'])

    if phenotips_json.get('ethnicity'):
        ethnicity = phenotips_json.get('ethnicity')
        if ethnicity.get('paternal_ethnicity'):
            result['paternal_ancestry'] = ", ".join(ethnicity.get('paternal_ethnicity'))

        if ethnicity.get('maternal_ethnicity'):
            result['maternal_ancestry'] = ", ".join(ethnicity.get('maternal_ethnicity'))

    if phenotips_json.get('global_age_of_onset'):
        result['age_of_onset'] = ", ".join((a.get('label') for a in phenotips_json.get('global_age_of_onset') if a))

    return result


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

