"""Utilities for parsing .fam files or other tables that describe families' pedigree structure."""

import logging
import xlrd

from reference_data.models import HumanPhenotypeOntology
from seqr.models import Individual

logger = logging.getLogger(__name__)


def parse_rows_from_fam_file(stream):
    """Parses a .ped or .tsv file into a list of rows.

    Args:
        stream (object): a file handle or stream for iterating over lines in the file
    Returns:
        list: a list of rows where each row is a list of strings corresponding to values in the table
    """

    result = []
    for line in stream:
        if not line or line.startswith('#'):
            continue
        if len(result) == 0 and _is_header_row(line):
            continue

        fields = line.rstrip('\n').split('\t')
        fields = map(lambda s: s.strip(), fields)
        result.append(fields)
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

    rows = []
    for i in range(ws.nrows):
        if i == 0 and _is_header_row(', '.join([ws.cell(rowx=i, colx=j).value for j in range(ws.ncols)])):
            continue

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
            rows.append(parsed_row)

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
    result = []
    for i, row in enumerate(rows):
        fields = map(lambda s: s.strip(), row)

        if len(fields) < 6:
            raise ValueError("Row %s contains only %s columns instead of 6" % (i+1, len(fields)))

        family_id = fields[0]
        if not family_id:
            raise ValueError("Row %s is missing a family id: %s" % (i+1, str(row)))

        individual_id = fields[1]
        if not individual_id:
            raise ValueError("Row %s is missing an individual id: %s" % (i+1, str(row)))

        paternal_id = fields[2]
        if paternal_id == ".":
            paternal_id = ""

        maternal_id = fields[3]
        if maternal_id == ".":
            maternal_id = ""

        sex = fields[4]
        if sex == '1' or sex.upper().startswith('M'):
            sex = 'M'
        elif sex == '2' or sex.upper().startswith('F'):
            sex = 'F'
        elif sex == '0' or not sex or sex.lower() == 'unknown':
            sex = 'U'
        else:
            raise ValueError("Invalid value '%s' in the sex column in row #%d" % (str(sex), i+1))

        affected = fields[5]
        if affected == '1' or affected.upper() == "U" or affected.lower() == 'unaffected':
            affected = 'N'
        elif affected == '2' or affected.upper().startswith('A'):
            affected = 'A'
        elif affected == '0' or not affected or affected.lower() == 'unknown':
            affected = 'U'
        elif affected:
            raise ValueError("Invalid value '%s' in the affected status column in row #%d" % (str(affected), i+1))

        notes = fields[6] if len(fields) > 6 else None
        hpo_terms = filter(None, map(lambda s: s.strip(), fields[7].split(','))) if len(fields) > 7 else []

        result.append({
            'familyId': family_id,
            'individualId': individual_id,
            'paternalId': paternal_id,
            'maternalId': maternal_id,
            'sex': sex,
            'affected': affected,
            'notes': notes,
            'hpoTerms': hpo_terms, # unknown
        })

    return result


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
        if r['hpoTerms']:
            for hpo_id in r['hpoTerms']:
                if not HumanPhenotypeOntology.objects.filter(hpo_id=hpo_id):
                    warnings.append("Invalid HPO ID: %(hpo_id)s" % locals())

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

    return False
