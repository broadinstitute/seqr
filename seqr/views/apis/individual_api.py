"""
APIs used to retrieve, update, and create Individual records
"""

import gzip
import hashlib
import json
import logging
import os
import tempfile
import traceback
import xlrd

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Individual, Family, CAN_EDIT
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.pedigree_image_api import update_pedigree_image
from seqr.views.apis.phenotips_api import create_patient
from seqr.views.utils.json_to_orm_utils import update_individual_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual
from seqr.views.utils.request_utils import _get_project_and_check_permissions
from reference_data.models import HumanPhenotypeOntology

from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_individual_field(request, individual_guid, field_name):
    """Updates the `case_review_discussion` field for the given family.

    Args:
        individual_guid (string): GUID of the individual.
    """

    individual = Individual.objects.get(guid=individual_guid)

    # check permission
    project = individual.family.project
    if not request.user.is_staff and not request.user.has_perm(CAN_EDIT, project):
        raise PermissionDenied("%s does not have EDIT permissions for %s" % (request.user, project))

    request_json = json.loads(request.body)
    if "value" not in request_json:
        raise ValueError("Request is missing 'value' key")

    individual_json = {field_name: request_json['value']}
    update_individual_from_json(individual, individual_json)

    return create_json_response({
        individual.guid: _get_json_for_individual(individual, request.user)
    })


def parse_ped_file(stream):
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


def parse_xls(stream):
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


def process_rows(rows):
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
        if affected == '1' or affected.lower() == 'unaffected':
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


def validate_records(records):
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


def _compute_serialized_file_path(token):
    """Compute local file path, and make sure the directory exists"""

    upload_directory = os.path.join(tempfile.gettempdir(), 'temp_uploads')
    if not os.path.isdir(upload_directory):
        logger.info("Creating directory: " + upload_directory)
        os.makedirs(upload_directory)

    return os.path.join(upload_directory, "temp_upload_%(token)s.json.gz" % locals())


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def receive_individuals_table(request, project_guid):
    """Handler for the initial upload of an Excel or .tsv table of individuals. This handler
    parses the records, but doesn't save them in the database. Instead, it saves them to
    a temporary file and sends a 'token' representing this file back to the client. If/when the
    client then wants to 'apply' this table, it can send the token to the
    save_individuals_table(..) handler to actually save the data in the database.

    Args:
        request (object): Django request object
        project_guid (string): project GUID
    """

    project = _get_project_and_check_permissions(project_guid, request.user)

    if len(request.FILES) != 1:
        return create_json_response({
            'errors': ["Received %s files instead of 1" % len(request.FILES)]
        })

    stream = request.FILES.values()[0]
    filename = stream._name
    #file_size = stream._size
    #content_type = stream.content_type
    #content_type_extra = stream.content_type_extra
    #for chunk in value.chunks():
    #   destination.write(chunk)

    if any(map(filename.endswith, ['.ped', '.tsv', '.xls', '.xlsx'])):
        try:
            if filename.endswith('.ped') or filename.endswith('tsv'):
                rows = parse_ped_file(stream)
            elif filename.endswith('.xls') or filename.endswith('.xlsx'):
                rows = parse_xls(stream)
        except Exception as e:
            traceback.print_exc()
            return create_json_response({
                'errors': ["Error while parsing file. " + str(e)]
            })

    else:
        return create_json_response({
            'errors': ["Unexpected file type: " + str(filename)]
        })

    # process and validate
    try:
        records = process_rows(rows)
    except ValueError as e:
        return create_json_response({'errors': [str(e)]})

    errors, warnings = validate_records(records)

    if errors:
        return create_json_response({'errors': errors, 'warnings': warnings})

    # save json to temporary file
    token = hashlib.md5(str(records)).hexdigest()
    serialized_file_path = _compute_serialized_file_path(token)
    with gzip.open(serialized_file_path, "w") as f:
        json.dump(records, f)

    # send back some stats
    num_families = len(set(r['familyId'] for r in records))
    num_individuals = len(set(r['individualId'] for r in records))
    num_families_to_create = len([family_id for family_id in set(r['familyId'] for r in records)
         if not Family.objects.filter(family_id=family_id, project=project)
    ])
    num_individuals_to_create = len(set(r['individualId'] for r in records
        if not Individual.objects.filter(individual_id=r['individualId'], family__family_id=r['familyId'], family__project=project)
    ))
    info = [
        "%(num_families)s families, %(num_individuals)s inidividuals parsed from %(filename)s" % locals(),
        "%d new families, %d new individuals will be added to the project" % (num_families_to_create, num_individuals_to_create),
        "%d existing individuals will be updated" % (num_individuals - num_individuals_to_create),
    ]

    return create_json_response({
        'token': token,
        'errors': errors,
        'warnings': warnings,
        'info': info,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def save_individuals_table(request, project_guid, token):
    """Handler for 'save' requests to apply Individual tables previously uploaded through receive_individuals_table(..)

    Args:
        request (object): Django request object
        project_guid (string): project GUID
        token (string): a token sent to the client by receive_individuals_table(..)
    """
    project = _get_project_and_check_permissions(project_guid, request.user)

    serialized_file_path = _compute_serialized_file_path(token)
    with gzip.open(serialized_file_path) as f:
        records = json.load(f)

    families = {}
    for record in records:
        family, created = Family.objects.get_or_create(project=project, family_id=record['familyId'])
        if created:
            if not family.display_name:
                family.display_name = family.family_id
                family.save()

            logger.info("Created family: %s" % str(family))

        individual, created = Individual.objects.get_or_create(family=family, individual_id=record['individualId'])
        update_individual_from_json(individual, record, allow_unknown_keys=True)

        individual.phenotips_eid = individual.guid  # use this instead of individual_id to avoid chance of collisions
        if created:
            patient_record = create_patient(project, individual.phenotips_eid)
            individual.phenotips_patient_id = patient_record['id']
            logger.info("Created phenotips record with patient id %s and external id %s" % (
                str(individual.phenotips_patient_id), str(individual.phenotips_eid)))

        if not individual.case_review_status:
            individual.case_review_status = Individual.CASE_REVIEW_STATUS_IN_REVIEW
        if not individual.display_name:
            individual.display_name = individual.individual_id
        individual.save()

        _deprecated_update_original_individual_data(project, individual)

        families[family.family_id] = family

    # update pedigree images
    for family in families.values():
        update_pedigree_image(family)

    # sync events

    os.remove(serialized_file_path)

    return create_json_response({})


def _deprecated_update_original_individual_data(project, individual):
    base_project = BaseProject.objects.filter(project_id=project.deprecated_project_id)
    base_project = base_project[0]

    base_family, created = BaseFamily.objects.get_or_create(project=base_project, family_id=individual.family.family_id)
    if created:
        logger.info("Created xbrowse family: %s" % str(base_family))

    base_individual, created = BaseIndividual.objects.get_or_create(project=base_project, family=base_family, indiv_id=individual.individual_id)
    if created:
        logger.info("Created xbrowse individual: %s" % str(base_individual))

    base_individual.created_date = individual.created_date
    base_individual.maternal_id = individual.maternal_id
    base_individual.paternal_id = individual.paternal_id
    base_individual.gender = individual.sex
    base_individual.affected = individual.affected
    base_individual.nickname = individual.display_name
    if created or not base_individual.phenotips_id:
        base_individual.phenotips_id = individual.phenotips_eid
    base_individual.phenotips_data = individual.phenotips_data
    base_individual.save()

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
        
