"""Utilities for parsing .fam files or other tables that describe individual pedigree structure."""
import difflib
import os
import json
import logging
import tempfile
import openpyxl as xl
from django.core.mail.message import EmailMultiAlternatives
from django.utils.html import strip_tags

from settings import UPLOADED_PEDIGREE_FILE_RECIPIENTS
from seqr.models import Individual

logger = logging.getLogger(__name__)


RELATIONSHIP_REVERSE_LOOKUP = {v.lower(): k for k, v in Individual.RELATIONSHIP_LOOKUP.items()}


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
        rows = [row for row in parsed_file[1:] if row and not (row[0] or '').startswith('#')]

        header_string = str(parsed_file[0])
        is_datstat_upload = 'DATSTAT' in header_string
        is_merged_pedigree_sample_manifest = "do not modify" in header_string.lower() and "Broad" in header_string
        if is_merged_pedigree_sample_manifest:
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
            unexpected_header_columns = '|'.join(difflib.unified_diff(expected, actual)).split('\n')[3:]
            if unexpected_header_columns:
                raise ValueError("Expected vs. actual header columns: {}".format("\t".join(unexpected_header_columns)))

            header = expected_header_columns
        else:
            if _is_header_row(header_string):
                header_row = parsed_file[0]
            else:
                header_row = next(
                    (row for row in parsed_file[1:] if row[0].startswith('#') and _is_header_row(','.join(row))),
                    ['family_id', 'individual_id', 'paternal_id', 'maternal_id', 'sex', 'affected']
                )
            header = [(field or '').strip('#') for field in header_row]

        for i, row in enumerate(rows):
            if len(row) != len(header):
                raise ValueError("Row {} contains {} columns: {}, while header contains {}: {}".format(
                    i + 1, len(row), ', '.join(row), len(header), ', '.join(header)
                ))

        rows = [dict(zip(header, row)) for row in rows]
    except Exception as e:
        errors.append("Error while parsing file: %(filename)s. %(e)s" % locals())
        return json_records, errors, warnings

    # convert to json and validate
    try:
        if is_merged_pedigree_sample_manifest:
            logger.info("Parsing merged pedigree-sample-manifest file")
            rows, sample_manifest_rows, kit_id = _parse_merged_pedigree_sample_manifest_format(rows)
        elif is_datstat_upload:
            logger.info("Parsing datstat export file")
            rows = _parse_datstat_export_format(rows)
        else:
            logger.info("Parsing regular pedigree file")

        json_records = _convert_fam_file_rows_to_json(rows)
    except Exception as e:
        errors.append("Error while converting %(filename)s rows to json: %(e)s" % locals())
        return json_records, errors, warnings

    errors, warnings = validate_fam_file_records(json_records)

    if not errors and is_merged_pedigree_sample_manifest:
        _send_sample_manifest(sample_manifest_rows, kit_id, filename, parsed_file, user, project)

    return json_records, errors, warnings


def _convert_fam_file_rows_to_json(rows):
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
            value = (value or '').strip()
            if key == JsonConstants.FAMILY_NOTES_COLUMN.lower():
                json_record[JsonConstants.FAMILY_NOTES_COLUMN] = value
            elif "family" in key:
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
            elif 'proband' in key and 'relation' in key:
                json_record[JsonConstants.PROBAND_RELATIONSHIP] = value

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

        if json_record.get(JsonConstants.PROBAND_RELATIONSHIP):
            relationship =  RELATIONSHIP_REVERSE_LOOKUP.get(json_record[JsonConstants.PROBAND_RELATIONSHIP].lower())
            if not relationship:
                raise ValueError('Invalid value "{}" for proband relationship in row #{}'.format(
                    json_record[JsonConstants.PROBAND_RELATIONSHIP], i + 1))
            json_record[JsonConstants.PROBAND_RELATIONSHIP] = relationship

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

        # check proband relationship has valid gender
        if r.get(JsonConstants.PROBAND_RELATIONSHIP) and r.get(JsonConstants.SEX_COLUMN):
            invalid_choices = {}
            if r[JsonConstants.SEX_COLUMN] == Individual.SEX_MALE:
                invalid_choices = Individual.FEMALE_RELATIONSHIP_CHOICES
            elif r[JsonConstants.SEX_COLUMN] == Individual.SEX_FEMALE:
                invalid_choices = Individual.MALE_RELATIONSHIP_CHOICES
            if invalid_choices and r[JsonConstants.PROBAND_RELATIONSHIP] in invalid_choices:
                errors.append(
                    'Invalid proband relationship "{relationship}" for {individual_id} with given gender {sex}'.format(
                        relationship=Individual.RELATIONSHIP_LOOKUP[r[JsonConstants.PROBAND_RELATIONSHIP]],
                        individual_id=individual_id,
                        sex=dict(Individual.SEX_CHOICES)[r[JsonConstants.SEX_COLUMN]]
                    ))

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
        MergedPedigreeSampleManifestConstants.COLLABORATOR_SAMPLE_ID_COLUMN: JsonConstants.INDIVIDUAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.PATERNAL_ID_COLUMN: JsonConstants.PATERNAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.MATERNAL_ID_COLUMN: JsonConstants.MATERNAL_ID_COLUMN,
        MergedPedigreeSampleManifestConstants.SEX_COLUMN: JsonConstants.SEX_COLUMN,
        MergedPedigreeSampleManifestConstants.AFFECTED_COLUMN: JsonConstants.AFFECTED_COLUMN,
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


def _send_sample_manifest(sample_manifest_rows, kit_id, original_filename, original_file_rows, user, project):

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

    sample_manifest_filename = kit_id+".xlsx"
    logger.info("Sending sample manifest file %s to %s" % (sample_manifest_filename, UPLOADED_PEDIGREE_FILE_RECIPIENTS))

    original_table_attachment_filename = '{}.xlsx'.format('.'.join(os.path.basename(original_filename).split('.')[:-1]))

    email_body = "User {} just uploaded pedigree info to {}.<br />".format(user.email or user.username, project.name)

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
        to=UPLOADED_PEDIGREE_FILE_RECIPIENTS,
        attachments=[
            (sample_manifest_filename, temp_sample_manifest_file.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            (original_table_attachment_filename, temp_original_file.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ],
    )
    email_message.attach_alternative(email_body, 'text/html')
    email_message.send()


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

    return pedigree_rows


def _get_datstat_family_notes(row):
    row = {k: v.encode('ascii', errors='ignore').decode() for k, v in row.items()}

    DC = DatstatConstants

    def _get_column_val(column):
        val_code = row[column].split(':')[0]
        if column in DC.VALUE_MAP:
            return DC.VALUE_MAP[column][val_code]
        return val_code

    def _get_list_column_val(column):
        return ', '.join([DC.VALUE_MAP[column][raw_val] for raw_val in row[column].split(':')[0].split(',')])

    def _has_test(test):
        return _get_column_val('TESTS.{}'.format(test)) == DC.YES

    def _test_summary(test, name):
        col_config = DC.TEST_DETAIL_COLUMNS[test]

        relatives = json.loads(row[col_config[DC.RELATIVES_KEY]]) if row[col_config[DC.RELATIVES_KEY]] else None

        return '{name}. Year: {year}, Lab: {lab}, Relatives: {relatives}{other_relatives}'.format(
            name=name,
            year=row[col_config[DC.YEAR_KEY]] or 'unspecified',
            lab=row[col_config[DC.LAB_KEY]] or 'unspecified',
            relatives=', '.join(relatives).replace('AuntUncle', 'Aunt or Uncle').replace('NieceNephew', 'Niece or Nephew') if relatives else 'not specified',
            other_relatives=': {}'.format(row[col_config[DC.RELATIVE_SPEC_KEY]] or 'not specified') if 'Other' in (relatives or []) else '',
        )

    def _parent_summary(parent):
        col_config = DC.get_parent_detail_columns(parent)

        def _bool_condition_val(column, yes, no, default, unknown=None):
            column_val = _get_column_val(col_config[column])
            if column_val == DC.YES:
                return yes
            elif column_val == DC.NO:
                return no
            elif unknown and column_val == DC.DONT_KNOW:
                return unknown
            return default

        parent_details = [_bool_condition_val(DC.AFFECTED_KEY, 'affected', 'unaffected', 'unknown affected status')]
        if _get_column_val(col_config[DC.AFFECTED_KEY]) == DC.YES:
            parent_details.append('onset age {}'.format(row[col_config[DC.PARENT_AGE_KEY]]))
        can_participate = _get_column_val(col_config[DC.CAN_PARTICIPATE_KEY]) == DC.YES
        parent_details.append('available' if can_participate else 'unavailable')
        if not can_participate:
            parent_details.append(_bool_condition_val(DC.DECEASED_KEY, yes='deceased', no='living', unknown='unknown deceased status', default='unspecified deceased status'))
        if row[col_config[DC.DECEASED_KEY]] and _get_column_val(col_config[DC.DECEASED_KEY]) == DC.YES:
            parent_details.append(_bool_condition_val(DC.STORED_DNA_KEY, 'sample available', 'sample not available', 'unknown sample availability'))

        return ', '.join(parent_details)

    def _relative_list_summary(relative, all_affected=False):
        col_config = DC.RELATIVE_DETAIL_COLUMNS[relative]
        sex_map = DC.RELATIVE_SEX_MAP[relative]

        if _get_column_val(col_config[DC.NO_RELATIVES_KEY]) == DC.YES:
            return 'None'

        def _bool_condition_val(val, display, unknown_display):
            val = val or ''
            if val.upper() == 'YES':
                return display
            elif val.upper() == 'NO':
                return 'un{}'.format(display)
            return 'unspecified {}'.format(unknown_display)

        relatives = [', '.join([
            sex_map.get(rel['sex']) or sex_map['Other'],
            'age {}'.format(rel['age']),
            'affected' if all_affected else _bool_condition_val(rel['sameCondition'], 'affected', 'affected status'),
            _bool_condition_val(rel['ableToParticipate'], 'available', 'availability'),
        ]) for rel in json.loads(row[col_config[DC.RELATIVES_LIST_KEY]] or '[]') or []]

        divider = '\n{tab}{tab}'.format(tab=DC.TAB)
        return '{divider}{relatives}'.format(
            divider=divider,
            relatives=divider.join(relatives),
        )

    relationship_code = _get_column_val(DC.RELATIONSHIP_COLUMN)
    clinical_diagnoses = _get_column_val(DC.CLINICAL_DIAGNOSES_COLUMN)
    genetic_diagnoses = _get_column_val(DC.GENETIC_DIAGNOSES_COLUMN)
    doctors_list = json.loads(row[DC.DOCTOR_TYPES_COLUMN])

    if _has_test(DC.NONE_TEST):
        testing = 'None'
    elif _has_test(DC.NOT_SURE_TEST):
        testing = 'Not sure'
    else:
        all_tests = []
        for test_col, display in DC.TEST_DISPLAYS:
            if _has_test(test_col):
                if test_col in DC.TEST_DETAIL_COLUMNS:
                    display = _test_summary(test_col, display)
                all_tests.append(display)

        if _has_test(DC.OTHER_TEST):
            all_tests.append('Other tests: {}'.format(row[DC.OTHER_TEST_COLUMN] or 'Unspecified'))

        testing = 'Yes;\n{tab}{tab}{tests}'.format(tab=DC.TAB, tests='\n{0}{0}'.format(DC.TAB).join(all_tests))

    return """#### Clinical Information
{tab} __Patient is my:__ {specified_relationship}{relationship}
{tab} __Current Age:__ {age}
{tab} __Age of Onset:__ {age_of_onset}
{tab} __Race/Ethnicity:__ {race}; {ethnicity}
{tab} __Case Description:__ {description}
{tab} __Clinical Diagnoses:__ {clinical_diagnoses}{clinical_diagnoses_specify}
{tab} __Genetic Diagnoses:__ {genetic_diagnoses}{genetic_diagnoses_specify}
{tab} __Website/Blog:__ {website}
{tab} __Additional Information:__ {info}
#### Prior Testing
{tab} __Referring Physician:__ {physician}
{tab} __Doctors Seen:__ {doctors}{other_doctors}
{tab} __Previous Testing:__ {testing}
{tab} __Biopsies Available:__ {biopses}{other_biopses}
{tab} __Other Research Studies:__ {studies}
#### Family Information
{tab} __Mother:__ {mother}
{tab} __Father:__ {father}
{tab} __Siblings:__ {siblings}
{tab} __Children:__ {children}
{tab} __Relatives:__ {relatives}
    """.format(
        tab=DC.TAB,
        specified_relationship=row[DC.RELATIONSHIP_SPECIFY_COLUMN] or 'Unspecified other relationship'
            if relationship_code == DC.OTHER_RELATIONSHIP_CODE else '',
        relationship=DC.RELATIONSHIP_MAP[relationship_code][_get_column_val(DC.SEX_COLUMN)],
        age='Patient is deceased, age {deceased_age}, due to {cause}, sample {sample_availability}'.format(
            deceased_age=row[DC.DECEASED_AGE_COLUMN],
            cause=(row[DC.DECEASED_CAUSE_COLUMN] or 'unspecified cause').lower(),
            sample_availability=_get_column_val(DC.SAMPLE_AVAILABILITY_COLUMN),
        ) if row[DC.DECEASED_COLUMN] == DC.YES else row[DC.AGE_COLUMN],
        age_of_onset=row[DC.AGE_OF_ONSET_COLUMN],
        race=', '.join(json.loads(row[DC.RACE_COLUMN])),
        ethnicity=_get_column_val(DC.ETHNICITY_COLUMN),
        description=row[DC.DESCRIPTION_COLUMN],
        clinical_diagnoses=clinical_diagnoses,
        clinical_diagnoses_specify='; {}'.format(row[DC.CLINICAL_DIAGNOSES_SPECIFY_COLUMN]) if clinical_diagnoses == 'Yes' else '',
        genetic_diagnoses=genetic_diagnoses,
        genetic_diagnoses_specify='; {}'.format(row[DC.GENETIC_DIAGNOSES_SPECIFY_COLUMN]) if genetic_diagnoses == 'Yes' else '',
        website='Yes' if row[DC.WEBSITE_COLUMN] else 'No',
        info=row[DC.FAMILY_INFO_COLUMN] or 'None specified',
        physician=row[DC.DOCTOR_DETAILS_COLUMN] or 'Not specified' if _get_column_val(DC.HAS_DOCTOR_COLUMN) == DC.YES else 'None',
        doctors=', '.join(doctors_list).replace('ClinGen', 'Clinical geneticist'),
        other_doctors=': {}'.format(row[DC.DOCTOR_TYPES_SPECIFY_COLUMN] or 'Unspecified') if 'Other' in doctors_list else '',
        testing=testing,
        biopses='None' if (_get_column_val(DC.NO_BIOPSY_COLUMN) == DC.YES or not row[DC.BIOPSY_COLUMN]) else _get_list_column_val(DC.BIOPSY_COLUMN),
        other_biopses=': {}'.format(row[DC.OTHER_BIOPSY_COLUMN] or 'Unspecified') if 'OTHER' in row[DC.BIOPSY_COLUMN] else '',
        studies='Yes, Name of studies: {study_names}, Expecting results: {expecting_results}'.format(
            study_names=row[DC.OTHER_STUDIES_COLUMN] or 'Unspecified',
            expecting_results=_get_column_val(DC.EXPECTING_RESULTS_COLUMN) if row[DC.EXPECTING_RESULTS_COLUMN] else 'Unspecified',
        ) if _get_column_val(DC.HAS_OTHER_STUDIES_COLUMN) == DC.YES else 'No',
        mother=_parent_summary(DC.MOTHER),
        father=_parent_summary(DC.FATHER),
        siblings=_relative_list_summary(DC.SIBLINGS),
        children=_relative_list_summary(DC.CHILDREN),
        relatives=_relative_list_summary(DC.OTHER_RELATIVES, all_affected=True),
    )


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
    PROBAND_RELATIONSHIP = 'probandRelationship'
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
    TAB = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'

    YES = '1'
    NO = '2'
    DONT_KNOW = '3'
    YES_NO_UNSURE_MAP = {YES: 'Yes', NO: 'No', DONT_KNOW: 'Unknown/Unsure'}

    FAMILY_ID_COLUMN = 'FAMILY_ID'
    SEX_COLUMN = 'PATIENT_SEX'
    AGE_COLUMN = 'PATIENT_AGE'
    AGE_OF_ONSET_COLUMN = 'CONDITION_AGE'
    DECEASED_AGE_COLUMN = 'DECEASED_AGE'
    DECEASED_CAUSE_COLUMN = 'DECEASED_CAUSE'
    DECEASED_COLUMN = 'PATIENT_DECEASED'
    RELATIONSHIP_COLUMN = 'RELATIONSHIP'
    RELATIONSHIP_SPECIFY_COLUMN = 'RELATIONSHIP_SPECIFY'
    SAMPLE_AVAILABILITY_COLUMN = 'DECEASED_STORED_SAMPLE'
    RACE_COLUMN = 'RACE_LIST'
    ETHNICITY_COLUMN = 'PTETHNICITY'
    CLINICAL_DIAGNOSES_COLUMN = 'CLINICAL_DIAGNOSES'
    CLINICAL_DIAGNOSES_SPECIFY_COLUMN = 'CLINICAL_DIAGNOSES_SPECIFY'
    GENETIC_DIAGNOSES_COLUMN = 'GENETIC_DIAGNOSES'
    GENETIC_DIAGNOSES_SPECIFY_COLUMN = 'GENETIC_DIAGNOSES_SPECIFY'
    DOCTOR_TYPES_COLUMN = 'DOCTOR_TYPES_LIST'
    DOCTOR_TYPES_SPECIFY_COLUMN = 'DOCTOR_TYPES_SPECIFY'
    HAS_DOCTOR_COLUMN = 'FIND_OUT.DOCTOR'
    DOCTOR_DETAILS_COLUMN = 'FIND_OUT_DOCTOR_DETAILS'
    DESCRIPTION_COLUMN = 'DESCRIPTION'
    FAMILY_INFO_COLUMN = 'FAMILY_INFO'
    WEBSITE_COLUMN = 'PATIENT_WEBSITE'
    MICROARRAY_YEAR_COLUMN = 'TESTS_MICROARRAY_YEAR'
    MICROARRAY_LAB_COLUMN = 'TESTS_MICROARRAY_LAB'
    MICROARRAY_RELATIVE_COLUMN = 'TESTS_MICROARRAY_RELATIVE_LIST'
    MICROARRAY_RELATIVE_SPEC_COLUMN = 'TESTS_MICROARRAY_RELATIVE_SPEC'
    OTHER_TEST_COLUMN = 'TEST_OTHER_SPECIFY'
    BIOPSY_COLUMN = 'BIOPSY'
    NO_BIOPSY_COLUMN = 'BIOPSY.NONE'
    OTHER_BIOPSY_COLUMN = 'BIOPSY_OTHER_SPECIFY'
    HAS_OTHER_STUDIES_COLUMN = 'OTHER_GENETIC_STUDIES'
    OTHER_STUDIES_COLUMN = 'OTHER_GENETIC_STUDIES_SPECIFY'
    EXPECTING_RESULTS_COLUMN = 'EXPECTING_GENETIC_RESULTS'

    SEX_OPTION_MAP = {'1': 'MALE', '2': 'FEMALE', '3': 'UNKNOWN'}
    ETHNICITY_COLUMN_MAP = {'1': 'Hispanic', '2': 'Not Hispanic', '3': 'Unknown', '4': 'I prefer not to answer'}
    SAMPLE_AVAILABILITY_MAP = {'1': 'available', '2': 'not available', '3': 'availability unknown'}
    BIOPSY_MAP = {
        biopsy_type: '{} Biopsy'.format(biopsy_type.replace('_', ' ').title())
        for biopsy_type in ['MUSCLE', 'BONE_MARROW', 'LIVER', 'HEART', 'SKIN', 'CRANIOFACIAL']
    }
    BIOPSY_MAP['OTHER'] = 'Other Tissue Biopsy'

    VALUE_MAP = {
        CLINICAL_DIAGNOSES_COLUMN: YES_NO_UNSURE_MAP,
        GENETIC_DIAGNOSES_COLUMN: YES_NO_UNSURE_MAP,
        ETHNICITY_COLUMN: ETHNICITY_COLUMN_MAP,
        EXPECTING_RESULTS_COLUMN: YES_NO_UNSURE_MAP,
        SAMPLE_AVAILABILITY_COLUMN: SAMPLE_AVAILABILITY_MAP,
        BIOPSY_COLUMN: BIOPSY_MAP
    }

    OTHER_RELATIONSHIP_CODE = '6'
    RELATIONSHIP_MAP = {
        '1': {'1': 'Myself (male)', '2': 'Myself (female)', '3': 'Myself (unspecified sex)'},
        '2': {'1': 'Son', '2': 'Daughter', '3': 'Child (unspecified sex)'},
        '3': {'1': 'Brother', '2': 'Sister', '3': 'Sibling (unspecified sex)'},
        '4': {'1': 'Cousin (male)', '2': 'Cousin (female)', '3': 'Cousin (unspecified sex)'},
        '5': {'1': 'Nephew', '2': 'Niece', '3': 'Niece or nephew (unspecified sex)'},
        OTHER_RELATIONSHIP_CODE: {'1': ' (male)', '2': ' (female)', '3': ' (unspecified sex)'},
        '7': {'1': 'Minor Son', '2': 'Minor Daughter', '3': 'Minor Child (unspecified sex)'},
        '8': {
            '1': 'Adult Son - unable to provide consent',
            '2': 'Adult Daughter - unable to provide consent',
            '3': 'Adult Child (unspecified sex) - unable to provide consent',
        },
    }

    NONE_TEST = 'NONE'
    NOT_SURE_TEST = 'NOT_SURE'
    KARYOTYPE_TEST = 'KARYOTYPE'
    SINGLE_GENE_TEST = 'SINGLE_GENE_TESTING'
    GENE_PANEL_TEST = 'GENE_PANEL_TESTING'
    MITOCHON_GENOME_TEST = 'MITOCHON_GENOME_SEQUENCING'
    MICROARRAY_TEST = 'MICROARRAY'
    WES_TEST = 'WEXOME_SEQUENCING'
    WGS_TEST = 'WGENOME_SEQUENCING'
    OTHER_TEST = 'OTHER'

    YEAR_KEY = 'YEAR'
    LAB_KEY = 'LAB'
    RELATIVES_KEY = 'RELATIVES'
    RELATIVE_SPEC_KEY = 'RELATIVE_SPEC'
    TEST_DETAIL_COLUMNS = {
        MICROARRAY_TEST: {
            YEAR_KEY: 'TESTS_MICROARRAY_YEAR',
            LAB_KEY: 'TESTS_MICROARRAY_LAB',
            RELATIVES_KEY: 'TESTS_MICROARRAY_RELATIVE_LIST',
            RELATIVE_SPEC_KEY: 'TESTS_MICROARRAY_RELATIVE_SPEC'
        },
        WES_TEST: {
            YEAR_KEY: 'TESTS_WEXOME_SEQUENCING_YEAR',
            LAB_KEY: 'TESTS_WEXOME_SEQUENCING_LAB',
            RELATIVES_KEY: 'TESTS_WEXOME_SEQUENCING_REL_LI',
            RELATIVE_SPEC_KEY: 'TESTS_WEXOME_SEQUENCING_REL_SP'
        },
        WGS_TEST: {
            YEAR_KEY: 'TESTS_WGENOME_SEQUENCING_YEAR',
            LAB_KEY: 'TESTS_WGENOME_SEQUENCING_LAB',
            RELATIVES_KEY: 'TESTS_WGENOME_SEQUENCING_REL_L',
            RELATIVE_SPEC_KEY: 'ESTS_WGENOME_SEQUENCING_REL_S'
        },
    }

    TEST_DISPLAYS = [
        (KARYOTYPE_TEST, 'Karyotype'),
        (SINGLE_GENE_TEST, 'Single gene testing'),
        (GENE_PANEL_TEST, 'Gene panel testing'),
        (MITOCHON_GENOME_TEST, 'Mitochondrial genome sequencing'),
        (MICROARRAY_TEST, 'Microarray'),
        (WES_TEST, 'Whole exome sequencing'),
        (WGS_TEST, 'Whole genome sequencing'),
    ]

    MOTHER = 'MOM'
    FATHER = 'DAD'
    AFFECTED_KEY = 'SAME_CONDITION'
    PARENT_AGE_KEY = 'CONDITION_AGE'
    CAN_PARTICIPATE_KEY = 'ABLE_TO_PARTICIPATE'
    DECEASED_KEY = 'DECEASED'
    STORED_DNA_KEY = 'STORED_DNA'
    PARENT_DETAIL_FIELDS = [AFFECTED_KEY, PARENT_AGE_KEY, CAN_PARTICIPATE_KEY, DECEASED_KEY, STORED_DNA_KEY]

    SIBLINGS = 'SIBLINGS'
    CHILDREN = 'CHILDREN'
    OTHER_RELATIVES = 'RELATIVES'
    NO_RELATIVES_KEY = 'NO_RELATIVES'
    RELATIVES_LIST_KEY = 'RELATIVES_LIST'
    RELATIVE_DETAIL_COLUMNS = {
        SIBLINGS: {NO_RELATIVES_KEY: 'NO_SIBLINGS', RELATIVES_LIST_KEY: 'SIBLING_LIST'},
        CHILDREN: {NO_RELATIVES_KEY: 'NO_CHILDREN', RELATIVES_LIST_KEY: 'CHILD_LIST'},
        OTHER_RELATIVES: {NO_RELATIVES_KEY: 'NO_RELATIVE_AFFECTED', RELATIVES_LIST_KEY: 'RELATIVE_LIST'},
    }

    RELATIVE_SEX_MAP = {
        SIBLINGS: {'Male': 'Brother', 'Female': 'Sister', 'Other': 'Sibling (unspecified sex)'},
        CHILDREN: {'Male': 'Son', 'Female': 'Daughter', 'Other': 'Child (unspecified sex)'},
        OTHER_RELATIVES: {'Male': 'Male', 'Female': 'Female', 'Other': 'unspecified sex'},
    }

    @classmethod
    def get_parent_detail_columns(cls, parent):
        return {key: '{}_{}'.format(key, parent) for key in cls.PARENT_DETAIL_FIELDS}
