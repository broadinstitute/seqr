"""
APIs for retrieving, updating, creating, and deleting Individual records
"""

import json
import logging
from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.model_utils import get_or_create_seqr_model
from seqr.models import Individual, Family, CAN_EDIT
from seqr.views.utils.pedigree_image_utils import update_pedigree_images
from seqr.views.utils.file_utils import save_uploaded_file, load_uploaded_file
from seqr.views.utils.json_to_orm_utils import update_individual_from_json, update_family_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual, _get_json_for_individuals, _get_json_for_family, _get_json_for_families
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table, validate_fam_file_records, JsonConstants
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions
from seqr.views.utils.individual_utils import delete_individuals
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)

_SEX_TO_EXPORTED_VALUE = dict(Individual.SEX_LOOKUP)
_SEX_TO_EXPORTED_VALUE['U'] = ''

__AFFECTED_TO_EXPORTED_VALUE = dict(Individual.AFFECTED_STATUS_LOOKUP)
__AFFECTED_TO_EXPORTED_VALUE['U'] = ''


class ErrorsWarningsException(Exception):
    def __init__(self, errors, warnings=None):
        Exception.__init__(self, str(errors))
        self.errors = errors
        self.warnings = warnings


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_individual_handler(request, individual_guid):
    """Updates a single field in an Individual record.

    Args:
        request (object): Django HTTP Request object.
        individual_guid (string): GUID of the Individual.

    Request:
        body should be a json dictionary like: { 'value': xxx }

    Response:
        json dictionary representing the updated individual like:
            {
                <individualGuid> : {
                    individualId: xxx,
                    sex: xxx,
                    affected: xxx,
                    ...
                }
            }
    """

    individual = Individual.objects.get(guid=individual_guid)

    project = individual.family.project

    check_permissions(project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)

    update_individual_from_json(individual, request_json, user=request.user, allow_unknown_keys=True)

    return create_json_response({
        individual.guid: _get_json_for_individual(individual, request.user)
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def edit_individuals_handler(request, project_guid):
    """Modify one or more Individual records.

    Args:
        request (object): Django HTTP Request object.
        project_guid (string): GUID of project that contains these individuals.

    Request:
        body should be a json dictionary that contains a 'individuals' list that includes the individuals to update,
         represented by dictionaries of their guid and fields to update -
        for example:
            {
                'individuals': [
                    { 'individualGuid': <individualGuid1>, 'paternalId': <paternalId>, 'affected': 'A' },
                    { 'individualGuid': <individualGuid1>, 'sex': 'U' },
                    ...
                [
            }

    Response:
        json dictionary representing the updated individual(s) like:
            {
                <individualGuid1> : { individualId: xxx, sex: xxx, affected: xxx, ...},
                <individualGuid2> : { individualId: xxx, sex: xxx, affected: xxx, ...},
                ...
            }
    """

    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)

    request_json = json.loads(request.body)

    modified_individuals_list = request_json.get('individuals')
    if modified_individuals_list is None:
        return create_json_response(
            {}, status=400, reason="'individuals' not specified")

    update_individuals = {ind['individualGuid']: ind for ind in modified_individuals_list}
    update_individual_models = {ind.guid: ind for ind in Individual.objects.filter(guid__in=update_individuals.keys())}
    for modified_ind in modified_individuals_list:
        model = update_individual_models[modified_ind['individualGuid']]
        if modified_ind[JsonConstants.INDIVIDUAL_ID_COLUMN] != model.individual_id:
            modified_ind[JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN] = model.individual_id

    modified_family_ids = {ind.get('familyId') or ind['family']['familyId'] for ind in modified_individuals_list}
    modified_family_ids.update({ind.family.family_id for ind in update_individual_models.values()})
    related_individuals = Individual.objects.filter(
        family__family_id__in=modified_family_ids, family__project=project).exclude(guid__in=update_individuals.keys())
    related_individuals_json = _get_json_for_individuals(related_individuals, project_guid=project_guid, family_fields=['family_id'])
    individuals_list = modified_individuals_list + related_individuals_json

    errors, warnings = validate_fam_file_records(individuals_list, fail_on_warnings=True)
    if errors:
        return create_json_response({'errors': errors, 'warnings': warnings}, status=400, reason='Invalid updates')

    try:
        updated_families, updated_individuals = _add_or_update_individuals_and_families(
            project, modified_individuals_list, user=request.user
        )
    except Exception as e:
        return create_json_response({'errors': [e.message]}, status=400, reason='Invalid updates')

    individuals_by_guid = {
        individual.guid: _get_json_for_individual(individual, request.user) for individual in updated_individuals
    }
    families_by_guid = {
        family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True)
        for family in updated_families
    }

    return create_json_response({
        'individualsByGuid': individuals_by_guid,
        'familiesByGuid': families_by_guid,
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_individuals_handler(request, project_guid):
    """Delete one or more Individual records.

    Args:
        request (object): Django HTTP Request object.
        project_guid (string): GUID of project that contains these individuals.

    Request:
        body should be a json dictionary that contains a 'recordIdsToDelete' list of individual
        GUIDs to delete - for example:
            {
                'form': {
                    'recordIdsToDelete': [
                        <individualGuid1>,
                        <individualGuid2>,
                        ...
                    }
                }
            }

    Response:
        json dictionary with the deleted GUIDs mapped to None:
            {
                <individualGuid1> : None,
                <individualGuid2> : None,
                ...
            }
    """

    # validate request
    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)

    request_json = json.loads(request.body)
    individuals_list = request_json.get('individuals')
    if individuals_list is None:
        return create_json_response(
            {}, status=400, reason="Invalid request: 'individuals' not in request_json")

    logger.info("delete_individuals_handler %s", request_json)

    individual_guids_to_delete = [ind['individualGuid'] for ind in individuals_list]

    # delete the individuals
    families_with_deleted_individuals = delete_individuals(project, individual_guids_to_delete)

    deleted_individuals_by_guid = {
        individual_guid: None for individual_guid in individual_guids_to_delete
    }

    families_by_guid = {
        family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True) for family in families_with_deleted_individuals
    }  # families whose list of individuals may have changed

    # send response
    return create_json_response({
        'individualsByGuid': deleted_individuals_by_guid,
        'familiesByGuid': families_by_guid,
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def receive_individuals_table_handler(request, project_guid):
    """Handler for the initial upload of an Excel or .tsv table of individuals. This handler
    parses the records, but doesn't save them in the database. Instead, it saves them to
    a temporary file and sends a 'uploadedFileId' representing this file back to the client. If/when the
    client then wants to 'apply' this table, it can send the uploadedFileId to the
    save_individuals_table(..) handler to actually save the data in the database.

    Args:
        request (object): Django request object
        project_guid (string): project GUID
    """

    project = get_project_and_check_permissions(project_guid, request.user)

    def process_records(json_records, filename='ped_file'):
        pedigree_records, errors, warnings = parse_pedigree_table(json_records, filename, user=request.user, project=project)
        if errors:
            raise ErrorsWarningsException(errors, warnings)
        return pedigree_records

    try:
        uploaded_file_id, filename, json_records = save_uploaded_file(request, process_records=process_records)
    except ErrorsWarningsException as e:
        return create_json_response({'errors': e.errors, 'warnings': e.warnings}, status=400, reason=e.errors)
    except Exception as e:
        return create_json_response({'errors': [e.message or str(e)], 'warnings': []}, status=400, reason=e.message or str(e))

    # send back some stats
    individual_ids_by_family = defaultdict(list)
    for r in json_records:
        if r.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN):
            individual_ids_by_family[r[JsonConstants.FAMILY_ID_COLUMN]].append(
                (r[JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN], True)
            )
        else:
            individual_ids_by_family[r[JsonConstants.FAMILY_ID_COLUMN]].append(
                (r[JsonConstants.INDIVIDUAL_ID_COLUMN], False)
            )

    num_individuals = sum([len(indiv_ids) for indiv_ids in individual_ids_by_family.values()])
    num_existing_individuals = 0
    missing_prev_ids = []
    for family_id, indiv_ids in individual_ids_by_family.items():
        existing_individuals = {i.individual_id for i in Individual.objects.filter(
            individual_id__in=[indiv_id for (indiv_id, _) in indiv_ids], family__family_id=family_id, family__project=project
        ).only('individual_id')}
        num_existing_individuals += len(existing_individuals)
        missing_prev_ids += [indiv_id for (indiv_id, is_previous) in indiv_ids if is_previous and indiv_id not in existing_individuals]
    num_individuals_to_create = num_individuals - num_existing_individuals
    if missing_prev_ids:
        return create_json_response(
            {'errors': [
                'Could not find individuals with the following previous IDs: {}'.format(', '.join(missing_prev_ids))
            ], 'warnings': []},
            status=400, reason='Invalid input')

    family_ids = set(r[JsonConstants.FAMILY_ID_COLUMN] for r in json_records)
    num_families = len(family_ids)
    num_existing_families = Family.objects.filter(family_id__in=family_ids, project=project).count()
    num_families_to_create = num_families - num_existing_families

    info = [
        "{num_families} families, {num_individuals} individuals parsed from {filename}".format(
            num_families=num_families, num_individuals=num_individuals, filename=filename
        ),
        "{} new families, {} new individuals will be added to the project".format(num_families_to_create, num_individuals_to_create),
        "{} existing individuals will be updated".format(num_existing_individuals),
    ]

    response = {
        'uploadedFileId': uploaded_file_id,
        'errors': [],
        'warnings': [],
        'info': info,
    }
    logger.info(response)
    return create_json_response(response)


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def save_individuals_table_handler(request, project_guid, upload_file_id):
    """Handler for 'save' requests to apply Individual tables previously uploaded through receive_individuals_table(..)

    Args:
        request (object): Django request object
        project_guid (string): project GUID
        uploadedFileId (string): a token sent to the client by receive_individuals_table(..)
    """
    project = get_project_and_check_permissions(project_guid, request.user)

    json_records = load_uploaded_file(upload_file_id)

    updated_families, updated_individuals = _add_or_update_individuals_and_families(
        project, individual_records=json_records, user=request.user
    )

    # edit individuals
    individuals = _get_json_for_individuals(updated_individuals, request.user, add_sample_guids_field=True)
    individuals_by_guid = {individual['individualGuid']: individual for individual in individuals}
    families = _get_json_for_families(updated_families, request.user, add_individual_guids_field=True)
    families_by_guid = {family['familyGuid']: family for family in families}

    updated_families_and_individuals_by_guid = {
        'individualsByGuid': individuals_by_guid,
        'familiesByGuid': families_by_guid,
    }

    return create_json_response(updated_families_and_individuals_by_guid)


def _add_or_update_individuals_and_families(project, individual_records, user=None):
    """Add or update individual and family records in the given project.

    Args:
        project (object): Django ORM model for the project to add families to
        individual_records (list): A list of JSON records representing individuals. See
            the return value of pedigree_info_utils#convert_fam_file_rows_to_json(..)

    Return:
        2-tuple: updated_families, updated_individuals containing Django ORM models
    """
    families = {}
    updated_individuals = set()
    parent_updates = []
    for i, record in enumerate(individual_records):
        # family id will be in different places in the json depending on whether it comes from a flat uploaded file or from the nested individual object
        family_id = record.get(JsonConstants.FAMILY_ID_COLUMN) or record.get('family', {}).get('familyId')
        if not family_id:
            raise ValueError("record #%s doesn't contain a 'familyId' key: %s" % (i, record))

        if JsonConstants.INDIVIDUAL_ID_COLUMN not in record and 'individualGuid' not in record:
            raise ValueError("record #%s doesn't contain an 'individualId' key: %s" % (i, record))

        family = families.get(family_id)
        if family:
            created = False
        else:
            family, created = get_or_create_seqr_model(Family, project=project, family_id=family_id)

        if created:
            logger.info("Created family: %s", family)

        # uploaded files do not have unique guid's so fall back to a combination of family and individualId
        if record.get('individualGuid'):
            individual_filters = {'guid': record['individualGuid']}
        else:
            individual_id = record.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN) or record[JsonConstants.INDIVIDUAL_ID_COLUMN]
            individual_filters = {'family': family, 'individual_id': individual_id}

        individual, created = get_or_create_seqr_model(Individual, **individual_filters)

        if created:
            record.update({
                'caseReviewStatus': 'I',
            })

        record['family'] = family
        record.pop('familyId', None)
        if individual.family != family:
            families[individual.family.family_id] = individual.family

        if record.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN):
            updated_individuals.update(individual.maternal_children.all())
            updated_individuals.update(individual.paternal_children.all())
            record['displayName'] = ''

        # Update the parent ids last, so if they are referencing updated individuals they will check for the correct ID
        if record.get('maternalId') or record.get('paternalId'):
            parent_updates.append({
                'individual': individual,
                'maternalId': record.pop('maternalId', None),
                'paternalId': record.pop('paternalId', None),
            })

        update_individual_from_json(individual, record, allow_unknown_keys=True, user=user)

        if record.get(JsonConstants.FAMILY_NOTES_COLUMN):
            update_family_from_json(family, {'analysis_notes': record[JsonConstants.FAMILY_NOTES_COLUMN]})

        updated_individuals.add(individual)
        families[family.family_id] = family

    for update in parent_updates:
        individual = update.pop('individual')
        update_individual_from_json(individual, update, user=user)

    updated_families = list(families.values())

    # update pedigree images
    update_pedigree_images(updated_families, project_guid=project.guid)

    return updated_families, list(updated_individuals)
