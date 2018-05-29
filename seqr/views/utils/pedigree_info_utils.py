"""Utilities for parsing .fam files or other tables that describe individual pedigree structure."""

import collections
import difflib
import os
import logging
import re
import tempfile
import traceback
import xlrd
import xlwt
from django.core.mail import EmailMessage
from django.core.mail.message import EmailMultiAlternatives
from django.utils.html import strip_tags

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
    temp_file = tempfile.NamedTemporaryFile()
    try:
        if filename.endswith('.fam') or filename.endswith('.ped') or filename.endswith('.tsv'):
            rows = parse_rows_from_fam_file(stream)
        elif filename.endswith('.xls') or filename.endswith('.xlsx'):
            rows = parse_rows_from_xls(stream, save_to_path=temp_file.name)
    except Exception as e:
        traceback.print_exc()
        errors.append("Error while parsing file: %(filename)s. %(e)s" % locals())
        return json_records, errors, warnings

    # send merged XLS table
    is_merged_pedigree_sample_manifest = len(rows) > 1 and _is_merged_pedigree_sample_manifest_header_row("\t".join(rows[0]))
    if is_merged_pedigree_sample_manifest:
        logger.info("Parsing merged pedigree-sample-manifest file")
        rows, sample_manifest_rows, kit_id = _parse_merged_pedigree_sample_manifest_format(rows)
    else:
        logger.info("Parsing regular pedigree file")

    # convert to json and validate
    try:
        json_records = convert_fam_file_rows_to_json(rows)
    except ValueError as e:
        errors.append("Error while converting %(filename)s rows to json: %(e)s" % locals())
        return json_records, errors, warnings

    errors, warnings = validate_fam_file_records(json_records)

    if not errors and is_merged_pedigree_sample_manifest:
        with open(temp_file.name) as original_file:
            _send_sample_manifest(sample_manifest_rows, kit_id, original_filename=filename, original_file_stream=original_file, user=user, project=project)

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
            raise ValueError("Row %s contains %d columns, while header contains %s: %s" % (i+1, len(fields), len(header), fields))

        fields = map(lambda s: s.strip(), fields)

        row_dict = dict(zip(header, fields))
        result.append(row_dict)

    return result


def parse_rows_from_xls(stream, save_to_path=None):
    """Parses an Excel table into a list of rows.

    Args:
        stream (object): a file handle or stream for reading the Excel file
        save_to_path (string): (optional) writes out a copy of the stream contents to the given file path
    Returns:
        list: a list of rows where each row is a list of strings corresponding to values in the table
    """
    wb = xlrd.open_workbook(file_contents=stream.read())
    ws = wb.sheet_by_index(0)

    if save_to_path is not None:
        wb_out = xlwt.Workbook()
        ws_out = wb_out.add_sheet(ws.name)

        def copy_row(i_out, ncols):
            [ws_out.write(i_out, j_out, ws.cell(rowx=i_out, colx=j_out).value) for j_out in range(ncols)]

    header = []
    rows = []
    row_idx_iter = iter(range(ws.nrows))
    for i in row_idx_iter:
        if save_to_path is not None:
            copy_row(i, ws.ncols)

        row_fields = [ws.cell(rowx=i, colx=j).value for j in range(ws.ncols)]
        row_string = "\t".join(map(str, row_fields))
        if i == 0 and _is_header_row(row_string):
            header = row_fields
            continue
        elif i == 0 and "do not modify" in row_string.lower() and "Broad" in row_string:
            # the merged pedigree/sample manifest has 3 header rows, so use the known header and skip the next 2 rows.

            row_idx_iter.next() # skip the 2 header rows
            row_idx_iter.next()

            if save_to_path is not None:
                copy_row(i + 1, ws.ncols)
                copy_row(i + 2, ws.ncols)

            # validate manifest_header_row1
            expected_header_columns = MergedPedigreeSampleManifestConstants.MERGED_PEDIGREE_SAMPLE_MANIFEST_COLUMN_NAMES
            expected_header_columns = expected_header_columns[:4] + ["Alias", "Alias"] + expected_header_columns[6:]
            actual_header_columns = [ws.cell(rowx=1, colx=j).value for j in range(len(MergedPedigreeSampleManifestConstants.MERGED_PEDIGREE_SAMPLE_MANIFEST_COLUMN_NAMES))]
            unexpected_header_columns = "\t".join(difflib.unified_diff(expected_header_columns, actual_header_columns)).split("\n")[3:]
            if unexpected_header_columns:
                raise ValueError("Expected vs. actual header columns: " + "\t".join(unexpected_header_columns))

            header = MergedPedigreeSampleManifestConstants.MERGED_PEDIGREE_SAMPLE_MANIFEST_COLUMN_NAMES
            continue
        elif not header:
            raise ValueError("Unexpected header row format: " + row_string)

        parsed_row = []
        for j in range(len(header)):
            try:
                cell = ws.cell(rowx=i, colx=j)
            except Exception as e:
                logger.warn("WARNING: Unable to access cell (%s, %s): %s" % (i, j, e))

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
                raise ValueError("Row %s contains %d columns, while header contains %s: %s" % (i+1, len(parsed_row), len(header), parsed_row))

            row_dict = collections.OrderedDict(zip(header, parsed_row))
            rows.append(row_dict)

    if save_to_path is not None:
        wb_out.save(save_to_path)

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
                    'codedPhenotype': ,
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
            JsonConstants.FAMILY_ID_COLUMN: '',
            JsonConstants.INDIVIDUAL_ID_COLUMN: '',
            JsonConstants.PATERNAL_ID_COLUMN: '',
            JsonConstants.MATERNAL_ID_COLUMN: '',
            JsonConstants.SEX_COLUMN: '',
            JsonConstants.AFFECTED_COLUMN: '',
            JsonConstants.NOTES_COLUMN: '',
            JsonConstants.CODED_PHENOTYPE_COLUMN: '',
            JsonConstants.HPO_TERMS_PRESENT_COLUMN: '',
            JsonConstants.HPO_TERMS_ABSENT_COLUMN: '',
            JsonConstants.FUNDING_SOURCE_COLUMN: '',
            JsonConstants.CASE_REVIEW_STATUS_COLUMN: '',
        }

        # parse
        for key, value in row_dict.items():
            key = key.lower()
            value = value.strip()
            if "family" in key:
                json_record[JsonConstants.FAMILY_ID_COLUMN] = value
            elif "indiv" in key:
                json_record[JsonConstants.INDIVIDUAL_ID_COLUMN] = value
            elif "father" in key or "paternal" in key:
                json_record[JsonConstants.PATERNAL_ID_COLUMN] = value if value != "." else ""
            elif "mother" in key or "maternal" in key:
                json_record[JsonConstants.MATERNAL_ID_COLUMN] = value if value != "." else ""
            elif "sex" in key or "gender" in key:
                json_record[JsonConstants.SEX_COLUMN] = value
            elif "affected" in key:
                json_record[JsonConstants.AFFECTED_COLUMN] = value
            elif key.startswith("notes"):
                json_record[JsonConstants.NOTES_COLUMN] = value
            elif "coded" in key and "phenotype" in key:
                json_record[JsonConstants.CODED_PHENOTYPE_COLUMN] = value
            elif re.match("hpo.*present", key):
                json_record[JsonConstants.HPO_TERMS_PRESENT_COLUMN] = filter(None, map(lambda s: s.strip(), value.split(',')))
            elif re.match("hpo.*absent", key):
                json_record[JsonConstants.HPO_TERMS_ABSENT_COLUMN] = filter(None, map(lambda s: s.strip(), value.split(',')))
            elif key.startswith("funding"):
                json_record[JsonConstants.FUNDING_SOURCE_COLUMN] = value
            elif re.match("case.*review.*status", key):
                json_record[JsonConstants.CASE_REVIEW_STATUS_COLUMN] = value

        # validate
        if not json_record[JsonConstants.FAMILY_ID_COLUMN]:
            raise ValueError("Family Id not specified in row #%d:\n%s" % (i+1, json_record))
        if not json_record[JsonConstants.INDIVIDUAL_ID_COLUMN]:
            raise ValueError("Individual Id not specified in row #%d:\n%s" % (i+1, json_record))

        if json_record[JsonConstants.SEX_COLUMN] == '1' or json_record[JsonConstants.SEX_COLUMN].upper().startswith('M'):
            json_record[JsonConstants.SEX_COLUMN] = 'M'
        elif json_record[JsonConstants.SEX_COLUMN] == '2' or json_record[JsonConstants.SEX_COLUMN].upper().startswith('F'):
            json_record[JsonConstants.SEX_COLUMN] = 'F'
        elif json_record[JsonConstants.SEX_COLUMN] == '0' or not json_record[JsonConstants.SEX_COLUMN] or json_record[JsonConstants.SEX_COLUMN].lower() == 'unknown':
            json_record[JsonConstants.SEX_COLUMN] = 'U'
        else:
            raise ValueError("Invalid value '%s' for sex in row #%d" % (json_record[JsonConstants.SEX_COLUMN], i+1))

        if json_record[JsonConstants.AFFECTED_COLUMN] == '1' or json_record[JsonConstants.AFFECTED_COLUMN].upper() == "U" or json_record[JsonConstants.AFFECTED_COLUMN].lower() == 'unaffected':
            json_record[JsonConstants.AFFECTED_COLUMN] = 'N'
        elif json_record[JsonConstants.AFFECTED_COLUMN] == '2' or json_record[JsonConstants.AFFECTED_COLUMN].upper().startswith('A'):
            json_record[JsonConstants.AFFECTED_COLUMN] = 'A'
        elif json_record[JsonConstants.AFFECTED_COLUMN] == '0' or not json_record[JsonConstants.AFFECTED_COLUMN] or json_record[JsonConstants.AFFECTED_COLUMN].lower() == 'unknown':
            json_record[JsonConstants.AFFECTED_COLUMN] = 'U'
        elif json_record[JsonConstants.AFFECTED_COLUMN]:
            raise ValueError("Invalid value '%s' for affected status in row #%d" % (json_record[JsonConstants.AFFECTED_COLUMN], i+1))

        if json_record[JsonConstants.CASE_REVIEW_STATUS_COLUMN]:
            if json_record[JsonConstants.CASE_REVIEW_STATUS_COLUMN].lower() not in Individual.CASE_REVIEW_STATUS_REVERSE_LOOKUP:
                raise ValueError("Invalid value '%s' in the 'Case Review Status' column in row #%d." % (json_record[JsonConstants.CASE_REVIEW_STATUS_COLUMN], i+1))
            json_record[JsonConstants.CASE_REVIEW_STATUS_COLUMN] = Individual.CASE_REVIEW_STATUS_REVERSE_LOOKUP[json_record[JsonConstants.CASE_REVIEW_STATUS_COLUMN].lower()]

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
    records_by_id = {r[JsonConstants.INDIVIDUAL_ID_COLUMN]: r for r in records}

    errors = []
    warnings = []
    for r in records:
        individual_id = r[JsonConstants.INDIVIDUAL_ID_COLUMN]
        family_id = r.get(JsonConstants.FAMILY_ID_COLUMN) or r['family']['familyId']

        # check maternal and paternal ids for consistency
        for parent_id_type, parent_id, expected_sex in [
            ('father', r[JsonConstants.PATERNAL_ID_COLUMN], 'M'),
            ('mother', r[JsonConstants.MATERNAL_ID_COLUMN], 'F')
        ]:
            if len(parent_id) == 0:
                continue

            # is there a separate record for the parent id?
            if parent_id not in records_by_id:
                warnings.append("%(parent_id)s is the %(parent_id_type)s of %(individual_id)s but doesn't have a separate record in the table" % locals())
                continue

            # is father male and mother female?
            actual_sex = records_by_id[parent_id][JsonConstants.SEX_COLUMN]
            if actual_sex != expected_sex:
                actual_sex_label = dict(Individual.SEX_CHOICES)[actual_sex]
                errors.append("%(parent_id)s is recorded as %(actual_sex_label)s and also as the %(parent_id_type)s of %(individual_id)s" % locals())

            # is the parent in the same family?
            parent = records_by_id[parent_id]
            parent_family_id = parent.get(JsonConstants.FAMILY_ID_COLUMN) or parent['family']['familyId']
            if parent_family_id != family_id:
                errors.append("%(parent_id)s is recorded as the %(parent_id_type)s of %(individual_id)s but they have different family ids: %(parent_family_id)s and %(family_id)s" % locals())

        # check HPO ids
        if r.get(JsonConstants.HPO_TERMS_PRESENT_COLUMN):
            for hpo_id in r[JsonConstants.HPO_TERMS_PRESENT_COLUMN]:
                if not HumanPhenotypeOntology.objects.filter(hpo_id=hpo_id):
                    warnings.append("HPO term in 'HPO Terms Present' column not recognized: %(hpo_id)s" % locals())
        if r.get(JsonConstants.HPO_TERMS_ABSENT_COLUMN):
            for hpo_id in r[JsonConstants.HPO_TERMS_ABSENT_COLUMN]:
                if not HumanPhenotypeOntology.objects.filter(hpo_id=hpo_id):
                    warnings.append("HPO term in 'HPO Terms Absent' column not recognized: %(hpo_id)s" % locals())

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
    else:
        return False


def _is_merged_pedigree_sample_manifest_header_row(header_row):
    """Checks whether these rows are from a file that contains columns from the Broad's sample manifest + pedigree table.
    See #_parse_merged_pedigree_sample_manifest_format docs for format details.

    Args:
        row (string): The 1st row in the file
    """
    if "kit id" in header_row.lower() and "sample id" in header_row.lower():
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
         3-tuple: rows, sample_manifest_rows, kit_id
    """

    c = MergedPedigreeSampleManifestConstants
    kit_id = rows[0][c.KIT_ID_COLUMN]

    RENAME_COLUMNS = {
        MergedPedigreeSampleManifestConstants.FAMILY_ID_COLUMN: JsonConstants.FAMILY_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.COLLABORATOR_PARTICIPANT_ID_COLUMN: JsonConstants.INDIVIDUAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.PATERNAL_ID_COLUMN: JsonConstants.PATERNAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.MATERNAL_ID_COLUMN: JsonConstants.MATERNAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.SEX_COLUMN: JsonConstants.SEX_COLUMN,
        MergedPedigreeSampleManifestConstants.AFFECTED_COLUMN: JsonConstants.AFFECTED_COLUMN,
        MergedPedigreeSampleManifestConstants.COLLABORATOR_SAMPLE_ID_COLUMN: JsonConstants.SAMPLE_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.NOTES_COLUMN: JsonConstants.NOTES_COLUMN,
        MergedPedigreeSampleManifestConstants.CODED_PHENOTYPE_COLUMN: JsonConstants.CODED_PHENOTYPE_COLUMN,
    }

    pedigree_rows = []
    sample_manifest_rows = []
    for row in rows:
        sample_manifest_rows.append({
            column_name: row[column_name] for column_name in MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_COLUMN_NAMES
        })

        pedigree_rows.append({
            RENAME_COLUMNS.get(column_name, column_name): row[column_name] for column_name in MergedPedigreeSampleManifestConstants.MERGED_PEDIGREE_COLUMN_NAMES
        })

    return pedigree_rows, sample_manifest_rows, kit_id


def _send_sample_manifest(sample_manifest_rows, kit_id, original_filename, original_file_stream, user=None, project=None):

    # write out the sample manifest file
    wb = xlwt.Workbook()
    ws = wb.add_sheet(kit_id)

    for i, header_row in enumerate([
        MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_HEADER_ROW1,
        MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_HEADER_ROW2,
    ]):
        for j, header_column in enumerate(header_row):
            ws.write(i, j, header_column)

    for i, row in enumerate(sample_manifest_rows):
        for j, column_key in enumerate(MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_COLUMN_NAMES):
            ws.write(i + 2, j, row[column_key])  # add + 2 to skip 2 header rows

    temp_sample_manifest_file = tempfile.NamedTemporaryFile()
    wb.save(temp_sample_manifest_file.name)
    temp_sample_manifest_file.seek(0)

    sample_manifest_filename = kit_id+'.xlsx'
    logger.info("Sending sample manifest file %s to %s" % (sample_manifest_filename, settings.UPLOADED_PEDIGREE_FILE_RECIPIENTS))

    if user is not None and project is not None:
        email_body = "%(user)s just uploaded pedigree info to %(project)s.\n" % locals()
    else:
        email_body = ""

    email_body += """This email has 2 attached files:

    <b>%(sample_manifest_filename)s</b> is the sample manifest to send to GP.

    <b>%(original_filename)s</b> is the original file uploaded by the user.
    """ % locals()

    email_message = EmailMultiAlternatives(
        subject=kit_id + " Merged Sample Pedigree File",
        body=strip_tags(email_body),
        to=settings.UPLOADED_PEDIGREE_FILE_RECIPIENTS,
        attachments=[
            (sample_manifest_filename, temp_sample_manifest_file.read(), "application/xls"),
            (os.path.basename(original_filename), original_file_stream.read(), "application/xls"),
        ],
    )
    email_message.attach_alternative(email_body, 'text/html')
    email_message.send()


class JsonConstants:
    FAMILY_ID_COLUMN = 'familyId'
    INDIVIDUAL_ID_COLUMN = 'individualId'
    PATERNAL_ID_COLUMN = 'paternalId'
    MATERNAL_ID_COLUMN = 'maternalId'
    SEX_COLUMN = 'sex'
    AFFECTED_COLUMN = 'affected'
    SAMPLE_ID_COLUMN = 'sampleId'
    NOTES_COLUMN = 'notes'
    CODED_PHENOTYPE_COLUMN = 'codedPhenotype'
    HPO_TERMS_PRESENT_COLUMN = 'hpoTermsPresent'
    HPO_TERMS_ABSENT_COLUMN = 'hpoTermsAbsent'
    FUNDING_SOURCE_COLUMN = 'fundingSource'
    CASE_REVIEW_STATUS_COLUMN = 'caseReviewStatus'


class MergedPedigreeSampleManifestConstants:
    FIRST_DATA_ROW_IDX = 3

    KIT_ID_COLUMN = "Kit ID"
    WELL_POSITION_COLUMN = "Well"
    SAMPLE_ID_COLUMN = "Sample ID"     # Broad barcoded ID that is generated by GP auto (ex- SM-133J)
    FAMILY_ID_COLUMN = "Family ID"
    COLLABORATOR_PARTICIPANT_ID_COLUMN = "Collaborator Participant ID"  # denotes individual (ex - BON_UC14)
    COLLABORATOR_SAMPLE_ID_COLUMN = "Collaborator Sample ID"            # denotes aliquot number of individual (ex- BON_UC14_1)
    PATERNAL_ID_COLUMN = "Paternal Sample ID"
    MATERNAL_ID_COLUMN = "Maternal Sample ID"
    SEX_COLUMN = "Gender"
    AFFECTED_COLUMN = "Affected Status"
    VOLUME_COLUMN = "Volume"
    CONCENTRATION_COLUMN = "Concentration"
    NOTES_COLUMN = "Notes"
    CODED_PHENOTYPE_COLUMN = "Coded Phenotype"
    DATA_USE_RESTRICTIONS_COLUMN = "Data Use Restrictions"


    MERGED_PEDIGREE_SAMPLE_MANIFEST_COLUMN_NAMES = [
        KIT_ID_COLUMN,
        WELL_POSITION_COLUMN,
        SAMPLE_ID_COLUMN,
        FAMILY_ID_COLUMN,
        COLLABORATOR_PARTICIPANT_ID_COLUMN,
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

    MERGED_PEDIGREE_COLUMN_NAMES = [
        FAMILY_ID_COLUMN,
        COLLABORATOR_PARTICIPANT_ID_COLUMN,
        PATERNAL_ID_COLUMN,
        MATERNAL_ID_COLUMN,
        SEX_COLUMN,
        AFFECTED_COLUMN,
        COLLABORATOR_SAMPLE_ID_COLUMN,
        NOTES_COLUMN,
        CODED_PHENOTYPE_COLUMN,
        DATA_USE_RESTRICTIONS_COLUMN,
    ]

    SAMPLE_MANIFEST_COLUMN_NAMES = [
        KIT_ID_COLUMN,
        WELL_POSITION_COLUMN,
        SAMPLE_ID_COLUMN,
        COLLABORATOR_PARTICIPANT_ID_COLUMN,
        COLLABORATOR_SAMPLE_ID_COLUMN,
        SEX_COLUMN,
        VOLUME_COLUMN,
        CONCENTRATION_COLUMN,
    ]

    SAMPLE_MANIFEST_HEADER_ROW1 = list(SAMPLE_MANIFEST_COLUMN_NAMES)  # make a copy
    SAMPLE_MANIFEST_HEADER_ROW1[3] = 'Alias'
    SAMPLE_MANIFEST_HEADER_ROW1[4] = 'Alias'

    SAMPLE_MANIFEST_HEADER_ROW2 = [''] * len(SAMPLE_MANIFEST_COLUMN_NAMES)
    SAMPLE_MANIFEST_HEADER_ROW2[1] = 'Position'
    SAMPLE_MANIFEST_HEADER_ROW2[3] = COLLABORATOR_PARTICIPANT_ID_COLUMN
    SAMPLE_MANIFEST_HEADER_ROW2[4] = COLLABORATOR_SAMPLE_ID_COLUMN
    SAMPLE_MANIFEST_HEADER_ROW2[6] = 'ul'
    SAMPLE_MANIFEST_HEADER_ROW2[7] = 'ng/ul'


