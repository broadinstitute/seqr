"""Utilities for parsing .fam files or other tables that describe individual pedigree structure."""

import logging
import re
import traceback
import xlrd

from reference_data.models import HumanPhenotypeOntology
from seqr.models import Individual

logger = logging.getLogger(__name__)


def parse_pedigree_table(filename, stream):
    """Validates and parses pedigree information from a .fam, .tsv, or Excel file.

    Args:
        filename (string): The original filename - used to determine the file format based on the suffix.
        stream (file): An open input stream object.

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


    # convert to json and validate
    try:
        json_records = convert_fam_file_rows_to_json(rows)
    except ValueError as e:
        errors.append("Error while converting %(filename)s rows to json: %(e)s" % locals())
        return json_records, errors, warnings

    errors, warnings = validate_fam_file_records(json_records)

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
    for i in range(ws.nrows):
        row_fields = [ws.cell(rowx=i, colx=j).value for j in range(ws.ncols)]
        if i == 0 and _is_header_row("\t".join(row_fields)):
            header = row_fields
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

            row_dict = dict(zip(header, parsed_row))
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
                    'hpoTerms': hpo_terms, # unknown
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


def validate_fam_file_records(records, fail_on_warnings=False):
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
        family_id = r.get('familyId') or r['family']['familyId']
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
            parent = records_by_id[parent_id]
            parent_family_id = parent.get('familyId') or parent['family']['familyId']
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

    if fail_on_warnings:
        errors += warnings
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

    return False
