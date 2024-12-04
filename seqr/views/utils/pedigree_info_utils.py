"""Utilities for parsing .fam files or other tables that describe individual pedigree structure."""
import difflib
import os
import json
import re
import tempfile
import openpyxl as xl
from collections import defaultdict
from datetime import date

from reference_data.models import HumanPhenotypeOntology
from seqr.utils.communication_utils import send_html_email
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.views.utils.json_utils import _to_snake_case, _to_title_case
from seqr.views.utils.permissions_utils import user_is_pm, get_pm_user_emails
from seqr.models import Individual

logger = SeqrLogger(__name__)


NO_VALIDATE_MANIFEST_PROJECT_CATEGORIES = ['CMG', 'TGG_Non-Report']
RELATIONSHIP_REVERSE_LOOKUP = {v.lower(): k for k, v in Individual.RELATIONSHIP_LOOKUP.items()}


def parse_pedigree_table(parsed_file, filename, user, project):
    """Validates and parses pedigree information from a .fam, .tsv, or Excel file.

    Args:
        parsed_file (array): The parsed output from the raw file.
        filename (string): The original filename - used to determine the file format based on the suffix.
        user (User): Django User object
        project (Project): Django Project object

    Return:
        A 3-tuple that contains:
        (
            json_records (list): list of dictionaries, with each dictionary containing info about
                one of the individuals in the input data
            errors (list): list of error message strings
            warnings (list): list of warning message strings
        )
    """
    header_string = str(parsed_file[0])
    is_merged_pedigree_sample_manifest = "do not modify" in header_string.lower() and "Broad" in header_string
    if is_merged_pedigree_sample_manifest:
        if not user_is_pm(user):
            raise ValueError('Unsupported file format')
        if not project:
            raise ValueError('Project argument required for parsing sample manifest')
        header, rows = _parse_merged_pedigree_sample_manifest_rows(parsed_file[1:])
    else:
        header = None
        rows = None

    rows, header = _parse_pedigree_table_rows(parsed_file, filename, header=header, rows=rows)

    # convert to json and validate
    errors = None
    column_map = None
    try:
        if is_merged_pedigree_sample_manifest:
            logger.info("Parsing merged pedigree-sample-manifest file", user)
            sample_manifest_rows, kit_id, errors = _parse_merged_pedigree_sample_manifest_format(rows, project)
            column_map = MergedPedigreeSampleManifestConstants.MERGED_PEDIGREE_COLUMN_MAP
        elif 'participant_guid' in header:
            logger.info("Parsing RGP DSM export file", user)
            rows = _parse_rgp_dsm_export_format(rows)
            header = None
    except Exception as e:
        raise ErrorsWarningsException(['Error while converting {} rows to json: {}'.format(filename, e)], [])

    json_records, warnings = _parse_pedigree_table_json(project, rows, header=header, column_map=column_map, errors=errors)

    if is_merged_pedigree_sample_manifest:
        _set_proband_relationship(json_records)
        _send_sample_manifest(sample_manifest_rows, kit_id, filename, parsed_file, user, project)

    return json_records, warnings


def parse_basic_pedigree_table(project, parsed_file, filename, required_columns=None, update_features=False):
    rows, header = _parse_pedigree_table_rows(parsed_file, filename)
    return _parse_pedigree_table_json(
        project, rows, header=header, fail_on_warnings=True, allow_id_update=False,
        required_columns=required_columns, update_features=update_features,
    )


def _parse_pedigree_table_rows(parsed_file, filename, header=None, rows=None):
    # parse rows from file
    try:
        rows = rows or [row for row in parsed_file[1:] if row and not (row[0] or '').startswith('#')]
        if not header:
            header_string = str(parsed_file[0])
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

        formatted_rows = [{header_item: str(field).strip() for header_item, field in zip(header, row)} for row in rows]
        return formatted_rows, header

    except Exception as e:
        raise ErrorsWarningsException(['Error while parsing file: {}. {}'.format(filename, e)], [])


def _parse_pedigree_table_json(project, rows, header=None, column_map=None, errors=None, fail_on_warnings=False, required_columns=None, allow_id_update=True, update_features=False):
    # convert to json and validate
    column_map = column_map or (_parse_header_columns(header, allow_id_update, update_features) if header else None)
    if column_map:
        json_records = _convert_fam_file_rows_to_json(column_map, rows, required_columns=required_columns, update_features=update_features)
    else:
        json_records = rows

    warnings = validate_fam_file_records(project, json_records, fail_on_warnings=fail_on_warnings, errors=errors, update_features=update_features)
    return json_records, warnings


def _parse_sex(sex):
    if sex == '1' or sex.upper().startswith('M'):
        return 'M'
    elif sex == '2' or sex.upper().startswith('F'):
        return 'F'
    elif sex == '0' or not sex or sex.lower() in {'unknown', 'prefer_not_answer'}:
        return 'U'
    return Individual.SEX_LOOKUP.get(sex)


def _parse_affected(affected):
    if affected == '1' or affected.upper() == "U" or affected.lower() == 'unaffected':
        return 'N'
    elif affected == '2' or affected.upper().startswith('A'):
        return 'A'
    elif affected == '0' or not affected or affected.lower() == 'unknown':
        return 'U'
    return None


def parse_hpo_terms(hpo_term_string):
    if not hpo_term_string:
        return []
    terms = {hpo_term.strip() for hpo_term in re.sub(r'\(.*?\)', '', hpo_term_string).replace(',', ';').split(';')}
    return[{'id': term} for term in sorted(terms) if term]


def _convert_fam_file_rows_to_json(column_map, rows, required_columns=None, update_features=False):
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
    required_columns = [JsonConstants.FAMILY_ID_COLUMN, JsonConstants.INDIVIDUAL_ID_COLUMN] + (required_columns or [])
    missing_cols = [_to_title_case(_to_snake_case(col)) for col in set(required_columns) - set(column_map.values())]
    if update_features and JsonConstants.FEATURES not in column_map.values():
        missing_cols.append('HPO Terms')
    if missing_cols:
        raise ErrorsWarningsException([f"Missing required columns: {', '.join(sorted(missing_cols))}"])

    json_results = []
    errors = []
    for i, row_dict in enumerate(rows):
        json_record = {}
        for key, column in column_map.items():
            value = (row_dict.get(key) or '').strip()
            if column in required_columns and not value:
                errors.append(f'Missing {_to_title_case(_to_snake_case(column))} in row #{i + 1}')
                continue

            try:
                value = _format_value(value, column)
            except (KeyError, ValueError):
                errors.append(f'Invalid value "{value}" for {_to_title_case(_to_snake_case(column))} in row #{i + 1}')
                continue

            json_record[column] = value

        json_results.append(json_record)

    if errors:
        raise ErrorsWarningsException(errors)
    return json_results


def _parse_header_columns(header, allow_id_update, update_features):
    column_map = {}
    for key in header:
        column = None
        full_key = key
        key = key.lower()
        if full_key in JsonConstants.JSON_COLUMNS:
            column = full_key
        elif key == JsonConstants.FAMILY_NOTES_COLUMN.lower():
            column = JsonConstants.FAMILY_NOTES_COLUMN
        elif key.startswith("notes"):
            column = JsonConstants.NOTES_COLUMN
        elif 'indiv' in key and 'previous' in key:
            if allow_id_update:
                column = JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN
        elif update_features and 'hpo' in key and 'term' in key:
            column = JsonConstants.FEATURES
        else:
            column = next((
                col for col, substrings in JsonConstants.COLUMN_SUBSTRINGS
                if all(substring in key for substring in substrings)
            ), None)

        if column:
            column_map[full_key] = column
    return column_map


def _format_value(value, column):
    format_func = JsonConstants.FORMAT_COLUMNS.get(column)
    if format_func:
        if (value or column in {JsonConstants.SEX_COLUMN, JsonConstants.AFFECTED_COLUMN, JsonConstants.FEATURES}):
            value = format_func(value)
            if value is None and column not in JsonConstants.NULLABLE_COLUMNS:
                raise ValueError()
    elif value == '':
        value = None
    return value


def validate_fam_file_records(project, records, fail_on_warnings=False, errors=None, clear_invalid_values=False, update_features=False):
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

    loaded_individual_families = dict(Individual.objects.filter(
        family__project=project, sample__is_active=True).values_list('individual_id', 'family__family_id'))

    hpo_terms = get_valid_hpo_terms(records) if update_features else None

    errors = errors or []
    warnings = []
    individual_id_counts = defaultdict(int)
    affected_status_by_family = defaultdict(list)
    for r in records:
        individual_id = r[JsonConstants.INDIVIDUAL_ID_COLUMN]
        individual_id_counts[individual_id] += 1
        family_id = r.get(JsonConstants.FAMILY_ID_COLUMN) or r['family']['familyId']

        if loaded_individual_families.get(r.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN)):
            errors.append(f'{r[JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN]} already has loaded data and cannot update the ID')
        if loaded_individual_families.get(individual_id) and loaded_individual_families[individual_id] != family_id:
            errors.append(f'{individual_id} already has loaded data and cannot be moved to a different family')

        # check proband relationship has valid gender
        if r.get(JsonConstants.PROBAND_RELATIONSHIP) and r.get(JsonConstants.SEX_COLUMN):
            invalid_choices = {}
            if r[JsonConstants.SEX_COLUMN] in Individual.MALE_SEXES:
                invalid_choices = Individual.FEMALE_RELATIONSHIP_CHOICES
            elif r[JsonConstants.SEX_COLUMN] in Individual.FEMALE_SEXES:
                invalid_choices = Individual.MALE_RELATIONSHIP_CHOICES
            if invalid_choices and r[JsonConstants.PROBAND_RELATIONSHIP] in invalid_choices:
                message = 'Invalid proband relationship "{relationship}" for {individual_id} with given gender {sex}'.format(
                    relationship=Individual.RELATIONSHIP_LOOKUP[r[JsonConstants.PROBAND_RELATIONSHIP]],
                    individual_id=individual_id,
                    sex=Individual.SEX_LOOKUP[r[JsonConstants.SEX_COLUMN]]
                )
                if clear_invalid_values:
                    r[JsonConstants.PROBAND_RELATIONSHIP] = None
                    warnings.append(f'Skipped {message}')
                else:
                    errors.append(message)

        # check maternal and paternal ids for consistency
        for parent in [
            ('father', JsonConstants.PATERNAL_ID_COLUMN, Individual.MALE_SEXES),
            ('mother', JsonConstants.MATERNAL_ID_COLUMN, Individual.FEMALE_SEXES)
        ]:
            _validate_parent(r, *parent, individual_id, family_id, records_by_id, warnings, errors, clear_invalid_values)

        if update_features:
            features = r[JsonConstants.FEATURES] or []
            if not features and r[JsonConstants.AFFECTED_COLUMN] == Individual.AFFECTED_STATUS_AFFECTED:
                errors.append(f'{individual_id} is affected but has no HPO terms')
            invalid_features = {feature['id'] for feature in features if feature['id'] not in hpo_terms}
            if invalid_features:
                errors.append(f'{individual_id} has invalid HPO terms: {", ".join(sorted(invalid_features))}')

        affected_status_by_family[family_id].append(r.get(JsonConstants.AFFECTED_COLUMN))

    errors += [
        f'{individual_id} is included as {count} separate records, but must be unique within the project'
        for individual_id, count in individual_id_counts.items() if count > 1
    ]

    no_affected_families = get_no_affected_families(affected_status_by_family)
    if no_affected_families:
        warnings.append('The following families do not have any affected individuals: {}'.format(', '.join(no_affected_families)))

    if fail_on_warnings:
        errors += warnings
        warnings = []
    if errors:
        raise ErrorsWarningsException(errors, warnings)
    return warnings


def get_no_affected_families(affected_status_by_family: dict[str, list[str]]) -> list[str]:
    return [
        family_id for family_id, affected_statuses in affected_status_by_family.items()
        if all(affected is not None and affected != Individual.AFFECTED_STATUS_AFFECTED for affected in affected_statuses)
    ]


def get_valid_hpo_terms(records, additional_feature_columns=None):
    all_hpo_terms = set()
    for record in records:
        all_hpo_terms.update({feature['id'] for feature in record.get(JsonConstants.FEATURES, [])})
        for col in (additional_feature_columns or []):
            all_hpo_terms.update({feature['id'] for feature in record.get(col, [])})
    return set(HumanPhenotypeOntology.objects.filter(hpo_id__in=all_hpo_terms).values_list('hpo_id', flat=True))


def _validate_parent(row, parent_id_type, parent_id_field, expected_sexes, individual_id, family_id, records_by_id, warnings, errors, clear_invalid_values):
    parent_id = row.get(parent_id_field)
    if not parent_id:
        return

    # is there a separate record for the parent id?
    if parent_id not in records_by_id:
        warning = f'{parent_id} is the {parent_id_type} of {individual_id} but is not included'
        if clear_invalid_values:
            row[parent_id_field] = None
        else:
            warning += f'. Make sure to create an additional record with {parent_id} as the Individual ID'
        warnings.append(warning)
        return

    # is the parent the same individuals
    if parent_id == individual_id:
        errors.append('{} is recorded as their own {}'.format(parent_id, parent_id_type))

    # is father male and mother female?
    if JsonConstants.SEX_COLUMN in records_by_id[parent_id]:
        actual_sex = records_by_id[parent_id][JsonConstants.SEX_COLUMN]
        if actual_sex not in expected_sexes:
            actual_sex_label = Individual.SEX_LOOKUP[actual_sex]
            errors.append(
                "%(parent_id)s is recorded as %(actual_sex_label)s sex and also as the %(parent_id_type)s of %(individual_id)s" % locals())

    # is the parent in the same family?
    parent = records_by_id[parent_id]
    parent_family_id = parent.get(JsonConstants.FAMILY_ID_COLUMN) or parent['family']['familyId']
    if parent_family_id != family_id:
        errors.append(
            "%(parent_id)s is recorded as the %(parent_id_type)s of %(individual_id)s but they have different family ids: %(parent_family_id)s and %(family_id)s" % locals())


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


def _parse_merged_pedigree_sample_manifest_rows(rows):
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

    return expected_header_columns, rows


def _parse_merged_pedigree_sample_manifest_format(rows, project):
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

    is_no_validate_project = project.projectcategory_set.filter(name__in=NO_VALIDATE_MANIFEST_PROJECT_CATEGORIES).exists()
    sample_manifest_rows = []
    errors = []
    consent_codes = set()
    for row in rows:
        sample_manifest_rows.append({
            column_name: row[column_name] for column_name in c.SAMPLE_MANIFEST_COLUMN_NAMES
        })

        if not is_no_validate_project:
            missing_cols = {col for col in c.REQUIRED_COLUMNS if not row[col]}
            if missing_cols:
                individual_id = row[c.COLLABORATOR_SAMPLE_ID_COLUMN]
                errors.append(f'{individual_id} is missing the following required columns: {", ".join(sorted(missing_cols))}')

        consent_code = row[c.CONSENT_CODE_COLUMN]
        if consent_code:
            consent_codes.add(consent_code)

    if len(consent_codes) > 1:
        errors.append(f'Multiple consent codes specified in manifest: {", ".join(sorted(consent_codes))}')
    elif len(consent_codes) == 1:
        consent_code = consent_codes.pop()
        project_consent_code = project.get_consent_code_display()
        if consent_code != project_consent_code:
            errors.append(
                f'Consent code in manifest "{consent_code}" does not match project consent code "{project_consent_code}"')

    return sample_manifest_rows, kit_id, errors


def _set_proband_relationship(json_records):
    records_by_family = defaultdict(list)
    for r in json_records:
        records_by_family[r[JsonConstants.FAMILY_ID_COLUMN]].append(r)

    family_relationships = {}
    for family_id, records in records_by_family.items():
        affected = [r for r in records if r[JsonConstants.AFFECTED_COLUMN] == 'A']
        if len(affected) > 1:
            affected_children = sorted(
                [r for r in affected if r[JsonConstants.PATERNAL_ID_COLUMN] or r[JsonConstants.MATERNAL_ID_COLUMN]],
                key=lambda r: bool(r[JsonConstants.PATERNAL_ID_COLUMN]) and bool(r[JsonConstants.MATERNAL_ID_COLUMN]),
                reverse=True
            )
            if affected_children:
                affected = affected_children
        if not affected:
            continue
        affected = affected[0]

        relationships = {
            affected[JsonConstants.MATERNAL_ID_COLUMN]: Individual.MOTHER_RELATIONSHIP,
            affected[JsonConstants.PATERNAL_ID_COLUMN]: Individual.FATHER_RELATIONSHIP,
        }

        maternal_siblings = {
            r[JsonConstants.INDIVIDUAL_ID_COLUMN] for r in records
            if affected[JsonConstants.MATERNAL_ID_COLUMN] and affected[JsonConstants.MATERNAL_ID_COLUMN] == r[JsonConstants.MATERNAL_ID_COLUMN]
        }
        paternal_siblings = {
            r[JsonConstants.INDIVIDUAL_ID_COLUMN] for r in records
            if affected[JsonConstants.PATERNAL_ID_COLUMN] and affected[JsonConstants.PATERNAL_ID_COLUMN] == r[JsonConstants.PATERNAL_ID_COLUMN]
        }
        relationships.update({r_id: Individual.MATERNAL_SIBLING_RELATIONSHIP for r_id in maternal_siblings})
        relationships.update({r_id: Individual.PATERNAL_SIBLING_RELATIONSHIP for r_id in paternal_siblings})
        relationships.update({r_id: Individual.SIBLING_RELATIONSHIP for r_id in paternal_siblings.intersection(maternal_siblings)})

        relationships.update({
            r[JsonConstants.INDIVIDUAL_ID_COLUMN]: Individual.CHILD_RELATIONSHIP for r in records
            if affected[JsonConstants.INDIVIDUAL_ID_COLUMN] in {r[JsonConstants.MATERNAL_ID_COLUMN], r[JsonConstants.PATERNAL_ID_COLUMN]}
        })

        relationships[affected[JsonConstants.INDIVIDUAL_ID_COLUMN]] = Individual.SELF_RELATIONSHIP
        family_relationships[family_id] = relationships

    for r in json_records:
        r[JsonConstants.PROBAND_RELATIONSHIP] = family_relationships.get(
            r[JsonConstants.FAMILY_ID_COLUMN], {}).get(r[JsonConstants.INDIVIDUAL_ID_COLUMN])


def _send_sample_manifest(sample_manifest_rows, kit_id, original_filename, original_file_rows, user, project):

    recipients = get_pm_user_emails(user)

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

    email_body = "User {} just uploaded pedigree info to {}.\n".format(user.email or user.username, project.name)

    email_body += """This email has 2 attached files:
    
    <b>%(sample_manifest_filename)s</b> is the sample manifest file in a format that can be sent to GP.
    
    <b>%(original_filename)s</b> is the original merged pedigree-sample-manifest file that the user uploaded.
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
            JsonConstants.AFFECTED_COLUMN: Individual.AFFECTED_STATUS_AFFECTED,
        }
        proband_row.update(_get_rgp_dsm_proband_fields(row))

        mother_row = {
            JsonConstants.FAMILY_ID_COLUMN: family_id,
            JsonConstants.INDIVIDUAL_ID_COLUMN: maternal_id,
            JsonConstants.SEX_COLUMN: Individual.SEX_FEMALE,
            JsonConstants.AFFECTED_COLUMN: Individual.AFFECTED_STATUS_UNAFFECTED,
        }
        father_row = {
            JsonConstants.FAMILY_ID_COLUMN: family_id,
            JsonConstants.INDIVIDUAL_ID_COLUMN: paternal_id,
            JsonConstants.SEX_COLUMN: Individual.SEX_MALE,
            JsonConstants.AFFECTED_COLUMN: Individual.AFFECTED_STATUS_UNAFFECTED,
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
* __Relatives:__ {relatives}""".format(
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
        JsonConstants.SEX_COLUMN: _parse_sex(row[DC.SEX_COLUMN]),
        JsonConstants.FAMILY_NOTES_COLUMN: _get_rgp_dsm_family_notes(row),
        JsonConstants.MATERNAL_ETHNICITY: _get_rgp_dsm_parent_ethnicity(row, DC.MOTHER),
        JsonConstants.PATERNAL_ETHNICITY: _get_rgp_dsm_parent_ethnicity(row, DC.FATHER),
        JsonConstants.BIRTH_YEAR: birth_year,
        JsonConstants.DEATH_YEAR: death_year,
        JsonConstants.ONSET_AGE: onset_age,
        JsonConstants.AFFECTED_RELATIVES: affected_relatives,
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
    MONDO_ID_COLUMN = 'mondoId'
    PROBAND_RELATIONSHIP = 'probandRelationship'
    MATERNAL_ETHNICITY = 'maternalEthnicity'
    PATERNAL_ETHNICITY = 'paternalEthnicity'
    BIRTH_YEAR = 'birthYear'
    DEATH_YEAR = 'deathYear'
    ONSET_AGE = 'onsetAge'
    AFFECTED_RELATIVES = 'affectedRelatives'
    PRIMARY_BIOSAMPLE = 'primaryBiosample'
    ANALYTE_TYPE = 'analyteType'
    TISSUE_AFFECTED_STATUS = 'tissueAffectedStatus'
    FEATURES = 'features'

    JSON_COLUMNS = {MATERNAL_ETHNICITY, PATERNAL_ETHNICITY, BIRTH_YEAR, DEATH_YEAR, ONSET_AGE, AFFECTED_RELATIVES}
    NULLABLE_COLUMNS = {TISSUE_AFFECTED_STATUS}
    NULLABLE_COLUMNS.update(JSON_COLUMNS)

    FORMAT_COLUMNS = {
        SEX_COLUMN: _parse_sex,
        AFFECTED_COLUMN: _parse_affected,
        PATERNAL_ID_COLUMN: lambda value: value if value != '.' else '',
        MATERNAL_ID_COLUMN: lambda value: value if value != '.' else '',
        PROBAND_RELATIONSHIP: lambda value: RELATIONSHIP_REVERSE_LOOKUP.get(value.lower()),
        PRIMARY_BIOSAMPLE: lambda value: next(
            (code for code, uberon_code in Individual.BIOSAMPLE_CHOICES if value.startswith(uberon_code)), None),
        ANALYTE_TYPE: Individual.ANALYTE_REVERSE_LOOKUP.get,
        TISSUE_AFFECTED_STATUS: lambda value: {'Yes': True, 'No': False, 'Unknown': None}[value],
        FEATURES: parse_hpo_terms,
    }
    FORMAT_COLUMNS.update({col: json.loads for col in JSON_COLUMNS})

    COLUMN_SUBSTRINGS = [
        (FAMILY_ID_COLUMN, ['family']),
        (INDIVIDUAL_ID_COLUMN, ['indiv']),
        (PATERNAL_ID_COLUMN, ['father']),
        (PATERNAL_ID_COLUMN, ['paternal']),
        (MATERNAL_ID_COLUMN, ['mother']),
        (MATERNAL_ID_COLUMN, ['maternal']),
        (SEX_COLUMN, ['sex']),
        (SEX_COLUMN, ['gender']),
        (TISSUE_AFFECTED_STATUS, ['tissue', 'affected', 'status']),
        (PRIMARY_BIOSAMPLE, ['primary', 'biosample']),
        (ANALYTE_TYPE, ['analyte', 'type']),
        (AFFECTED_COLUMN, ['affected']),
        (CODED_PHENOTYPE_COLUMN, ['coded', 'phenotype']),
        (MONDO_ID_COLUMN, ['mondo', 'id']),
        (PROBAND_RELATIONSHIP, ['proband', 'relation']),
    ]


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
    BIOSAMPLE_COLUMN = 'Primary Biosample'
    ANALYTE_TYPE_COLUMN = 'Analyte Type'
    TISSUE_AFFECTED_COLUMN = 'Tissue Affected Status'
    RECONTACTABLE_COLUMN = 'Recontactable'
    VOLUME_COLUMN = "Volume"
    CONCENTRATION_COLUMN = "Concentration"
    NOTES_COLUMN = "Notes"
    CODED_PHENOTYPE_COLUMN = 'MONDO Label'
    MONDO_ID_COLUMN = 'MONDO ID'
    CONSENT_CODE_COLUMN = 'Consent Code'
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
        BIOSAMPLE_COLUMN,
        ANALYTE_TYPE_COLUMN,
        TISSUE_AFFECTED_COLUMN,
        RECONTACTABLE_COLUMN,
        VOLUME_COLUMN,
        CONCENTRATION_COLUMN,
        NOTES_COLUMN,
        CODED_PHENOTYPE_COLUMN,
        MONDO_ID_COLUMN,
        CONSENT_CODE_COLUMN,
        DATA_USE_RESTRICTIONS_COLUMN,
    ]

    MERGED_PEDIGREE_COLUMN_MAP = {
        FAMILY_ID_COLUMN: JsonConstants.FAMILY_ID_COLUMN,
        COLLABORATOR_SAMPLE_ID_COLUMN: JsonConstants.INDIVIDUAL_ID_COLUMN,
        PATERNAL_ID_COLUMN: JsonConstants.PATERNAL_ID_COLUMN,
        MATERNAL_ID_COLUMN: JsonConstants.MATERNAL_ID_COLUMN,
        SEX_COLUMN: JsonConstants.SEX_COLUMN,
        AFFECTED_COLUMN: JsonConstants.AFFECTED_COLUMN,
        NOTES_COLUMN: JsonConstants.NOTES_COLUMN,
        CODED_PHENOTYPE_COLUMN: JsonConstants.CODED_PHENOTYPE_COLUMN,
        MONDO_ID_COLUMN: JsonConstants.MONDO_ID_COLUMN,
        BIOSAMPLE_COLUMN: JsonConstants.PRIMARY_BIOSAMPLE,
        ANALYTE_TYPE_COLUMN: JsonConstants.ANALYTE_TYPE,
        TISSUE_AFFECTED_COLUMN: JsonConstants.TISSUE_AFFECTED_STATUS,
    }

    REQUIRED_COLUMNS = [
        COLLABORATOR_SAMPLE_ID_COLUMN,
        SEX_COLUMN,
        AFFECTED_COLUMN,
        BIOSAMPLE_COLUMN,
        ANALYTE_TYPE_COLUMN,
        TISSUE_AFFECTED_COLUMN,
        CODED_PHENOTYPE_COLUMN,
        MONDO_ID_COLUMN,
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
