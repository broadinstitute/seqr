"""
APIs for retrieving, updating, creating, and deleting Individual records
"""
import json
import logging
import re
from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

from reference_data.models import HumanPhenotypeOntology
from seqr.models import Individual, Family
from seqr.views.utils.pedigree_image_utils import update_pedigree_images
from seqr.views.utils.file_utils import save_uploaded_file, load_uploaded_file
from seqr.views.utils.json_to_orm_utils import update_individual_from_json, update_family_from_json, \
    update_model_from_json, create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual, _get_json_for_individuals, _get_json_for_family, _get_json_for_families
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table, validate_fam_file_records, JsonConstants
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions
from seqr.views.utils.individual_utils import delete_individuals, get_parsed_feature
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

    check_project_permissions(project, request.user, can_edit=True)

    request_json = json.loads(request.body)

    update_individual_from_json(individual, request_json, user=request.user, allow_unknown_keys=True)

    return create_json_response({
        individual.guid: _get_json_for_individual(individual, request.user)
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_individual_hpo_terms(request, individual_guid):
    """Updates features fields for the given Individual
    """

    individual = Individual.objects.get(guid=individual_guid)

    project = individual.family.project

    check_project_permissions(project, request.user, can_edit=True)

    request_json = json.loads(request.body)

    update_json = {
        key: [get_parsed_feature(feature) for feature in request_json[key]] if request_json.get(key) else None
        for key in ['features', 'absentFeatures', 'nonstandardFeatures', 'absentNonstandardFeatures']
    }
    update_model_from_json(individual, update_json, user=request.user)

    return create_json_response({
        individual.guid: _get_json_for_individual(individual, request.user, add_hpo_details=True)
    })


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
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

    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

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

    updated_families, updated_individuals = _add_or_update_individuals_and_families(
        project, modified_individuals_list, user=request.user
    )

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
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

    request_json = json.loads(request.body)
    individuals_list = request_json.get('individuals')
    if individuals_list is None:
        return create_json_response(
            {}, status=400, reason="Invalid request: 'individuals' not in request_json")

    logger.info("delete_individuals_handler %s", request_json)

    individual_guids_to_delete = [ind['individualGuid'] for ind in individuals_list]

    # delete the individuals
    families_with_deleted_individuals = delete_individuals(project, individual_guids_to_delete, request.user)

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

    warnings = []
    def process_records(json_records, filename='ped_file'):
        pedigree_records, errors, ped_warnings = parse_pedigree_table(json_records, filename, user=request.user, project=project)
        if errors:
            raise ErrorsWarningsException(errors, ped_warnings)
        nonlocal warnings
        warnings += ped_warnings
        return pedigree_records

    try:
        uploaded_file_id, filename, json_records = save_uploaded_file(request, process_records=process_records)
    except ErrorsWarningsException as e:
        return create_json_response({'errors': e.errors, 'warnings': e.warnings}, status=400, reason=e.errors)
    except Exception as e:
        return create_json_response({'errors': [str(e)], 'warnings': []}, status=400, reason=str(e))

    if warnings:
        # If there are warnings, it might be because the upload referenced valid existing individuals and there is no
        # issue, or because it referenced individuals that actually don't exist, so re-validate with all individuals
        family_ids = {r[JsonConstants.FAMILY_ID_COLUMN] for r in json_records}
        individual_ids = {r[JsonConstants.INDIVIDUAL_ID_COLUMN] for r in json_records}

        related_individuals = Individual.objects.filter(
            family__family_id__in=family_ids, family__project=project).exclude(individual_id__in=individual_ids)
        related_individuals_json = _get_json_for_individuals(
            related_individuals, project_guid=project_guid, family_fields=['family_id'])

        errors, _ = validate_fam_file_records(json_records + related_individuals_json, fail_on_warnings=True)
        if errors:
            return create_json_response({'errors': errors, 'warnings': []}, status=400, reason=errors)

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


def _add_or_update_individuals_and_families(project, individual_records, user):
    """Add or update individual and family records in the given project.

    Args:
        project (object): Django ORM model for the project to add families to
        individual_records (list): A list of JSON records representing individuals. See
            the return value of pedigree_info_utils#convert_fam_file_rows_to_json(..)

    Return:
        2-tuple: updated_families, updated_individuals containing Django ORM models
    """
    updated_families = set()
    updated_individuals = set()
    parent_updates = []

    family_ids = {_get_record_family_id(record) for record in individual_records}
    families_by_id = {f.family_id: f for f in Family.objects.filter(project=project, family_id__in=family_ids)}

    missing_family_ids = family_ids - set(families_by_id.keys())
    for family_id in missing_family_ids:
        family = create_model_from_json(Family, {'project': project, 'family_id': family_id}, user)
        families_by_id[family_id] = family
        updated_families.add(family)
        logger.info('Created family: {}'.format(family))

    individual_models = Individual.objects.filter(family__project=project).prefetch_related(
        'family', 'mother', 'father')
    has_individual_guid = any(record.get('individualGuid') for record in individual_records)
    if has_individual_guid:
        individual_lookup = {
            i.guid: i for i in individual_models.filter(
            guid__in=[record['individualGuid'] for record in individual_records])
        }
    else:
        individual_lookup = defaultdict(dict)
        for i in individual_models.filter(
                individual_id__in=[_get_record_individual_id(record) for record in individual_records]):
            individual_lookup[i.individual_id][i.family] = i

    for record in individual_records:
        family_id = _get_record_family_id(record)
        family = families_by_id.get(family_id)

        if has_individual_guid:
            individual = individual_lookup[record.pop('individualGuid')]
        else:
            # uploaded files do not have unique guid's so fall back to a combination of family and individualId
            individual_id = _get_record_individual_id(record)
            individual = individual_lookup[individual_id].get(family)
            if not individual:
                individual = create_model_from_json(
                    Individual, {'family': family, 'individual_id': individual_id, 'case_review_status': 'I'}, user)

        record['family'] = family
        record.pop('familyId', None)
        if individual.family != family:
            family = individual.family
            updated_families.add(family)

        previous_id = record.pop(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN, None)
        if previous_id:
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

        family_notes = record.pop(JsonConstants.FAMILY_NOTES_COLUMN, None)
        if family_notes:
            update_family_from_json(family, {'analysis_notes': family_notes}, user)
            updated_families.add(family)

        is_updated = update_individual_from_json(individual, record, user=user, allow_unknown_keys=True)
        if is_updated:
            updated_individuals.add(individual)
            updated_families.add(family)

    for update in parent_updates:
        individual = update.pop('individual')
        update_individual_from_json(individual, update, user=user)

    # update pedigree images
    update_pedigree_images(updated_families, user, project_guid=project.guid)

    return list(updated_families), list(updated_individuals)


def _get_record_family_id(record):
    # family id will be in different places in the json depending on whether it comes from a flat uploaded file or from the nested individual object
    return record.get(JsonConstants.FAMILY_ID_COLUMN) or record.get('family', {})['familyId']


def _get_record_individual_id(record):
    return record.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN) or record[JsonConstants.INDIVIDUAL_ID_COLUMN]


# Use column keys that align with phenotips fields to support phenotips json export format
FAMILY_ID_COLUMN = 'family_id'
INDIVIDUAL_ID_COLUMN = 'external_id'
INDIVIDUAL_GUID_COLUMN = 'individual_guid'
HPO_TERMS_PRESENT_COLUMN = 'hpo_present'
HPO_TERMS_ABSENT_COLUMN = 'hpo_absent'
HPO_TERM_NUMBER_COLUMN = 'hpo_number'
AFFECTED_COLUMN = 'affected'
FEATURES_COLUMN = 'features'


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def receive_hpo_table_handler(request, project_guid):
    """Handler for bulk update of hpo terms. This handler parses the records, but doesn't save them in the database.
    Instead, it saves them to a temporary file and sends a 'uploadedFileId' representing this file back to the client.

    Args:
        request (object): Django request object
        project_guid (string): project GUID
    """

    project = get_project_and_check_permissions(project_guid, request.user)

    def process_records(json_records, filename=''):
        records, errors, warnings = _process_hpo_records(json_records, filename, project)
        if errors:
            raise ErrorsWarningsException(errors, warnings)
        return records, warnings

    try:
        uploaded_file_id, _, (json_records, warnings) = save_uploaded_file(request, process_records=process_records)
    except ErrorsWarningsException as e:
        return create_json_response({'errors': e.errors, 'warnings': e.warnings}, status=400, reason=e.errors)
    except Exception as e:
        return create_json_response({'errors': [str(e)], 'warnings': []}, status=400, reason=str(e))

    response = {
        'uploadedFileId': uploaded_file_id,
        'errors': [],
        'warnings': warnings,
        'info': ['{} individuals will be updated'.format(len(json_records))],
    }
    return create_json_response(response)


def _process_hpo_records(records, filename, project):
    if filename.endswith('.json'):
        row_dicts = records
        column_map = set(row_dicts[0].keys())
    else:
        column_map = {}
        for i, field in enumerate(records[0]):
            key = field.lower()
            if 'family' in key or 'pedigree' in key:
                column_map[FAMILY_ID_COLUMN] = i
            elif 'individual' in key:
                column_map[INDIVIDUAL_ID_COLUMN] = i
            elif re.match("hpo.*present", key):
                column_map[HPO_TERMS_PRESENT_COLUMN] = i
            elif re.match("hpo.*absent", key):
                column_map[HPO_TERMS_ABSENT_COLUMN] = i
            elif re.match("hp.*number*", key):
                if not HPO_TERM_NUMBER_COLUMN in column_map:
                    column_map[HPO_TERM_NUMBER_COLUMN] = []
                column_map[HPO_TERM_NUMBER_COLUMN].append(i)
            elif 'affected' in key:
                column_map[AFFECTED_COLUMN] = i
        if INDIVIDUAL_ID_COLUMN not in column_map:
            raise ValueError('Invalid header, missing individual id column')

        row_dicts = [{column: row[index] if isinstance(index, int) else next((row[i] for i in index if row[i]), None)
                      for column, index in column_map.items()} for row in records[1:]]

    if FEATURES_COLUMN in column_map:
        for row in row_dicts:
            row[HPO_TERMS_PRESENT_COLUMN] = []
            row[HPO_TERMS_ABSENT_COLUMN] = []
            for feature in row[FEATURES_COLUMN]:
                column = HPO_TERMS_PRESENT_COLUMN if feature['observed'] == 'yes' else HPO_TERMS_ABSENT_COLUMN
                row[column].append(feature['id'])

        return _parse_individual_hpo_terms(row_dicts, project)

    if HPO_TERMS_PRESENT_COLUMN in column_map or HPO_TERMS_ABSENT_COLUMN in column_map:
        for row in row_dicts:
            row[HPO_TERMS_PRESENT_COLUMN] = _parse_hpo_terms(row.get(HPO_TERMS_PRESENT_COLUMN))
            row[HPO_TERMS_ABSENT_COLUMN] = _parse_hpo_terms(row.get(HPO_TERMS_ABSENT_COLUMN))
        return _parse_individual_hpo_terms(row_dicts, project)

    if HPO_TERM_NUMBER_COLUMN in column_map:
        aggregate_rows = defaultdict(lambda: {HPO_TERMS_PRESENT_COLUMN: [], HPO_TERMS_ABSENT_COLUMN: []})
        for row in row_dicts:
            column = HPO_TERMS_ABSENT_COLUMN if row.get(AFFECTED_COLUMN) == 'no' else HPO_TERMS_PRESENT_COLUMN
            aggregate_entry = aggregate_rows[(row.get(FAMILY_ID_COLUMN), row.get(INDIVIDUAL_ID_COLUMN))]
            if row.get(HPO_TERM_NUMBER_COLUMN):
                aggregate_entry[column].append(row[HPO_TERM_NUMBER_COLUMN].strip())
            else:
                aggregate_entry[column] = []
        return _parse_individual_hpo_terms([{
            FAMILY_ID_COLUMN: family_id,
            INDIVIDUAL_ID_COLUMN: individual_id,
            HPO_TERMS_PRESENT_COLUMN: features[HPO_TERMS_PRESENT_COLUMN],
            HPO_TERMS_ABSENT_COLUMN: features[HPO_TERMS_ABSENT_COLUMN]
        } for (family_id, individual_id), features in aggregate_rows.items()], project)

    raise ValueError('Invalid header, missing hpo terms columns')


def _parse_hpo_terms(hpo_term_string):
    if not hpo_term_string:
        return []
    return [hpo_term.strip().split('(')[0].strip() for hpo_term in hpo_term_string.replace(',', ';').split(';')]


def _has_same_features(individual, present_features, absent_features):
    return {feature['id'] for feature in individual.features or []} == set(present_features) and \
           {feature['id'] for feature in individual.absent_features or []} == set(absent_features)


def _parse_individual_hpo_terms(json_records, project):
    errors = []
    warnings = []
    parsed_records = []

    all_hpo_terms = set()
    for record in json_records:
        all_hpo_terms.update(record[HPO_TERMS_PRESENT_COLUMN])
        all_hpo_terms.update(record[HPO_TERMS_ABSENT_COLUMN])
    hpo_terms = set(HumanPhenotypeOntology.objects.filter(hpo_id__in=all_hpo_terms).values_list('hpo_id', flat=True))

    missing_individuals = []
    unchanged_individuals = []
    invalid_hpo_term_individuals = defaultdict(list)
    for record in json_records:
        family_id = record.get(FAMILY_ID_COLUMN, None)
        individual_id = record.get(INDIVIDUAL_ID_COLUMN)
        individual_q = Individual.objects.filter(
            individual_id__in=[individual_id, '{}_{}'.format(family_id, individual_id)],
            family__project=project,
        )
        if family_id:
            individual_q = individual_q.filter(family__family_id=family_id)
        individual = individual_q.first()
        if individual:
            present_features = []
            absent_features = []
            for feature in record[HPO_TERMS_PRESENT_COLUMN]:
                if feature in hpo_terms:
                    present_features.append(feature)
                else:
                    invalid_hpo_term_individuals[feature].append(individual_id)
            for feature in record[HPO_TERMS_ABSENT_COLUMN]:
                if feature in hpo_terms:
                    absent_features.append(feature)
                else:
                    invalid_hpo_term_individuals[feature].append(individual_id)

            if _has_same_features(individual, present_features, absent_features):
                unchanged_individuals.append(individual_id)
            else:
                parsed_records.append({
                    INDIVIDUAL_GUID_COLUMN: individual.guid,
                    HPO_TERMS_PRESENT_COLUMN: present_features,
                    HPO_TERMS_ABSENT_COLUMN: absent_features,
                })
        else:
            missing_individuals.append(individual_id)

    if not parsed_records:
        errors.append('Unable to find individuals to update for any of the {total} parsed individuals.{missing}{unchanged}'.format(
            total=len(missing_individuals) + len(unchanged_individuals),
            missing=' No matching ids found for {} individuals.'.format(len(missing_individuals)) if missing_individuals else '',
            unchanged=' No changes detected for {} individuals.'.format(len(unchanged_individuals)) if unchanged_individuals else '',
        ))

    if invalid_hpo_term_individuals:
        warnings.append(
            "The following HPO terms were not found in seqr's HPO data and will not be added: {}".format(
                '; '.join(['{} ({})'.format(term, ', '.join(individuals)) for term, individuals in sorted(invalid_hpo_term_individuals.items())])
            )
        )
    if missing_individuals:
        warnings.append(
            'Unable to find matching ids for {} individuals. The following entries will not be updated: {}'.format(
                len(missing_individuals), ', '.join(missing_individuals)
            ))
    if unchanged_individuals:
        warnings.append(
            'No changes detected for {} individuals. The following entries will not be updated: {}'.format(
                len(unchanged_individuals), ', '.join(sorted(unchanged_individuals))
            ))

    return parsed_records, errors, warnings


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def save_hpo_table_handler(request, project_guid, upload_file_id):
    """
    Handler for 'save' requests to apply HPO terms tables previously uploaded through receive_hpo_table_handler
    """
    project = get_project_and_check_permissions(project_guid, request.user)

    json_records, _ = load_uploaded_file(upload_file_id)

    individual_guids = [record[INDIVIDUAL_GUID_COLUMN] for record in json_records]
    individuals_by_guid = {
        i.guid: i for i in Individual.objects.filter(family__project=project, guid__in=individual_guids)
    }

    for record in json_records:
        individual = individuals_by_guid[record[INDIVIDUAL_GUID_COLUMN]]
        update_model_from_json(individual, {
            'features': [{'id': feature} for feature in record[HPO_TERMS_PRESENT_COLUMN]],
            'absent_features': [{'id': feature} for feature in record[HPO_TERMS_ABSENT_COLUMN]],
        }, user=request.user)

    return create_json_response({
        'individualsByGuid': {
            individual['individualGuid']: individual for individual in _get_json_for_individuals(
            list(individuals_by_guid.values()), user=request.user, add_hpo_details=True,
        )},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def get_hpo_terms(request, hpo_parent_id):
    """
    Get all the HPO Terms with the given parent ID
    """

    return create_json_response({
        hpo_parent_id: {
            hpo.hpo_id: {'id': hpo.hpo_id, 'category': hpo.category_id, 'label': hpo.name}
            for hpo in HumanPhenotypeOntology.objects.filter(parent_id=hpo_parent_id)
        }
    })
