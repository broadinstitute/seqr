"""Utilities for parsing .fam files or other tables that describe individual pedigree structure."""
import difflib
import os
import json
import tempfile
import openpyxl as xl
from datetime import date
from django.contrib.auth.models import User

from settings import PM_USER_GROUP
from seqr.utils.communication_utils import send_html_email
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.views.utils.permissions_utils import user_is_pm
from seqr.models import Individual

logger = SeqrLogger(__name__)


RELATIONSHIP_REVERSE_LOOKUP = {v.lower(): k for k, v in Individual.RELATIONSHIP_LOOKUP.items()}


def parse_pedigree_table(parsed_file, filename, user, project=None, fail_on_warnings=False):
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

    # parse rows from file
    try:
        rows = [row for row in parsed_file[1:] if row and not (row[0] or '').startswith('#')]

        header_string = str(parsed_file[0])
        is_merged_pedigree_sample_manifest = "do not modify" in header_string.lower() and "Broad" in header_string
        if is_merged_pedigree_sample_manifest:
            if not user_is_pm(user):
                raise ValueError('Unsupported file format')
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
        raise ErrorsWarningsException(['Error while parsing file: {}. {}'.format(filename, e)], [])

    # convert to json and validate
    try:
        if is_merged_pedigree_sample_manifest:
            logger.info("Parsing merged pedigree-sample-manifest file", user)
            rows, sample_manifest_rows, kit_id = _parse_merged_pedigree_sample_manifest_format(rows)
        elif 'participant_guid' in header:
            logger.info("Parsing RGP DSM export file", user)
            rows = _parse_rgp_dsm_export_format(rows)
        else:
            logger.info("Parsing regular pedigree file", user)

        json_records = _convert_fam_file_rows_to_json(rows)
    except Exception as e:
        raise ErrorsWarningsException(['Error while converting {} rows to json: {}'.format(filename, e)], [])

    warnings = validate_fam_file_records(json_records, fail_on_warnings=fail_on_warnings)

    if is_merged_pedigree_sample_manifest:
        _send_sample_manifest(sample_manifest_rows, kit_id, filename, parsed_file, user, project)

    return json_records, warnings


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

        json_record = _parse_row_dict(row_dict)

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
            elif json_record[JsonConstants.SEX_COLUMN] == '0' or not json_record[JsonConstants.SEX_COLUMN] or json_record[JsonConstants.SEX_COLUMN].lower() in {'unknown', 'prefer_not_answer'}:
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


def _parse_row_dict(row_dict):
    json_record = {}
    for key, value in row_dict.items():
        full_key = key
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
        elif full_key in {
            JsonConstants.MATERNAL_ETHNICITY, JsonConstants.PATERNAL_ETHNICITY, JsonConstants.BIRTH_YEAR,
            JsonConstants.DEATH_YEAR, JsonConstants.ONSET_AGE, JsonConstants.AFFECTED_RELATIVES}:
            json_record[full_key] = json.loads(value)
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
    return json_record


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

            # is the parent the same individuals
            if parent_id == individual_id:
                errors.append('{} is recorded as their own {}'.format(parent_id, parent_id_type))

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

    if fail_on_warnings:
        errors += warnings
        warnings = []
    if errors:
        raise ErrorsWarningsException(errors, warnings)
    return warnings


def _is_header_row(row):
    """Checks if the 1st row of a table is a header row

    Args:
        row (string): 1st row of a table
    Returns:
        True if it's a header row rather than data
    """
    row = row.lower()
    if "family" in row and ("indiv" in row or "participant" in row):
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

    recipients = [u.email for u in User.objects.filter(groups__name=PM_USER_GROUP)]

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
    logger.info('Sending sample manifest file {} to {}'.format(sample_manifest_filename, ', '.join(recipients)), user)

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

    send_html_email(
        email_body,
        subject=kit_id + " Merged Sample Pedigree File",
        to=recipients,
        attachments=[
            (sample_manifest_filename, temp_sample_manifest_file.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            (original_table_attachment_filename, temp_original_file.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ],
    )


def _parse_rgp_dsm_export_format(rows):
    pedigree_rows = []
    for row in rows:
        family_id = 'RGP_{}'.format(row[DSMConstants.FAMILY_ID_COLUMN])
        maternal_id = '{}_1'.format(family_id)
        paternal_id = '{}_2'.format(family_id)

        proband_row = {
            JsonConstants.FAMILY_ID_COLUMN: family_id,
            JsonConstants.INDIVIDUAL_ID_COLUMN: '{}_3'.format(family_id),
            JsonConstants.MATERNAL_ID_COLUMN: maternal_id,
            JsonConstants.PATERNAL_ID_COLUMN: paternal_id,
            JsonConstants.AFFECTED_COLUMN: 'A',
        }
        proband_row.update(_get_rgp_dsm_proband_fields(row))

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

def _get_detailed_yes_no(row, column, detail_column):
    val = row[column]
    formatted_val = val.title()
    if val == DSMConstants.YES and row[detail_column]:
        formatted_val = '{}; {}'.format(formatted_val, row[detail_column])
    return formatted_val

def _bool_condition_val(column_val, yes, no, default, unknown=None):
    if column_val == DSMConstants.YES:
        return yes
    elif column_val == DSMConstants.NO:
        return no
    elif unknown and column_val == DSMConstants.UNSURE:
        return unknown
    return default

def _test_summary(row, test):
    test = test.strip()
    if test == DSMConstants.OTHER:
        display = 'Other tests: {}'.format(row[DSMConstants.OTHER_TEST_COLUMN] or 'Unspecified')
    else:
        display = DSMConstants.TEST_DISPLAYS[test]

    if test not in DSMConstants.TEST_DETAIL_COLUMNS:
        return display

    def _get_test_detail(column):
        return row['TESTS_{}_{}'.format(test, column)]

    relatives = _get_test_detail(DSMConstants.RELATIVES_KEY) or 'None Specified'

    return '{name}. Year: {year}, Lab: {lab}, Relatives: {relatives}{other_relatives}'.format(
        name=display,
        year=_get_test_detail(DSMConstants.YEAR_KEY) or 'unspecified',
        lab=_get_test_detail(DSMConstants.LAB_KEY) or 'unspecified',
        relatives=', '.join([rel.strip().title().replace('_', ' or ') for rel in relatives.split(',')]),
        other_relatives=': {}'.format(
            _get_test_detail(DSMConstants.RELATIVE_DETAILS_KEY) or 'not specified') if DSMConstants.OTHER in relatives else '',
    )

def _get_testing(row):
    tests = row[DSMConstants.TESTS_COLUMN]
    if DSMConstants.NONE in tests or not tests:
        return 'None'
    elif DSMConstants.NOT_SURE_TEST in tests:
        return 'Not sure'
    return '\n* * '.join(['Yes;'] + [_test_summary(row, test) for test in tests.split(',')])

def _parent_summary(row, parent):
    parent_values = {
        field: row['{}_{}'.format(parent, field)] for field in DSMConstants.PARENT_DETAIL_FIELDS
    }

    is_affected = parent_values[DSMConstants.AFFECTED_KEY]
    can_participate = parent_values[DSMConstants.CAN_PARTICIPATE_KEY] == DSMConstants.YES
    is_deceased = parent_values[DSMConstants.DECEASED_KEY]

    parent_details = [
        _bool_condition_val(is_affected, 'affected', 'unaffected', 'unknown affected status'),
        'onset age {}'.format(parent_values[DSMConstants.PARENT_AGE_KEY]) if is_affected == DSMConstants.YES else None,
        'available' if can_participate else 'unavailable',
        None if can_participate else _bool_condition_val(
            is_deceased, yes='deceased', no='living', unknown='unknown deceased status',
            default='unspecified deceased status'),
        _bool_condition_val(
            parent_values[DSMConstants.STORED_DNA_KEY], 'sample available', 'sample not available', 'unknown sample availability')
        if is_deceased == DSMConstants.YES else None,
    ]

    return ', '.join(filter(lambda x: x, parent_details))

def _relative_summary(relative, relative_type, all_affected):
    relative_values = {
        field: relative.get('{}_{}'.format(relative_type, field)) for field in DSMConstants.RELATIVE_DETAIL_FIELDS
    }
    sex_map = DSMConstants.RELATIVE_SEX_MAP[relative_type]

    return ', '.join([
        sex_map.get(relative_values[DSMConstants.SEX_KEY]) or sex_map['Other'],
        'age {}'.format(relative_values[DSMConstants.AGE_KEY]),
        'affected' if all_affected else _bool_condition_val(
            relative_values[DSMConstants.SAME_CONDITION_KEY], 'affected', 'unaffected', 'unspecified affected status'),
        _bool_condition_val(relative_values[DSMConstants.CAN_PARTICIPATE_KEY], 'available', 'unavailable', 'unspecified availability'),
    ])

def _relative_list_summary(row, relative, all_affected=False):
    relative_list = _get_rgp_dsm_relative_list(row, relative)
    if relative_list is None:
        return 'None'

    divider = '\n* * '
    return divider + divider.join([_relative_summary(rel, relative, all_affected) for rel in relative_list])

def _get_rgp_dsm_relative_list(row, relative):
    if row[DSMConstants.NO_RELATIVES_COLUMNS[relative]] == DSMConstants.YES:
        return None

    return [rel for rel in json.loads(row[DSMConstants.RELATIVES_LIST_COLUMNS[relative]] or '[]') if rel]

def _get_dsm_races(race_string):
    return [race.strip().title() for race in race_string.split(',') if race]

def _get_dsm_ethnicity(ethnicity):
    return ethnicity.replace('_', ' ').title()

def _get_rgp_dsm_parent_ethnicity(row, parent):
    races = _get_dsm_races(row['{}_{}'.format(parent, DSMConstants.RACE_COLUMN)])
    ethnicity = row['{}_{}'.format(parent, DSMConstants.ETHNICITY_COLUMN)]
    if ethnicity and ethnicity not in {DSMConstants.UNKNOWN, DSMConstants.PREFER_NOT_ANSWER}:
        races.append(_get_dsm_ethnicity(ethnicity))
    return races or None

def _get_rgp_dsm_family_notes(row):
    row = {k: v.encode('ascii', errors='ignore').decode() for k, v in row.items()}

    DC = DSMConstants

    return """#### Clinical Information
* __Patient is my:__ {specified_relationship}{relationship}
* __Current Age:__ {age}
* __Age of Onset:__ {age_of_onset}
* __Race/Ethnicity:__ {race}; {ethnicity}
* __Case Description:__ {description}
* __Clinical Diagnoses:__ {clinical_diagnoses}
* __Genetic Diagnoses:__ {genetic_diagnoses}
* __Website/Blog:__ {website}
* __Additional Information:__ {info}
#### Prior Testing
* __Referring Physician:__ {physician}
* __Doctors Seen:__ {doctors}{other_doctors}
* __Previous Testing:__ {testing}
* __Biopsies Available:__ {biopses}{other_biopses}
* __Other Research Studies:__ {studies}
#### Family Information
* __Mother:__ {mother}
* __Father:__ {father}
* __Siblings:__ {siblings}
* __Children:__ {children}
* __Relatives:__ {relatives}
    """.format(
        specified_relationship=row[DC.RELATIONSHIP_SPECIFY_COLUMN] or 'Unspecified other relationship'
            if row[DC.RELATIONSHIP_COLUMN] == DC.OTHER else '',
        relationship=DC.RELATIONSHIP_MAP[row[DC.RELATIONSHIP_COLUMN]][row[DC.SEX_COLUMN] or DC.PREFER_NOT_ANSWER],
        age='Patient is deceased, age {deceased_age}, due to {cause}, sample {sample_availability}'.format(
            deceased_age=row[DC.DECEASED_AGE_COLUMN],
            cause=(row[DC.DECEASED_CAUSE_COLUMN] or 'unspecified cause').lower(),
            sample_availability=_bool_condition_val(
                row[DC.SAMPLE_AVAILABILITY_COLUMN], 'available', 'not available', 'availability unknown'),
        ) if row[DC.DECEASED_COLUMN] == DC.YES else row[DC.AGE_COLUMN],
        age_of_onset=row[DC.AGE_OF_ONSET_COLUMN],
        race=', '.join(_get_dsm_races(row[DC.RACE_COLUMN])),
        ethnicity=_get_dsm_ethnicity(row[DC.ETHNICITY_COLUMN]) or 'Prefer Not To Answer',
        description=row[DC.DESCRIPTION_COLUMN],
        clinical_diagnoses=_get_detailed_yes_no(row, DC.CLINICAL_DIAGNOSES_COLUMN, DC.CLINICAL_DIAGNOSES_SPECIFY_COLUMN),
        genetic_diagnoses=_get_detailed_yes_no(row, DC.GENETIC_DIAGNOSES_COLUMN, DC.GENETIC_DIAGNOSES_SPECIFY_COLUMN),
        website='Yes' if row[DC.WEBSITE_COLUMN] else 'No',
        info=row[DC.FAMILY_INFO_COLUMN] or 'None specified',
        physician=row[DC.DOCTOR_DETAILS_COLUMN] or 'None',
        doctors=', '.join([DC.DOCTOR_TYPE_MAP[doc.strip()] for doc in row[DC.DOCTOR_TYPES_COLUMN].split(',') if doc]),
        other_doctors=': {}'.format(row[DC.DOCTOR_TYPES_SPECIFY_COLUMN] or 'Unspecified') if DC.OTHER in row[DC.DOCTOR_TYPES_COLUMN] else '',
        testing=_get_testing(row),
        biopses='None' if (DC.NONE in row[DC.BIOPSY_COLUMN] or not row[DC.BIOPSY_COLUMN]) else ', '.join([
           '{} Biopsy'.format('Other Tissue' if biopsy.strip() == DC.OTHER else biopsy.strip().title())
            for biopsy in row[DC.BIOPSY_COLUMN].split(',')]),
        other_biopses=': {}'.format(row[DC.OTHER_BIOPSY_COLUMN] or 'Unspecified') if DC.OTHER in row[DC.BIOPSY_COLUMN] else '',
        studies='Yes, Name of studies: {study_names}, Expecting results: {expecting_results}'.format(
            study_names=row[DC.OTHER_STUDIES_COLUMN] or 'Unspecified',
            expecting_results=(row[DC.EXPECTING_RESULTS_COLUMN] or 'Unspecified').title(),
        ) if row[DC.HAS_OTHER_STUDIES_COLUMN] == DC.YES else 'No',
        mother=_parent_summary(row, DC.MOTHER),
        father=_parent_summary(row, DC.FATHER),
        siblings=_relative_list_summary(row, DC.SIBLINGS),
        children=_relative_list_summary(row, DC.CHILDREN),
        relatives=_relative_list_summary(row, DC.OTHER_RELATIVES, all_affected=True),
    )

def _get_rgp_dsm_proband_fields(row):
    DC = DSMConstants

    try:
        age = int(row[DC.AGE_COLUMN])
        birth_year = date.today().year - age
    except ValueError:
        birth_year = None

    death_year = None
    if row[DC.DECEASED_COLUMN] == DC.YES:
        try:
            age = int(row[DC.DECEASED_AGE_COLUMN])
            death_year = birth_year + age
        except (ValueError, TypeError):
            death_year = 0

    try:
        onset_age_val = int(row[DC.AGE_OF_ONSET_COLUMN])
        onset_age = next(age for cutoff, age in [
            (2, 'I'), # Infantile onset
            (13, 'C'), # Childhood onset
            (20, 'J'), # Juvenile onset
            (200, 'A')# Adult onset
        ] if onset_age_val < cutoff)
    except (ValueError, TypeError):
        onset_age = None

    affected_relatives = any(
        row['{}_{}'.format(parent, DC.AFFECTED_KEY)] == DC.YES for parent in [DC.MOTHER, DC.FATHER]
    ) or bool(_get_rgp_dsm_relative_list(row, DC.OTHER_RELATIVES)) or any(
        any(rel for rel in _get_rgp_dsm_relative_list(row, relative) or []
            if rel['{}_{}'.format(relative, DC.SAME_CONDITION_KEY)] == DC.YES)
        for relative in [DC.SIBLINGS, DC.CHILDREN])

    return {
        JsonConstants.SEX_COLUMN: row[DC.SEX_COLUMN],
        JsonConstants.FAMILY_NOTES_COLUMN: _get_rgp_dsm_family_notes(row),
        JsonConstants.MATERNAL_ETHNICITY: json.dumps(_get_rgp_dsm_parent_ethnicity(row, DC.MOTHER)),
        JsonConstants.PATERNAL_ETHNICITY: json.dumps(_get_rgp_dsm_parent_ethnicity(row, DC.FATHER)),
        JsonConstants.BIRTH_YEAR: json.dumps(birth_year),
        JsonConstants.DEATH_YEAR: json.dumps(death_year),
        JsonConstants.ONSET_AGE: json.dumps(onset_age),
        JsonConstants.AFFECTED_RELATIVES: json.dumps(affected_relatives),
    }


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
    PROBAND_RELATIONSHIP = 'probandRelationship'
    MATERNAL_ETHNICITY = 'maternalEthnicity'
    PATERNAL_ETHNICITY = 'paternalEthnicity'
    BIRTH_YEAR = 'birthYear'
    DEATH_YEAR = 'deathYear'
    ONSET_AGE = 'onsetAge'
    AFFECTED_RELATIVES = 'affectedRelatives'


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


class DSMConstants:
    YES = 'YES'
    NO = 'NO'
    UNSURE = 'UNSURE'
    UNKNOWN = 'UNKNOWN'
    OTHER = 'OTHER'
    NONE = 'NONE'
    PREFER_NOT_ANSWER = 'PREFER_NOT_ANSWER'

    FAMILY_ID_COLUMN = 'familyId'
    SEX_COLUMN = 'PATIENT_SEX'
    AGE_COLUMN = 'PATIENT_AGE'
    AGE_OF_ONSET_COLUMN = 'CONDITION_AGE'
    DECEASED_AGE_COLUMN = 'DECEASED_AGE'
    DECEASED_CAUSE_COLUMN = 'DECEASED_CAUSE'
    DECEASED_COLUMN = 'PATIENT_DECEASED'
    RELATIONSHIP_COLUMN = 'RELATIONSHIP'
    RELATIONSHIP_SPECIFY_COLUMN = 'RELATIONSHIP_OTHER_DETAILS'
    SAMPLE_AVAILABILITY_COLUMN = 'DECEASED_DNA'
    RACE_COLUMN = 'RACE'
    ETHNICITY_COLUMN = 'ETHNICITY'
    CLINICAL_DIAGNOSES_COLUMN = 'CLINICAL_DIAGNOSES'
    CLINICAL_DIAGNOSES_SPECIFY_COLUMN = 'CLINICAL_DIAGNOSES_DETAILS'
    GENETIC_DIAGNOSES_COLUMN = 'GENETIC_DIAGNOSES'
    GENETIC_DIAGNOSES_SPECIFY_COLUMN = 'GENETIC_DIAGNOSES_DETAILS'
    DOCTOR_TYPES_COLUMN = 'DOCTOR_TYPES'
    DOCTOR_TYPES_SPECIFY_COLUMN = 'DOCTOR_TYPES_OTHER_DETAILS'
    DOCTOR_DETAILS_COLUMN = 'FIND_OUT_DOCTOR_DETAILS'
    DESCRIPTION_COLUMN = 'DESCRIPTION'
    FAMILY_INFO_COLUMN = 'FAMILY_INFO'
    WEBSITE_COLUMN = 'WEBSITE'
    TESTS_COLUMN = 'TESTS'
    OTHER_TEST_COLUMN = 'TESTS_OTHER_DETAILS'
    BIOPSY_COLUMN = 'BIOPSY'
    OTHER_BIOPSY_COLUMN = 'BIOPSY_OTHER_DETAILS'
    HAS_OTHER_STUDIES_COLUMN = 'OTHER_STUDIES'
    OTHER_STUDIES_COLUMN = 'OTHER_STUDIES_DESCRIBE'
    EXPECTING_RESULTS_COLUMN = 'EXPECT_RESULTS'

    DOCTOR_TYPE_MAP = {
        'CLIN_GEN': 'Clinical geneticist',
        'NEURO': 'Neurologist',
        'ENDO': 'Endocrinologist',
        'PULMO': 'Pulmonologist',
        'CARDIO': 'Cardiologist',
        'NEPHRO': 'Nephrologist',
        'PSYCH': 'Psychologist',
        'GASTRO': 'Gastroenterologist',
        'DERMA': 'Dermatologist',
        'OPHTHAL': 'Ophthalmologist',
        'OTOL': 'Otologist',
        'OTHER': 'Other',
    }

    MALE_SEX = 'MALE'
    FEMALE_SEX = 'FEMALE'
    RELATIONSHIP_MAP = {
        'MYSELF': {MALE_SEX: 'Myself (male)', FEMALE_SEX: 'Myself (female)', PREFER_NOT_ANSWER: 'Myself (unspecified sex)'},
        'CHILD': {MALE_SEX: 'Son', FEMALE_SEX: 'Daughter', PREFER_NOT_ANSWER: 'Child (unspecified sex)'},
        'SIBLING': {MALE_SEX: 'Brother', FEMALE_SEX: 'Sister', PREFER_NOT_ANSWER: 'Sibling (unspecified sex)'},
        'COUSIN': {MALE_SEX: 'Cousin (male)', FEMALE_SEX: 'Cousin (female)', PREFER_NOT_ANSWER: 'Cousin (unspecified sex)'},
        'NIECE_NEPHEW': {MALE_SEX: 'Nephew', FEMALE_SEX: 'Niece', PREFER_NOT_ANSWER: 'Niece or nephew (unspecified sex)'},
        OTHER: {MALE_SEX: ' (male)', FEMALE_SEX: ' (female)', PREFER_NOT_ANSWER: ' (unspecified sex)'},
        'MINOR_CHILD': {MALE_SEX: 'Minor Son', FEMALE_SEX: 'Minor Daughter', PREFER_NOT_ANSWER: 'Minor Child (unspecified sex)'},
        'ADULT_CHILD': {
            MALE_SEX: 'Adult Son - unable to provide consent',
            FEMALE_SEX: 'Adult Daughter - unable to provide consent',
            PREFER_NOT_ANSWER: 'Adult Child (unspecified sex) - unable to provide consent',
        },
    }

    NOT_SURE_TEST = 'NOT_SURE'
    KARYOTYPE_TEST = 'KARYOTYPE'
    SINGLE_GENE_TEST = 'SINGLE_GENE'
    GENE_PANEL_TEST = 'GENE_PANEL'
    MITOCHON_GENOME_TEST = 'MITOCHON_GENOME'
    MICROARRAY_TEST = 'MICROARRAY'
    WES_TEST = 'WEXOME'
    WGS_TEST = 'WGENOME'

    YEAR_KEY = 'YEAR'
    LAB_KEY = 'LAB'
    RELATIVES_KEY = 'FAMILY'
    RELATIVE_DETAILS_KEY = 'FAMILY_OTHER_DETAILS'
    TEST_DETAIL_COLUMNS = {MICROARRAY_TEST, WES_TEST, WGS_TEST}

    TEST_DISPLAYS = {
        KARYOTYPE_TEST: 'Karyotype',
        SINGLE_GENE_TEST: 'Single gene testing',
        GENE_PANEL_TEST: 'Gene panel testing',
        MITOCHON_GENOME_TEST: 'Mitochondrial genome sequencing',
        MICROARRAY_TEST: 'Microarray',
        WES_TEST: 'Whole exome sequencing',
        WGS_TEST: 'Whole genome sequencing',
    }

    MOTHER = 'MOTHER'
    FATHER = 'FATHER'
    AFFECTED_KEY = 'SAME_CONDITION'
    PARENT_AGE_KEY = 'CONDITION_AGE'
    CAN_PARTICIPATE_KEY = 'CAN_PARTICIPATE'
    DECEASED_KEY = 'DECEASED'
    STORED_DNA_KEY = 'DECEASED_DNA'
    PARENT_DETAIL_FIELDS = [AFFECTED_KEY, PARENT_AGE_KEY, CAN_PARTICIPATE_KEY, DECEASED_KEY, STORED_DNA_KEY]

    SIBLINGS = 'SIBLING'
    CHILDREN = 'CHILD'
    OTHER_RELATIVES = 'RELATIVE'
    SEX_KEY = 'SEX'
    AGE_KEY = 'AGE'
    CAN_PARTICIPATE_KEY = 'CAN_PARTICIPATE'
    SAME_CONDITION_KEY = 'SAME_CONDITION'
    RELATIVE_DETAIL_FIELDS = [SEX_KEY, AGE_KEY, CAN_PARTICIPATE_KEY, SAME_CONDITION_KEY]

    NO_RELATIVES_COLUMNS = {
        SIBLINGS: 'NO_SIBLINGS',
        CHILDREN: 'NO_CHILDREN',
        OTHER_RELATIVES: 'NO_RELATIVE_AFFECTED',
    }

    RELATIVES_LIST_COLUMNS = {
        SIBLINGS: 'SIBLING',
        CHILDREN: 'CHILD',
        OTHER_RELATIVES: 'RELATIVE',
    }

    RELATIVE_SEX_MAP = {
        SIBLINGS: {'MALE': 'Brother', 'FEMALE': 'Sister', 'Other': 'Sibling (unspecified sex)'},
        CHILDREN: {'MALE': 'Son', 'FEMALE': 'Daughter', 'Other': 'Child (unspecified sex)'},
        OTHER_RELATIVES: {'MALE': 'Male', 'FEMALE': 'Female', 'Other': 'unspecified sex'},
    }
