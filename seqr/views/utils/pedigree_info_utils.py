"""Utilities for parsing .fam files or other tables that describe individual pedigree structure."""

import difflib
import os
import logging
import tempfile
import traceback
import openpyxl as xl
from django.core.mail.message import EmailMultiAlternatives
from django.utils.html import strip_tags

import settings
from seqr.models import Individual

logger = logging.getLogger(__name__)


def parse_pedigree_table(parsed_file, filename, user=None, project=None):
    """Validates and parses pedigree information from a .fam, .tsv, or Excel file.

    Args:
        parsed_file (array): The parsed output from the raw file.
        filename (string): The original filename - used to determine the file format based on the suffix.
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
    is_merged_pedigree_sample_manifest = False

    # parse rows from file
    try:
        rows = [row for row in parsed_file[1:] if row and not row[0].startswith('#')]

        headers = [parsed_file[0]] + [row for row in parsed_file[1:] if row[0].startswith('#')]
        header_string = ','.join(headers[0])
        is_datstat_upload = 'DATSTAT' in header_string
        if "do not modify" in header_string.lower() and "Broad" in header_string:
            # the merged pedigree/sample manifest has 3 header rows, so use the known header and skip the next 2 rows.
            headers = rows[:2]
            rows = rows[2:]

            # validate manifest_header_row1
            expected_header_columns = MergedPedigreeSampleManifestConstants.MERGED_PEDIGREE_SAMPLE_MANIFEST_COLUMN_NAMES
            expected_header_1_columns = expected_header_columns[:4] + ["Alias", "Alias"] + expected_header_columns[6:]

            expected = expected_header_1_columns
            actual = headers[0]
            if expected == actual:
                expected = expected_header_columns[4:6]
                actual = headers[1][4:6]
            unexpected_header_columns = "\t".join(difflib.unified_diff(expected, actual)).split("\n")[3:]
            if unexpected_header_columns:
                raise ValueError("Expected vs. actual header columns: {}".format("\t".join(unexpected_header_columns)))

            header = expected_header_columns
            is_merged_pedigree_sample_manifest = True
        else:
            header = next(
                ([field.strip('#') for field in row] for row in headers if _is_header_row(','.join(row))),
                ['family_id', 'individual_id', 'paternal_id', 'maternal_id', 'sex', 'affected']
            )

        for i, row in enumerate(rows):
            if len(row) != len(header):
                raise ValueError("Row {} contains {} columns: {}, while header contains {}: {}".format(
                    i + 1, len(row), row, len(header), header
                ))

        rows = [dict(zip(header, row)) for row in rows]
    except Exception as e:
        traceback.print_exc()
        errors.append("Error while parsing file: %(filename)s. %(e)s" % locals())
        return json_records, errors, warnings

    if is_merged_pedigree_sample_manifest:
        logger.info("Parsing merged pedigree-sample-manifest file")
        rows, sample_manifest_rows, kit_id = _parse_merged_pedigree_sample_manifest_format(rows)
    elif is_datstat_upload:
        logger.info("Parsing datstat export file")
        rows = _parse_datstat_export_format(rows)
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
        _send_sample_manifest(sample_manifest_rows, kit_id, original_filename=filename, original_file_rows=parsed_file, user=user, project=project)

    return json_records, errors, warnings


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

        json_record = {}

        # parse
        for key, value in row_dict.items():
            key = key.lower()
            value = value.strip()
            if "family" in key:
                json_record[JsonConstants.FAMILY_ID_COLUMN] = value
            elif "indiv" in key:
                if "previous" in key:
                    json_record[JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN] = value
                else:
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

        # validate
        if not json_record.get(JsonConstants.FAMILY_ID_COLUMN):
            raise ValueError("Family Id not specified in row #%d:\n%s" % (i+1, json_record))
        if not json_record.get(JsonConstants.INDIVIDUAL_ID_COLUMN):
            raise ValueError("Individual Id not specified in row #%d:\n%s" % (i+1, json_record))

        if JsonConstants.SEX_COLUMN in json_record:
            if json_record[JsonConstants.SEX_COLUMN] == '1' or json_record[JsonConstants.SEX_COLUMN].upper().startswith('M'):
                json_record[JsonConstants.SEX_COLUMN] = 'M'
            elif json_record[JsonConstants.SEX_COLUMN] == '2' or json_record[JsonConstants.SEX_COLUMN].upper().startswith('F'):
                json_record[JsonConstants.SEX_COLUMN] = 'F'
            elif json_record[JsonConstants.SEX_COLUMN] == '0' or not json_record[JsonConstants.SEX_COLUMN] or json_record[JsonConstants.SEX_COLUMN].lower() == 'unknown':
                json_record[JsonConstants.SEX_COLUMN] = 'U'
            else:
                raise ValueError("Invalid value '%s' for sex in row #%d" % (json_record[JsonConstants.SEX_COLUMN], i+1))

        if JsonConstants.AFFECTED_COLUMN in json_record:
            if json_record[JsonConstants.AFFECTED_COLUMN] == '1' or json_record[JsonConstants.AFFECTED_COLUMN].upper() == "U" or json_record[JsonConstants.AFFECTED_COLUMN].lower() == 'unaffected':
                json_record[JsonConstants.AFFECTED_COLUMN] = 'N'
            elif json_record[JsonConstants.AFFECTED_COLUMN] == '2' or json_record[JsonConstants.AFFECTED_COLUMN].upper().startswith('A'):
                json_record[JsonConstants.AFFECTED_COLUMN] = 'A'
            elif json_record[JsonConstants.AFFECTED_COLUMN] == '0' or not json_record[JsonConstants.AFFECTED_COLUMN] or json_record[JsonConstants.AFFECTED_COLUMN].lower() == 'unknown':
                json_record[JsonConstants.AFFECTED_COLUMN] = 'U'
            elif json_record[JsonConstants.AFFECTED_COLUMN]:
                raise ValueError("Invalid value '%s' for affected status in row #%d" % (json_record[JsonConstants.AFFECTED_COLUMN], i+1))

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
    records_by_id = {r[JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN]: r for r in records
                     if r.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN)}
    records_by_id.update({r[JsonConstants.INDIVIDUAL_ID_COLUMN]: r for r in records})

    errors = []
    warnings = []
    for r in records:
        individual_id = r[JsonConstants.INDIVIDUAL_ID_COLUMN]
        family_id = r.get(JsonConstants.FAMILY_ID_COLUMN) or r['family']['familyId']

        # check maternal and paternal ids for consistency
        for parent_id_type, parent_id, expected_sex in [
            ('father', r.get(JsonConstants.PATERNAL_ID_COLUMN), 'M'),
            ('mother', r.get(JsonConstants.MATERNAL_ID_COLUMN), 'F')
        ]:
            if not parent_id:
                continue

            # is there a separate record for the parent id?
            if parent_id not in records_by_id:
                warnings.append("%(parent_id)s is the %(parent_id_type)s of %(individual_id)s but doesn't have a separate record in the table" % locals())
                continue

            # is father male and mother female?
            if JsonConstants.SEX_COLUMN in records_by_id[parent_id]:
                actual_sex = records_by_id[parent_id][JsonConstants.SEX_COLUMN]
                if actual_sex != expected_sex:
                    actual_sex_label = dict(Individual.SEX_CHOICES)[actual_sex]
                    errors.append("%(parent_id)s is recorded as %(actual_sex_label)s and also as the %(parent_id_type)s of %(individual_id)s" % locals())

            # is the parent in the same family?
            parent = records_by_id[parent_id]
            parent_family_id = parent.get(JsonConstants.FAMILY_ID_COLUMN) or parent['family']['familyId']
            if parent_family_id != family_id:
                errors.append("%(parent_id)s is recorded as the %(parent_id_type)s of %(individual_id)s but they have different family ids: %(parent_family_id)s and %(family_id)s" % locals())

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
    if "family" in row and ("indiv" in row or "datstat" in row):
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


def _parse_datstat_export_format(rows):

    pedigree_rows = []
    for row in rows:
        family_id = 'RGP_{}'.format(row[DatstatConstants.FAMILY_ID_COLUMN])
        maternal_id = '{}_1'.format(family_id)
        paternal_id = '{}_2'.format(family_id)

        proband_row = {
            JsonConstants.FAMILY_ID_COLUMN: family_id,
            JsonConstants.INDIVIDUAL_ID_COLUMN: '{}_3'.format(family_id),
            JsonConstants.MATERNAL_ID_COLUMN: maternal_id,
            JsonConstants.PATERNAL_ID_COLUMN: paternal_id,
            JsonConstants.SEX_COLUMN: DatstatConstants.SEX_OPTION_MAP[row[DatstatConstants.SEX_COLUMN].split(':')[0]],
            JsonConstants.AFFECTED_COLUMN: 'A',
            JsonConstants.FAMILY_NOTES_COLUMN: _get_datstat_family_notes(row),
        }
        mother_row = {
            JsonConstants.FAMILY_ID_COLUMN: family_id,
            JsonConstants.INDIVIDUAL_ID_COLUMN: maternal_id,
            JsonConstants.SEX_COLUMN: 'F',
            JsonConstants.AFFECTED_COLUMN: 'U',
        }
        father_row = {
            JsonConstants.FAMILY_ID_COLUMN: family_id,
            JsonConstants.INDIVIDUAL_ID_COLUMN: paternal_id,
            JsonConstants.SEX_COLUMN: 'M',
            JsonConstants.AFFECTED_COLUMN: 'U',
        }
        pedigree_rows += [mother_row, father_row, proband_row]

        # TODO family notes

    return pedigree_rows


def _get_datstat_family_notes(row):
    """"CLINICAL INFORMATION"&CHAR(10)&Calculations[@relationship]&Ct[@brtb]&Calculations[@Age]&Ct[@brtb]&Calculations[@[Age of Onset]]&Ct[@brtb]&Calculations[@RaceEthnicity]&CHAR(10)&Calculations[@[Case Description]]&Ct[@brtb]&Calculations[@[Clinical Diagnoses]]&Ct[@brtb]&Calculations[@[Genetic Diagnoses]]&Ct[@brtb]&Calculations[@website]&CHAR(10)&Calculations[@InFormation]&CHAR(10)&CHAR(10)&"PRIOR TESTING"&CHAR(10)&Calculations[@[Referring Physician]]&CHAR(10)&Calculations[@[Doctors Seen]]&CHAR(10)&Calculations[@[Previous Testing]]&CHAR(10)&Calculations[@Biopsies]&CHAR(10)&Calculations[@[Other Studies]]&CHAR(10)&CHAR(10)&"FAMILY INFORMATION"&CHAR(10)&Calculations[@mother]&CHAR(10)&Calculations[@father]&CHAR(10)&Calculations[@siblings]&CHAR(10)&Calculations[@children]&CHAR(10)&Calculations[@relatives]"""


def _send_sample_manifest(sample_manifest_rows, kit_id, original_filename, original_file_rows, user=None, project=None):

    # write out the sample manifest file
    wb = xl.Workbook()
    ws = wb.active
    ws.title = "Sample Info"

    ws.append(MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_HEADER_ROW1)
    ws.append(MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_HEADER_ROW2)

    for row in sample_manifest_rows:
        ws.append([row[column_key] for column_key in MergedPedigreeSampleManifestConstants.SAMPLE_MANIFEST_COLUMN_NAMES])

    temp_sample_manifest_file = tempfile.NamedTemporaryFile()
    wb.save(temp_sample_manifest_file.name)
    temp_sample_manifest_file.seek(0)

    sample_manifest_filename = kit_id+".xls"
    logger.info("Sending sample manifest file %s to %s" % (sample_manifest_filename, settings.UPLOADED_PEDIGREE_FILE_RECIPIENTS))

    original_table_attachment_filename = os.path.basename(original_filename).replace(".xlsx", ".xls")

    if user is not None and project is not None:
        user_email_or_username = user.email or user.username
        email_body = "User %(user_email_or_username)s just uploaded pedigree info to %(project)s.<br />" % locals()
    else:
        email_body = ""

    email_body += """This email has 2 attached files:<br />
    <br />
    <b>%(sample_manifest_filename)s</b> is the sample manifest file in a format that can be sent to GP.<br />
    <br />
    <b>%(original_filename)s</b> is the original merged pedigree-sample-manifest file that the user uploaded.<br />
    """ % locals()

    temp_original_file = tempfile.NamedTemporaryFile()
    wb_out = xl.Workbook()
    ws_out = wb_out.active
    for row in original_file_rows:
        ws_out.append(row)
    wb_out.save(temp_original_file.name)
    temp_original_file.seek(0)

    email_message = EmailMultiAlternatives(
        subject=kit_id + " Merged Sample Pedigree File",
        body=strip_tags(email_body),
        to=settings.UPLOADED_PEDIGREE_FILE_RECIPIENTS,
        attachments=[
            (sample_manifest_filename, temp_sample_manifest_file.read(), "application/xls"),
            (original_table_attachment_filename, temp_original_file.read(), "application/xls"),
        ],
    )
    email_message.attach_alternative(email_body, 'text/html')
    email_message.send()


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
        # TODO change this to COLLABORATOR_PARTICIPANT_ID_COLUMN once Sample ids are used for database lookups
        MergedPedigreeSampleManifestConstants.COLLABORATOR_SAMPLE_ID_COLUMN: JsonConstants.INDIVIDUAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.PATERNAL_ID_COLUMN: JsonConstants.PATERNAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.MATERNAL_ID_COLUMN: JsonConstants.MATERNAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.SEX_COLUMN: JsonConstants.SEX_COLUMN,
        MergedPedigreeSampleManifestConstants.AFFECTED_COLUMN: JsonConstants.AFFECTED_COLUMN,
        #MergedPedigreeSampleManifestConstants.COLLABORATOR_SAMPLE_ID_COLUMN: JsonConstants.SAMPLE_ID_COLUMN,
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


class JsonConstants:
    FAMILY_ID_COLUMN = 'familyId'
    INDIVIDUAL_ID_COLUMN = 'individualId'
    PREVIOUS_INDIVIDUAL_ID_COLUMN = 'previousIndividualId'
    PATERNAL_ID_COLUMN = 'paternalId'
    MATERNAL_ID_COLUMN = 'maternalId'
    SEX_COLUMN = 'sex'
    AFFECTED_COLUMN = 'affected'
    SAMPLE_ID_COLUMN = 'sampleId'
    NOTES_COLUMN = 'notes'
    FAMILY_NOTES_COLUMN = 'familyNotes'

    CODED_PHENOTYPE_COLUMN = 'codedPhenotype'

    # staff-only uploads
    #CASE_REVIEW_STATUS_COLUMN = 'caseReviewStatus'

    #POST_DISCOVERY_OMIM_COLUMN = 'postDiscoveryOmim'
    #FUNDING_SOURCE_COLUMN = 'fundingSource'


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
        WELL_POSITION_COLUMN,
        SAMPLE_ID_COLUMN,
        COLLABORATOR_PARTICIPANT_ID_COLUMN,
        COLLABORATOR_SAMPLE_ID_COLUMN,
        SEX_COLUMN,
        VOLUME_COLUMN,
        CONCENTRATION_COLUMN,
    ]

    SAMPLE_MANIFEST_HEADER_ROW1 = list(SAMPLE_MANIFEST_COLUMN_NAMES)  # make a copy
    SAMPLE_MANIFEST_HEADER_ROW1[2] = 'Alias'
    SAMPLE_MANIFEST_HEADER_ROW1[3] = 'Alias'

    SAMPLE_MANIFEST_HEADER_ROW2 = [''] * len(SAMPLE_MANIFEST_COLUMN_NAMES)
    SAMPLE_MANIFEST_HEADER_ROW2[0] = 'Position'
    SAMPLE_MANIFEST_HEADER_ROW2[2] = COLLABORATOR_PARTICIPANT_ID_COLUMN
    SAMPLE_MANIFEST_HEADER_ROW2[3] = COLLABORATOR_SAMPLE_ID_COLUMN
    SAMPLE_MANIFEST_HEADER_ROW2[5] = 'ul'
    SAMPLE_MANIFEST_HEADER_ROW2[6] = 'ng/ul'


class DatstatConstants:
    FAMILY_ID_COLUMN = 'FAMILY_ID'
    SEX_COLUMN = 'PATIENT_SEX'

    SEX_OPTION_MAP = {'1': 'MALE', '2': 'FEMALE', '3': 'UNKNOWN'}
