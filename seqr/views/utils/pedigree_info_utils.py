"""Utilities for parsing .fam files or other tables that describe individual pedigree structure."""

import collections
import logging
import re
import traceback
import xlrd
import xlwt
from django.core.mail import EmailMessage

import settings
from reference_data.models import HumanPhenotypeOntology
from seqr.models import Individual

logger = logging.getLogger(__name__)


def parse_pedigree_table(filename, stream, user=None, project=None):
    """Validates and parses pedigree information from a .fam, .tsv, or Excel file.

    Args:
        filename (string): The original filename - used to determine the file format based on the suffix.
        stream (file): An open input stream object.
        user (User): (optional) Django User object
        project (Project): (optional) Django Project object

    Return:
        A 3-tuple that contains:
        (
            json_records (list): list of dictionaries, with each dictionary containing info about
                one of the individuals in the input data
            errors (list): list of error message strings
            warnings (list): list of warning message strings
        )
    """

    json_records = []
    errors = []
    warnings = []
    if not any(map(filename.endswith, ['.ped', '.fam', '.tsv', '.xls', '.xlsx'])):
        errors.append("Unexpected file type: %(filename)s" % locals())
        return json_records, errors, warnings

    # parse rows from file
    try:
        if filename.endswith('.fam') or filename.endswith('.ped') or filename.endswith('.tsv'):
            rows = parse_rows_from_fam_file(stream)
        elif filename.endswith('.xls') or filename.endswith('.xlsx'):
            rows = parse_rows_from_xls(stream)
    except Exception as e:
        traceback.print_exc()
        errors.append("Error while parsing file: %(filename)s. %(e)s" % locals())
        return json_records, errors, warnings

    # send merged XLS table
    is_merged_pedigree_sample_manifest = len(rows) > 1 and _is_merged_pedigree_sample_manifest_header_row(rows[0])
    if is_merged_pedigree_sample_manifest:
        original_rows = rows
        rows, sample_manifest_rows, original_rows = _parse_merged_pedigree_sample_manifest_format(rows)

    # convert to json and validate
    try:
        json_records = convert_fam_file_rows_to_json(rows)
    except ValueError as e:
        errors.append("Error while converting %(filename)s rows to json: %(e)s" % locals())
        return json_records, errors, warnings

    errors, warnings = validate_fam_file_records(json_records)

    if not errors and is_merged_pedigree_sample_manifest:
        _send_sample_manifest(sample_manifest_rows, original_rows)

    return json_records, errors, warnings


def parse_rows_from_fam_file(stream):
    """Parses a .ped or .tsv file into a list of rows.

    Args:
        stream (object): a file handle or stream for iterating over lines in the file
    Returns:
        list: a list of rows where each row is a dict that maps column names to values in the table
    """

    header = []
    result = []
    for i, line in enumerate(stream):
        if (i == 0 or line.startswith("#")) and _is_header_row(line):
            header = line.strip('#\n').split('\t')
            continue
        elif not line or line.startswith('#'):
            continue
        elif not header:
            raise ValueError("Header row not found")

        fields = line.rstrip('\n').split('\t')
        if len(fields) != len(header):
            raise ValueError("Row %s contains %d columns, while header contains %s: %s" % (i, len(fields), len(header), fields))

        fields = map(lambda s: s.strip(), fields)

        row_dict = dict(zip(header, fields))
        result.append(row_dict)

    return result


def parse_rows_from_xls(stream):
    """Parses an Excel table into a list of rows.

    Args:
        stream (object): a file handle or stream for reading the Excel file
    Returns:
        list: a list of rows where each row is a list of strings corresponding to values in the table
    """
    wb = xlrd.open_workbook(file_contents=stream.read())
    ws = wb.sheet_by_index(0)

    header = []
    rows = []
    row_idx_iter = range(ws.nrows)
    for i in row_idx_iter:
        row_fields = [ws.cell(rowx=i, colx=j).value for j in range(ws.ncols)]
        row_string = "\t".join(row_fields)
        if i == 0 and _is_header_row(row_string):
            header = row_fields
            continue
        elif i == 0 and _is_merged_pedigree_sample_manifest_header_row(row_string):
            # the merged pedigree/sample manifest has 3 header rows, so use the known header and skip the next 2 rows.
            header = MergedPedigreeSampleManifestConstants.COLUMN_NAMES
            row_idx_iter.next()
            row_idx_iter.next()
            continue
        elif not header:
            raise ValueError("Header row not found")

        parsed_row = []
        for j in range(ws.ncols):
            cell = ws.cell(rowx=i, colx=j)
            cell_value = cell.value
            if not cell_value:
                # if the 1st and 2nd column in a row is empty, treat this as the end of the table
                if j == 0 and (ws.ncols < 2 or not ws.cell(rowx=i, colx=1).value):
                    break
                else:
                    parsed_row.append('')
            else:
                if cell.ctype in (2,3) and int(cell_value) == cell_value:
                    cell_value = int(cell_value)
                parsed_row.append(unicode(cell_value).encode('UTF-8'))
        else:
            # keep this row as part of the table
            if len(parsed_row) != len(header):
                raise ValueError("Row %s contains %d columns, while header contains %s: %s" % (i, len(parsed_row), len(header), parsed_row))

            row_dict = collections.OrderedDict(zip(header, parsed_row))
            rows.append(row_dict)

    return rows


def convert_fam_file_rows_to_json(rows):
    """Parse the values in rows and convert them to a json representation.

    Args:
        rows (list): a list of rows where each row is a list of strings corresponding to values in the table

    Returns:
        list: a list of dictionaries with each dictionary being a json representation of a parsed row.
            For example:
               {
                    'familyId': family_id,
                    'individualId': individual_id,
                    'paternalId': paternal_id,
                    'maternalId': maternal_id,
                    'sex': sex,
                    'affected': affected,
                    'notes': notes,
                    'hpoTermsPresent': [...],
                    'hpoTermsAbsent': [...],
                    'fundingSource': [...],
                    'caseReviewStatus': [...],
                }

    Raises:
        ValueError: if there are unexpected values or row sizes
    """
    json_results = []
    for i, row_dict in enumerate(rows):

        json_record = {
            'familyId': '',
            'individualId': '',
            'paternalId': '',
            'maternalId': '',
            'sex': '',
            'affected': '',
            'notes': '',
            'codedPhenotype': '',
            'hpoTermsPresent': '',
            'hpoTermsAbsent': '',
            'fundingSource': '',
            'caseReviewStatus': '',
        }

        # parse
        for key, value in row_dict.items():
            key = key.lower()
            value = value.strip()
            if "family" in key:
                json_record['familyId'] = value
            elif "indiv" in key:
                json_record['individualId'] = value
            elif "father" in key or "paternal" in key:
                json_record['paternalId'] = value if value != "." else ""
            elif "mother" in key or "maternal" in key:
                json_record['maternalId'] = value if value != "." else ""
            elif "sex" in key or "gender" in key:
                json_record['sex'] = value
            elif "affected" in key:
                json_record['affected'] = value
            elif key.startswith("notes"):
                json_record['notes'] = value
            elif "coded" in key and "phenotype" in key:
                json_record['codedPhenotype'] = value
            elif re.match("hpo.*present", key):
                json_record['hpoTermsPresent'] = filter(None, map(lambda s: s.strip(), value.split(',')))
            elif re.match("hpo.*absent", key):
                json_record['hpoTermsAbsent'] = filter(None, map(lambda s: s.strip(), value.split(',')))
            elif key.startswith("funding"):
                json_record['fundingSource'] = value
            elif re.match("case.*review.*status", key):
                json_record['caseReviewStatus'] = value

        # validate
        if not json_record['familyId']:
            raise ValueError("Family Id not specified in row #%d ." % (i+1))
        if not json_record['individualId']:
            raise ValueError("Individual Id not specified in row #%d" % (i+1))

        if json_record['sex'] == '1' or json_record['sex'].upper().startswith('M'):
            json_record['sex'] = 'M'
        elif json_record['sex'] == '2' or json_record['sex'].upper().startswith('F'):
            json_record['sex'] = 'F'
        elif json_record['sex'] == '0' or not json_record['sex'] or json_record['sex'].lower() == 'unknown':
            json_record['sex'] = 'U'
        else:
            raise ValueError("Invalid value '%s' for sex in row #%d" % (json_record['sex'], i+1))

        if json_record['affected'] == '1' or json_record['affected'].upper() == "U" or json_record['affected'].lower() == 'unaffected':
            json_record['affected'] = 'N'
        elif json_record['affected'] == '2' or json_record['affected'].upper().startswith('A'):
            json_record['affected'] = 'A'
        elif json_record['affected'] == '0' or not json_record['affected'] or json_record['affected'].lower() == 'unknown':
            json_record['affected'] = 'U'
        elif json_record['affected']:
            raise ValueError("Invalid value '%s' for affected status in row #%d" % (json_record['affected'], i+1))

        if json_record['caseReviewStatus']:
            if json_record['caseReviewStatus'].lower() not in Individual.CASE_REVIEW_STATUS_REVERSE_LOOKUP:
                raise ValueError("Invalid value '%s' in the 'Case Review Status' column in row #%d." % (json_record['caseReviewStatus'], i+1))
            json_record['caseReviewStatus'] = Individual.CASE_REVIEW_STATUS_REVERSE_LOOKUP[json_record['caseReviewStatus'].lower()]

        json_results.append(json_record)

    return json_results


def validate_fam_file_records(records):
    """Basic validation such as checking that parents have the same family id as the child, etc.

    Args:
        records (list): a list of dictionaries (see return value of #process_rows).

    Returns:
        dict: json representation of any errors, warnings, or info messages:
            {
                'errors': ['error text1', 'error text2', ...],
                'warnings': ['warning text1', 'warning text2', ...],
                'info': ['info message', ...],
            }
    """
    records_by_id = {r['individualId']: r for r in records}

    errors = []
    warnings = []
    for r in records:
        individual_id = r['individualId']
        family_id = r['familyId']

        # check maternal and paternal ids for consistency
        for parent_id_type, parent_id, expected_sex in [
            ('father', r['paternalId'], 'M'),
            ('mother', r['maternalId'], 'F')
        ]:
            if len(parent_id) == 0:
                continue

            # is there a separate record for the parent id?
            if parent_id not in records_by_id:
                warnings.append("%(parent_id)s is the %(parent_id_type)s of %(individual_id)s but doesn't have a separate record in the table" % locals())
                continue

            # is father male and mother female?
            actual_sex = records_by_id[parent_id]['sex']
            if actual_sex != expected_sex:
                actual_sex_label = dict(Individual.SEX_CHOICES)[actual_sex]
                errors.append("%(parent_id)s is recorded as %(actual_sex_label)s and also as the %(parent_id_type)s of %(individual_id)s" % locals())

            # is the parent in the same family?
            parent_family_id = records_by_id[parent_id]['familyId']
            if parent_family_id != family_id:
                errors.append("%(parent_id)s is recorded as the %(parent_id_type)s of %(individual_id)s but they have different family ids: %(parent_family_id)s and %(family_id)s" % locals())

        # check HPO ids
        if r.get('hpoTerms'):
            for hpo_id in r['hpoTerms']:
                if not HumanPhenotypeOntology.objects.filter(hpo_id=hpo_id):
                    warnings.append("HPO term not recognized: %(hpo_id)s" % locals())

    if errors:
        for error in errors:
            logger.info("ERROR: " + error)

    if warnings:
        for warning in warnings:
            logger.info("WARNING: " + warning)

    return errors, warnings


def _is_header_row(row):
    """Checks if the 1st row of a table is a header row

    Args:
        row (string): 1st row of a table
    Returns:
        True if it's a header row rather than data
    """
    row = row.lower()
    if "sex" in row or "gender" in row:
        return True
    else:
        return False


def _is_merged_pedigree_sample_manifest_header_row(header_row):
    """Checks whether these rows are from a file that contains columns from the Broad's sample manifest + pedigree table.
    See #_parse_merged_pedigree_sample_manifest_format docs for format details.

    Args:
        row (string): The 1st row in the file
    """
    if "do not modify" in header_row.lower() and "broad" in header_row.lower():
        return True
    else:
        return False


def _parse_merged_pedigree_sample_manifest_format(rows):
    """Does post-processing of rows from Broad's sample manifest + pedigree table format. Expected columns are:

    Kit ID, Well Position, Sample ID, Family ID, Collaborator Participant ID, Collaborator Sample ID,
    Paternal Sample ID, Maternal ID, Gender, Affected Status, Volume, Concentration, Notes, Coded Phenotype,
    Data Use Restrictions

    Args:
        rows (list): A list of lists where each list contains values from each column in the table.

    Returns:
         2-tuple: rows, sample_manifest_rows
    """

    c = MergedPedigreeSampleManifestConstants
    kit_id = rows[c.FIRST_DATA_ROW_IDX][c.column_idx[c.KIT_ID_COLUMN]]

    pedigree_rows = []
    sample_manifest_rows = []
    for row in rows[c.FIRST_DATA_ROW_IDX:]:
        pedigree_rows.append({column_name: row[column_name] for column_name in MergedPedigreeSampleManifestConstants.PEDIGREE_COLUMN_NAMES})
        sample_manifest_rows.append({column_name: row[column_name] for column_name in MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_COLUMN_NAMES})


def _send_sample_manifest(sample_manifest_rows, original_rows, kit_id):

    wb = xlwt.Workbook()
    ws = wb.add_sheet(kit_id)

    for i, row in enumerate(sample_manifest_rows):
        for j, column_key in enumerate(MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_COLUMN_NAMES):
            ws.write(i, j, row[column_key])

    filename = kit_id+'.xls'
    wb.save(filename)

    with open(filename) as f:
        email_message = EmailMessage(
            kit_id + " Merged Sample Pedigree File",
            settings.UPLOADED_PEDIGREE_FILE_RECIPIENTS,
            attachments=[(filename, f.read(), "application/xls")],
        )
        email_message.send()

class MergedPedigreeSampleManifestConstants:
    FIRST_DATA_ROW_IDX = 3

    KIT_ID_COLUMN = "Kit ID"
    WELL_POSITION_COLUMN = "Well Position"
    SAMPLE_ID_COLUMN = "Sample ID"
    FAMILY_ID_COLUMN = "Family ID"
    COLLABORATOR_PARTICIPANT_ID_COLUMN = "Collaborator Participant ID"
    COLLABORATOR_SAMPLE_ID_COLUMN = "Collaborator Sample ID"
    PATERNAL_ID_COLUMN = "Paternal Sample ID"
    MATERNAL_ID_COLUMN = "Maternal ID"  # 7
    SEX_COLUMN = "Gender"
    AFFECTED_COLUMN = "Affected Status" # 9
    VOLUME_COLUMN = "Volume"
    CONCENTRATION_COLUMN = "Concentration"
    NOTES_COLUMN = "Notes" #12
    CODED_PHENOTYPE_COLUMN = "Coded Phenotype"
    DATA_USE_RESTRICTIONS_COLUMN = "Data Use Restrictions"

    MERGED_PEDIGREE_SAMPLE_MANIFEST_COLUMN_NAMES = [
        KIT_ID_COLUMN,
        WELL_POSITION_COLUMN,
        SAMPLE_ID_COLUMN,
        FAMILY_ID_COLUMN,
        COLLABORATOR_SAMPLE_ID_COLUMN,
        PATERNAL_ID_COLUMN,
        MATERNAL_ID_COLUMN,
        SEX_COLUMN,
        AFFECTED_COLUMN,
        VOLUME_COLUMN,
        CONCENTRATION_COLUMN,
        NOTES_COLUMN,
        CODED_PHENOTYPE_COLUMN,
        DATA_USE_RESTRICTIONS_COLUMN,
    ]

    PEDIGREE_COLUMN_NAMES = [
        KIT_ID_COLUMN,
        WELL_POSITION_COLUMN,
        SAMPLE_ID_COLUMN,
        FAMILY_ID_COLUMN,
        COLLABORATOR_SAMPLE_ID_COLUMN,
        PATERNAL_ID_COLUMN,
        MATERNAL_ID_COLUMN,
        SEX_COLUMN,
        AFFECTED_COLUMN,
        VOLUME_COLUMN,
        CONCENTRATION_COLUMN,
        NOTES_COLUMN,
        CODED_PHENOTYPE_COLUMN,
        DATA_USE_RESTRICTIONS_COLUMN,
    ]

    SAMPLE_MANIFEST_COLUMN_NAMES = [
        KIT_ID_COLUMN,
        WELL_POSITION_COLUMN,
        SAMPLE_ID_COLUMN,
        FAMILY_ID_COLUMN,
        COLLABORATOR_SAMPLE_ID_COLUMN,
        PATERNAL_ID_COLUMN,
        MATERNAL_ID_COLUMN,
        SEX_COLUMN,
        AFFECTED_COLUMN,
        VOLUME_COLUMN,
        CONCENTRATION_COLUMN,
        NOTES_COLUMN,
        CODED_PHENOTYPE_COLUMN,
        DATA_USE_RESTRICTIONS_COLUMN,
    ]

