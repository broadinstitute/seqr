import datetime
import json
import openpyxl as xl

from django.http.response import HttpResponse

from seqr.models import Individual
from seqr.views.utils.json_utils import _get_json_for_user


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
        ws.append(header)
        for row in rows:
            try:
                ws.append(row)
            except ValueError as e:
                raise ValueError("Unable to append row to xls writer: " + ','.join(row))

        wb.save(response)
        return response
    else:
        raise ValueError("Invalid format: %s" % file_format)


def _convert_html_to_plain_text(html_string):
    """Removes html markup from string - useful for rich-text data"""
    if not html_string:
        return ""

    return html_string.replace('&nbsp;', '').replace('<div>', '').replace('</div>', '\n')


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
        'analysis_summary',
        'analysis_notes',
    ])

    if include_case_review_columns:
        header.extend([
            'internal_case_review_brief_summary',
            'internal_case_review_notes',
        ])

    rows = []
    for f in families:
        row = []
        if include_project_column:
            row.extend([f.project.name or f.project.project_id])

        row.extend([
            f.family_id,
            f.display_name,
            f.created_date,
            f.description,
            f.analysis_summary,
            f.analysis_notes,
        ])

        if include_case_review_columns:
            row.extend([
                _convert_html_to_plain_text(f.internal_case_review_brief_summary),
                _convert_html_to_plain_text(f.internal_case_review_notes),
            ])

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)


def export_individuals(filename_prefix, individuals, file_format, include_project_column=False, include_case_review_columns=False, include_phenotips_columns=False):
    """Export Individuals table.

    Args:
        filename_prefix (string): Filename without the file extension.
        individuals (list): List of Django Individual objects to include in the table
        file_format (string): "xls" or "tsv"
        include_project_column (bool):
        include_case_review_columns (bool):
        include_phenotips_columns (bool):

    Returns:
        Django HttpResponse object with the table data as an attachment.
    """

    header = []
    if include_project_column:
        header.extend(['project'])

    header = [
        'family',
        'individual_id',
        'display_name',
        'paternal_id',
        'maternal_id',
        'sex',
        'affected',
        'created_date',
    ]

    if include_case_review_columns:
        header.extend([
            'case_review_status',
            'case_review_status_last_modified_date',
            'case_review_status_last_modified_by',
        ])

    if include_phenotips_columns:
        phenotips_columns_header = ['phenotips_features_present', 'phenotips_features_not_present', 'paternal_ancestry', 'maternal_ancestry', 'age_of_onset']
        header.extend(phenotips_columns_header)

    rows = []
    for i in individuals:
        row = []
        if include_project_column:
            row.extend([i.family.project.name or i.family.project.project_id])

        row.extend([
            i.family.display_name or i.family.family_id,
            i.individual_id,
            i.display_name,
            i.paternal_id,
            i.maternal_id,
            Individual.SEX_LOOKUP.get(i.sex),
            Individual.AFFECTED_LOOKUP.get(i.affected),
            i.created_date,
        ])

        if include_case_review_columns:
            row.extend([
                Individual.CASE_REVIEW_STATUS_LOOKUP.get(i.case_review_status),
                i.case_review_status_last_modified_date,
                _user_to_string(i.case_review_status_last_modified_by),
            ])

        if include_phenotips_columns:
            if i.phenotips_data:
                phenotips_json = json.loads(i.phenotips_data)
                phenotips_fields = _parse_phenotips_data(phenotips_json)
                row.extend([phenotips_fields[h] for h in phenotips_columns_header])

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)


def _parse_phenotips_data(phenotips_json):
    result = {
        'phenotips_features_present': '',
        'phenotips_features_not_present': '',
        'previously_tested_genes': '',
        'candidate_genes': '',
        'paternal_ancestry': '',
        'maternal_ancestry': '',
        'age_of_onset': '',
    }

    if phenotips_json.get('features'):
        result['phenotips_features_present'] = []
        result['phenotips_features_not_present'] = []
        for feature in phenotips_json.get('features'):
            if feature.get('observed') == 'yes':
                result['phenotips_features_present'].append(feature.get('label'))
            elif feature.get('observed') == 'no':
                result['phenotips_features_not_present'].append(feature.get('label'))
        result['phenotips_features_present'] = ', '.join(result['phenotips_features_present'])
        result['phenotips_features_not_present'] = ', '.join(result['phenotips_features_not_present'])

    if phenotips_json.get('rejectedGenes'):
        result['previously_tested_genes'] = []
        for gene in phenotips_json.get('rejectedGenes'):
            result['previously_tested_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        result['previously_tested_genes'] = ', '.join(result['previously_tested_genes'])

    if phenotips_json.get('genes'):
        result['candidate_genes'] = []
        for gene in phenotips_json.get('genes'):
            result['candidate_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        ', '.join(result['candidate_genes'])

    if phenotips_json.get('ethnicity'):
        ethnicity = phenotips_json.get('ethnicity')
        if ethnicity.get('paternal_ethnicity'):
            result['paternal_ancestry'] = ", ".join(ethnicity.get('paternal_ethnicity'))

        if ethnicity.get('maternal_ethnicity'):
            result['maternal_ancestry'] = ", ".join(ethnicity.get('paternal_ethnicity'))

    if phenotips_json.get('global_age_of_onset'):
        result['age_of_onset'] = ", ".join((a.get('label') for a in phenotips_json.get('global_age_of_onset') if a))

    return result


# def export_projects(filename_prefix, projects, file_format):
#     """Export Projects table.
#
#     Args:
#         filename_prefix (string): Filename wihtout
#         projects (list): List of Django Project objects to include in the table
#         file_format (string): "xls" or "tsv"
#
#     Returns:
#         Django HttpResponse object with the table data as an attachment.
#     """
#     header = []
#     header.extend([
#         'project_id',
#         'name',
#         'description',
#         'created_date',
#     ])
#
# def export_samples(filename_prefix, samples, file_format):
#     """Export Projects table.
#
#     Args:
#         filename_prefix (string): Filename wihtout
#         samples (list): List of Django SequencingSample objects to include in the table
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

