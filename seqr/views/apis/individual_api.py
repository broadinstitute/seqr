"""
APIs for retrieving, updating, creating, and deleting Individual records
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.model_utils import get_or_create_seqr_model, update_seqr_model, delete_seqr_model
from seqr.models import Sample, Individual, Family, CAN_EDIT
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.pedigree_image_api import update_pedigree_images
from seqr.views.apis.phenotips_api import create_patient, set_patient_hpo_terms, delete_patient, \
    PhenotipsException
from seqr.views.utils.export_table_utils import export_table
from seqr.views.utils.file_utils import save_uploaded_file, load_uploaded_file
from seqr.views.utils.json_to_orm_utils import update_individual_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual, _get_json_for_family
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table, validate_fam_file_records, JsonConstants
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions


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
                    maternalId: xxx,
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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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
                <individualGuid1> : { individualId: xxx, maternalId: xxx, paternalId: xxx, ...},
                <individualGuid2> : { individualId: xxx, maternalId: xxx, paternalId: xxx, ...},
                ...
            }
    """

    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)

    request_json = json.loads(request.body)

    modified_individuals_list = request_json.get('individuals')
    if modified_individuals_list is None:
        return create_json_response(
            {}, status=200, reason="'individuals' not specified")

    update_individuals = {ind['individualGuid']: ind for ind in modified_individuals_list}
    update_individual_models = {ind.guid: ind for ind in Individual.objects.filter(guid__in=update_individuals.keys())}

    modified_family_ids = {ind['family']['familyId'] for ind in modified_individuals_list}
    modified_family_ids.update({ind.family.family_id for ind in update_individual_models.values()})
    related_individuals = Individual.objects.filter(
        family__family_id__in=modified_family_ids, family__project=project).exclude(guid__in=update_individuals.keys())
    # can't use _get_json_for_individual because validation needs familyId, not familyGuid
    related_individuals_json = [{
        'individualId': ind.individual_id,
        'familyId': ind.family.family_id,
        'sex': ind.sex,
        'maternalId': ind.maternal_id,
        'paternalId': ind.paternal_id,
    } for ind in related_individuals]
    individuals_list = modified_individuals_list + related_individuals_json

    # TODO more validation?
    errors, warnings = validate_fam_file_records(individuals_list, fail_on_warnings=True)
    if errors:
        return create_json_response({'errors': errors, 'warnings': warnings}, status=400, reason='Invalid updates')

    updated_families, updated_individuals = add_or_update_individuals_and_families(
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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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

    def parse_file(filename, stream):
        pedigree_records, errors, warnings = parse_pedigree_table(filename, stream, user=request.user, project=project)
        if errors:
            raise ErrorsWarningsException(errors, warnings)
        return pedigree_records

    try:
        uploaded_file_id, filename, json_records = save_uploaded_file(request, parse_file)
    except ErrorsWarningsException as e:
        return create_json_response({'errors': e.errors, 'warnings': e.warnings}, status=400, reason=e.errors)
    except Exception as e:
        return create_json_response({'errors': [e.message or str(e)], 'warnings': []}, status=400, reason=e.message or str(e))

    # send back some stats
    num_families = len(set(r['familyId'] for r in json_records))
    num_individuals = len(set(r['individualId'] for r in json_records))
    num_families_to_create = len([
        family_id for family_id in set(r['familyId'] for r in json_records)
        if not Family.objects.filter(family_id=family_id, project=project)])

    num_individuals_to_create = len(set(
        r['individualId'] for r in json_records
        if not Individual.objects.filter(
            individual_id=r['individualId'],
            family__family_id=r['familyId'],
            family__project=project)))

    info = [
        "{num_families} families, {num_individuals} individuals parsed from {filename}".format(
            num_families=num_families, num_individuals=num_individuals, filename=filename
        ),
        "%d new families, %d new individuals will be added to the project" % (num_families_to_create, num_individuals_to_create),
        "%d existing individuals will be updated" % (num_individuals - num_individuals_to_create),
    ]

    response = {
        'uploadedFileId': uploaded_file_id,
        'errors': [],
        'warnings': [],
        'info': info,
    }
    logger.info(response)
    return create_json_response(response)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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

    updated_families, updated_individuals = add_or_update_individuals_and_families(
        project, individual_records=json_records, user=request.user
    )

    # edit individuals
    individuals_by_guid = {
        individual.guid: _get_json_for_individual(individual, request.user, add_sample_guids_field=True) for individual in updated_individuals
    }

    families_by_guid = {
        family.guid: _get_json_for_family(family, request.user, add_individual_guids_field=True) for family in updated_families
    }  # families whose list of individuals may have changed

    updated_families_and_individuals_by_guid = {
        'individualsByGuid': individuals_by_guid,
        'familiesByGuid': families_by_guid,
    }

    return create_json_response(updated_families_and_individuals_by_guid)


def add_or_update_individuals_and_families(project, individual_records, user=None):
    """Add or update individual and family records in the given project.

    Args:
        project (object): Django ORM model for the project to add families to
        individual_records (list): A list of JSON records representing individuals. See
            the return value of pedigree_info_utils#convert_fam_file_rows_to_json(..)

    Return:
        2-tuple: updated_families, updated_individuals containing Django ORM models
    """
    families = {}
    updated_individuals = []
    for i, record in enumerate(individual_records):
        # family id will be in different places in the json depending on whether it comes from a flat uploaded file or from the nested individual object
        family_id = record.get('familyId') or record.get('family', {}).get('familyId')
        if not family_id:
            raise ValueError("record #%s doesn't contain a 'familyId' key: %s" % (i, record))

        if 'individualId' not in record and 'individualGuid' not in record:
            raise ValueError("record #%s doesn't contain an 'individualId' key: %s" % (i, record))

        family, created = get_or_create_seqr_model(Family, project=project, family_id=family_id)

        if created:
            logger.info("Created family: %s", family)
            if not family.display_name:
                update_seqr_model(family, display_name = family.family_id)

        # uploaded files do not have unique guid's so fall back to a combination of family and individualId
        if record.get('individualGuid'):
            individual_filters = {'guid': record['individualGuid']}
        else:
            individual_filters = {'family': family, 'individual_id': record['individualId']}

        individual, created = get_or_create_seqr_model(Individual, **individual_filters)
        record['family'] = family
        record.pop('familyId', None)
        update_individual_from_json(individual, record, allow_unknown_keys=True, user=user)

        updated_individuals.append(individual)

        # apply additional json fields which don't directly map to Individual model fields
        individual.phenotips_eid = individual.guid  # use guid instead of indiv_id to avoid collisions

        if created:
            # create new PhenoTips patient record
            patient_record = create_patient(project, individual)
            update_seqr_model(
                individual,
                phenotips_patient_id=patient_record['id'],
                case_review_status='I'
            )

            logger.info("Created PhenoTips record with patient id %s and external id %s" % (
                str(individual.phenotips_patient_id), str(individual.phenotips_eid)))

        if record.get(JsonConstants.HPO_TERMS_PRESENT_COLUMN) or record.get(JsonConstants.FINAL_DIAGNOSIS_OMIM_COLUMN):
            # update phenotips hpo ids
            logger.info("Setting PhenoTips HPO Terms to: %s" % (record.get(JsonConstants.HPO_TERMS_PRESENT_COLUMN),))
            set_patient_hpo_terms(
                project,
                individual,
                hpo_terms_present=record.get(JsonConstants.HPO_TERMS_PRESENT_COLUMN, []),
                hpo_terms_absent=record.get(JsonConstants.HPO_TERMS_ABSENT_COLUMN, []),
                final_diagnosis_mim_ids=record.get(JsonConstants.FINAL_DIAGNOSIS_OMIM_COLUMN, []))

        if not individual.display_name:
            update_seqr_model(individual, display_name=individual.individual_id)

        families[family.family_id] = family

    updated_families = list(families.values())

    # update pedigree images
    update_pedigree_images(updated_families)

    return updated_families, updated_individuals


def delete_individuals(project, individual_guids):
    """Delete one or more individuals

    Args:
        project (object): Django ORM model for project
        individual_guids (list): GUIDs of individuals to delete

    Returns:
        list: Family objects for families with deleted individuals
    """

    individuals_to_delete = Individual.objects.filter(
        family__project=project, guid__in=individual_guids)

    samples_to_delete = Sample.objects.filter(
        individual__family__project=project, individual__guid__in=individual_guids)

    for sample in samples_to_delete:
        logger.info("Deleting sample: %s" % sample)
        sample.delete()

    families = {}
    for individual in individuals_to_delete:
        families[individual.family.family_id] = individual.family

        # delete phenotips records
        try:
            delete_patient(project, individual)
        except (PhenotipsException, ValueError) as e:
            logger.error("Error: couldn't delete patient from phenotips: %s %s",
                         individual.phenotips_eid,
                         individual)

        # delete Individual
        delete_seqr_model(individual)


    update_pedigree_images(families.values())

    families_with_deleted_individuals = list(families.values())

    return families_with_deleted_individuals


def export_individuals(
    filename_prefix,
    individuals,
    file_format,

    include_project_name=False,
    include_display_name=False,
    include_created_date=False,
    include_case_review_status=False,
    include_case_review_last_modified_date=False,
    include_case_review_last_modified_by=False,
    include_case_review_discussion=False,
    include_hpo_terms_present=False,
    include_hpo_terms_absent=False,
    include_paternal_ancestry=False,
    include_maternal_ancestry=False,
    include_age_of_onset=False,
):
    """Export Individuals table.

    Args:
        filename_prefix (string): Filename without the file extension.
        individuals (list): List of Django Individual objects to include in the table
        file_format (string): "xls" or "tsv"

    Returns:
        Django HttpResponse object with the table data as an attachment.
    """

    header = []
    if include_project_name:
        header.append('Project')

    header.extend([
        'Family ID',
        'Individual ID',
        'Paternal ID',
        'Maternal ID',
        'Sex',
        'Affected Status',
        'Notes',
    ])

    if include_display_name:
        header.append('Display Name')
    if include_created_date:
        header.append('Created Date')
    if include_case_review_status:
        header.append('Case Review Status')
    if include_case_review_last_modified_date:
        header.append('Case Review Status Last Modified')
    if include_case_review_last_modified_by:
        header.append('Case Review Status Last Modified By')
    if include_case_review_discussion:
        header.append('Case Review Discussion')
    if include_hpo_terms_present:
        header.append('HPO Terms (present)')
    if include_hpo_terms_absent:
        header.append('HPO Terms (absent)')
    if include_paternal_ancestry:
        header.append('Paternal Ancestry')
    if include_maternal_ancestry:
        header.append('Maternal Ancestry')
    if include_age_of_onset:
        header.append('Age of Onset')

    rows = []
    for i in individuals:
        row = []
        if include_project_name:
            row.extend([i.family.project.name or i.family.project.project_id])

        row.extend([
            i.family.family_id,
            i.individual_id,
            i.paternal_id,
            i.maternal_id,
            _SEX_TO_EXPORTED_VALUE.get(i.sex),
            __AFFECTED_TO_EXPORTED_VALUE.get(i.affected),
            i.notes,  # TODO should strip markdown (or be moved to client-side export)
        ])

        if include_display_name:
            row.append(i.display_name)
        if include_created_date:
            row.append(i.created_date)
        if include_case_review_status:
            row.append(Individual.CASE_REVIEW_STATUS_LOOKUP.get(i.case_review_status, ''))
        if include_case_review_last_modified_date:
            row.append(i.case_review_status_last_modified_date)
        if include_case_review_last_modified_by:
            row.append(_user_to_string(i.case_review_status_last_modified_by))
        if include_case_review_discussion:
            row.append(i.case_review_discussion)

        if (include_hpo_terms_present or \
            include_hpo_terms_absent or \
            include_paternal_ancestry or \
            include_maternal_ancestry or \
            include_age_of_onset):
            if i.phenotips_data:
                phenotips_json = json.loads(i.phenotips_data)
                phenotips_fields = _parse_phenotips_data(phenotips_json)
            else:
                phenotips_fields = {}

            if include_hpo_terms_present:
                row.append(phenotips_fields.get('phenotips_features_present', ''))
            if include_hpo_terms_absent:
                row.append(phenotips_fields.get('phenotips_features_absent', ''))
            if include_paternal_ancestry:
                row.append(phenotips_fields.get('paternal_ancestry', ''))
            if include_maternal_ancestry:
                row.append(phenotips_fields.get('maternal_ancestry', ''))
            if include_age_of_onset:
                row.append(phenotips_fields.get('age_of_onset', ''))

        rows.append(row)

    return export_table(filename_prefix, header, rows, file_format)


def _user_to_string(user):
    """Takes a Django User object and returns a string representation"""
    if not user:
        return ''

    return user.email or user.username


def _get_all_individuals(project, individual_guids):
    """
    Retrieves Django ORM Individual objects for the given GUIDs.

    Args:
        project (object): Django ORM model for the project that contains these individuals
        individual_records (list): A list of individual GUIDs

    Return:
         list: Django ORM Individual objects for the given GUIDs

    Raises:
        ValueError if one or more GUIDs are invalid

    """
    individuals = Individual.objects.filter(family__project=project, guid__in=individual_guids)

    if len(individuals) != len(individual_guids):
        unknown_guids = list(
            set(individual_guids) - set([individual.guid for individual in individuals])
        )

        raise ValueError("Unable to find individuals with these GUIDs in project %s: %s" % (
            project, unknown_guids))

    return list(individuals)

def _parse_phenotips_data(phenotips_json):
    """Takes a phenotips_json dictionary for a single Individual and converts it to a more convenient
    representation which is a flat dictionary of key-value pairs with the following keys:

        phenotips_features_present
        phenotips_features_absent
        previously_tested_genes
        candidate_genes
        paternal_ancestry
        maternal_ancestry
        age_of_onset
        ...

    Args:
        phenotips_json (dict): The PhenoTips json from an Individual

    Returns:
        dict: flat dictionary of key-value pairs
    """

    result = {
        'phenotips_features_present': '',
        'phenotips_features_absent': '',
        'previously_tested_genes': '',
        'candidate_genes': '',
        'paternal_ancestry': '',
        'maternal_ancestry': '',
        'age_of_onset': '',
    }

    if phenotips_json.get('features'):
        result['phenotips_features_present'] = []
        result['phenotips_features_absent'] = []
        for feature in phenotips_json.get('features'):
            if feature.get('observed') == 'yes':
                result['phenotips_features_present'].append(feature.get('label'))
            elif feature.get('observed') == 'no':
                result['phenotips_features_absent'].append(feature.get('label'))
        result['phenotips_features_present'] = ', '.join(result['phenotips_features_present'])
        result['phenotips_features_absent'] = ', '.join(result['phenotips_features_absent'])

    if phenotips_json.get('rejectedGenes'):
        result['previously_tested_genes'] = []
        for gene in phenotips_json.get('rejectedGenes'):
            result['previously_tested_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        result['previously_tested_genes'] = ', '.join(result['previously_tested_genes'])

    if phenotips_json.get('genes'):
        result['candidate_genes'] = []
        for gene in phenotips_json.get('genes'):
            result['candidate_genes'].append("%s (%s)" % (gene.get('gene', '').strip(), gene.get('comments', '').strip()))
        result['candidate_genes'] = ', '.join(result['candidate_genes'])

    if phenotips_json.get('ethnicity'):
        ethnicity = phenotips_json.get('ethnicity')
        if ethnicity.get('paternal_ethnicity'):
            result['paternal_ancestry'] = ", ".join(ethnicity.get('paternal_ethnicity'))

        if ethnicity.get('maternal_ethnicity'):
            result['maternal_ancestry'] = ", ".join(ethnicity.get('maternal_ethnicity'))

    if phenotips_json.get('global_age_of_onset'):
        result['age_of_onset'] = ", ".join((a.get('label') for a in phenotips_json.get('global_age_of_onset') if a))

    return result
