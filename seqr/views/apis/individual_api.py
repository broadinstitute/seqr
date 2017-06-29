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
from seqr.views.utils.pedigree_info_utils import parse_rows_from_fam_file, \
    parse_rows_from_xls, validate_fam_file_records, convert_fam_file_rows_to_json
from seqr.views.utils.request_utils import _get_project_and_check_permissions

from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_individual_field_handler(request, individual_guid, field_name):
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


def _compute_serialized_file_path(token):
    """Compute local file path, and make sure the directory exists"""

    upload_directory = os.path.join(tempfile.gettempdir(), 'temp_uploads')
    if not os.path.isdir(upload_directory):
        logger.info("Creating directory: " + upload_directory)
        os.makedirs(upload_directory)

    return os.path.join(upload_directory, "temp_upload_%(token)s.json.gz" % locals())


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def receive_individuals_table_handler(request, project_guid):
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
                rows = parse_rows_from_fam_file(stream)
            elif filename.endswith('.xls') or filename.endswith('.xlsx'):
                rows = parse_rows_from_xls(stream)
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
        json_records = convert_fam_file_rows_to_json(rows)
    except ValueError as e:
        return create_json_response({'errors': [str(e)]})

    errors, warnings = validate_fam_file_records(json_records)

    if errors:
        return create_json_response({'errors': errors, 'warnings': warnings})

    # save json to temporary file
    token = hashlib.md5(str(json_records)).hexdigest()
    serialized_file_path = _compute_serialized_file_path(token)
    with gzip.open(serialized_file_path, "w") as f:
        json.dump(json_records, f)

    # send back some stats
    num_families = len(set(r['familyId'] for r in json_records))
    num_individuals = len(set(r['individualId'] for r in json_records))
    num_families_to_create = len([family_id for family_id in set(r['familyId'] for r in json_records)
         if not Family.objects.filter(family_id=family_id, project=project)
    ])
    num_individuals_to_create = len(set(r['individualId'] for r in json_records
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
def save_individuals_table_handler(request, project_guid, token):
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

    add_or_update_individuals_and_families(project, individual_records=records)

    os.remove(serialized_file_path)

    return create_json_response({})


def add_or_update_individuals_and_families(project, individual_records):
    """Add or update individual and family records in the given project.

    Args:
        project (object): Django ORM model for the project to add families to
        individual_records (list): A list of JSON records representing individuals. See
            pedigree_info_utils#convert_fam_file_rows_to_json(..)
    """
    families = {}
    for record in individual_records:
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
    base_individual.maternal_id = individual.maternal_id or ''
    base_individual.paternal_id = individual.paternal_id or ''
    base_individual.gender = individual.sex
    base_individual.affected = individual.affected
    base_individual.nickname = individual.display_name
    if not base_individual.case_review_status:
        base_individual.case_review_status = individual.case_review_status 
    if created or not base_individual.phenotips_id:
        base_individual.phenotips_id = individual.phenotips_eid
    base_individual.phenotips_data = individual.phenotips_data
    base_individual.save()

