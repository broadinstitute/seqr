"""
seqr integrates with the `PhenoTips <http://phenotips.org>`_ UI so that users can enter
detailed phenotype information for individuals.
The PhenoTips server is installed locally so that it's not visible to the outside network, and
seqr then acts as a proxy for all HTTP requests between the PhenoTips web-based UI (which is
running in users' browser), and the PhenoTips server (running on the internal network).

This proxy setup allows seqr to check authentication and authorization before allowing users to
access patients in PhenoTips, and is similar to how seqr manages access to the SQL database and
other internal systems.

This module implements the proxy functionality + methods for making requests to PhenoTips HTTP APIs.

PhenoTips API docs are at:

https://phenotips.org/DevGuide/API
https://phenotips.org/DevGuide/RESTfulAPI
https://phenotips.org/DevGuide/PermissionsRESTfulAPI
"""

from datetime import datetime
import json
import logging
import re
import requests
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from reference_data.models import HumanPhenotypeOntology
from seqr.models import Project, CAN_EDIT, CAN_VIEW, Individual
from seqr.views.utils.file_utils import save_uploaded_file
from seqr.views.utils.json_utils import create_json_response, _to_snake_case
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual
from seqr.views.utils.permissions_utils import check_permissions, get_project_and_check_permissions
from seqr.views.utils.phenotips_utils import get_phenotips_uname_and_pwd_for_project, make_phenotips_api_call, \
    phenotips_patient_url, phenotips_patient_exists
from seqr.views.utils.proxy_request_utils import proxy_request
from settings import API_LOGIN_REQUIRED_URL, PHENOTIPS_ADMIN_UNAME, PHENOTIPS_ADMIN_PWD, PHENOTIPS_SERVER

logger = logging.getLogger(__name__)

PHENOTIPS_QUICK_SAVE_URL_REGEX = "/bin/preview/data/(P[0-9]{1,20})"

DO_NOT_PROXY_URL_KEYWORDS = [
    '/delete',
    '/logout',
    '/login',
    '/admin',
    '/CreatePatientRecord',
    '/bin/PatientAccessRightsManagement',
    '/ForgotUsername',
    '/ForgotPassword',
]

FAMILY_ID_COLUMN = 'family_id'
INDIVIDUAL_ID_COLUMN = 'external_id'
HPO_TERMS_PRESENT_COLUMN = 'hpo_present'
HPO_TERMS_ABSENT_COLUMN = 'hpo_absent'
HPO_TERM_NUMBER_COLUMN = 'hpo_number'
AFFECTED_COLUMN = 'affected'
FEATURES_COLUMN = 'features'


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def receive_hpo_table_handler(request, project_guid):
    """Handler for bulk update of hpo terms. This handler parses the records, but doesn't save them in the database.
    Instead, it saves them to a temporary file and sends a 'uploadedFileId' representing this file back to the client.

    Args:
        request (object): Django request object
        project_guid (string): project GUID
    """

    project = get_project_and_check_permissions(project_guid, request.user)

    try:
        uploaded_file_id, _, json_records = save_uploaded_file(request, process_records=_process_hpo_records)
    except Exception as e:
        return create_json_response({'errors': [e.message or str(e)], 'warnings': []}, status=400, reason=e.message or str(e))

    all_hpo_terms = set()
    for record in json_records:
        all_hpo_terms.update([feature['id'] for feature in record.get(FEATURES_COLUMN) or []])
    hpo_terms = {hpo.hpo_id: hpo for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_hpo_terms)}

    updates_by_individual_guid = {}
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
            features = []
            for feature in record.get(FEATURES_COLUMN) or []:
                hpo_data = hpo_terms.get(feature['id'])
                if hpo_data:
                    feature['category'] = hpo_data.category_id
                    feature['label'] = hpo_data.name
                    features.append(feature)
                else:
                    invalid_hpo_term_individuals[feature['id']].append(individual_id)

            if _has_same_features(individual, features):
                unchanged_individuals.append(individual_id)
            else:
                updates_by_individual_guid[individual.guid] = features
        else:
            missing_individuals.append(individual_id)

    if not updates_by_individual_guid:
        return create_json_response({
            'errors': ['Unable to find individuals to update for any of the {total} parsed individuals.{missing}{unchanged}'.format(
                total=len(missing_individuals) + len(unchanged_individuals),
                missing=' No matching ids found for {} individuals.'.format(len(missing_individuals)) if missing_individuals else '',
                unchanged=' No changes detected for {} individuals.'.format(len(unchanged_individuals)) if unchanged_individuals else '',
            )],
            'warnings': []
        }, status=400, reason='Unable to find any matching individuals')

    warnings = []
    if invalid_hpo_term_individuals:
        warnings.append(
            "The following HPO terms were not found in seqr's HPO data and will not be added: {}".format(
                '; '.join(['{} ({})'.format(term, ', '.join(individuals)) for term, individuals in invalid_hpo_term_individuals.items()])
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
                len(unchanged_individuals), ', '.join(unchanged_individuals)
            ))

    response = {
        'updatesByIndividualGuid': updates_by_individual_guid,
        'uploadedFileId': uploaded_file_id,
        'errors': [],
        'warnings': warnings,
        'info': ['{} individuals will be updated'.format(len(updates_by_individual_guid))],
    }
    return create_json_response(response)


def _process_hpo_records(records, filename=''):
    if filename.endswith('.json'):
        return records

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
        elif 'feature' in key:
            column_map[FEATURES_COLUMN] = i
    if INDIVIDUAL_ID_COLUMN not in column_map:
        raise ValueError('Invalid header, missing individual id column')

    row_dicts = [{column: row[index] if isinstance(index, int) else next((row[i] for i in index if row[i]), None)
                  for column, index in column_map.items()} for row in records[1:]]
    if FEATURES_COLUMN in column_map:
        return row_dicts

    if HPO_TERMS_PRESENT_COLUMN in column_map or HPO_TERMS_ABSENT_COLUMN in column_map:
        for row in row_dicts:
            row[FEATURES_COLUMN] = _parse_hpo_terms(row.get(HPO_TERMS_PRESENT_COLUMN), 'yes')
            row[FEATURES_COLUMN] += _parse_hpo_terms(row.get(HPO_TERMS_ABSENT_COLUMN), 'no')
        return row_dicts

    if HPO_TERM_NUMBER_COLUMN in column_map:
        aggregate_rows = defaultdict(list)
        for row in row_dicts:
            if row.get(HPO_TERM_NUMBER_COLUMN):
                aggregate_rows[(row.get(FAMILY_ID_COLUMN), row.get(INDIVIDUAL_ID_COLUMN))].append(
                    _hpo_term_item(row[HPO_TERM_NUMBER_COLUMN], row.get(AFFECTED_COLUMN, 'yes'))
                )
        return [{FAMILY_ID_COLUMN: family_id, INDIVIDUAL_ID_COLUMN: individual_id, FEATURES_COLUMN: features}
                for (family_id, individual_id), features in aggregate_rows.items()]

    raise ValueError('Invalid header, missing hpo terms columns')


def _hpo_term_item(term, observed):
    return {"id": term.strip(), "observed": observed.lower(), "type": "phenotype"}


def _parse_hpo_terms(hpo_term_string, observed):
    if not hpo_term_string:
        return []
    return [_hpo_term_item(hpo_term.strip().split('(')[0], observed) for hpo_term in hpo_term_string.replace(',', ';').split(';')]


def _has_same_features(individual, features):
    present_features = {feature['id'] for feature in features if feature['observed'] == 'yes'}
    absent_features = {feature['id'] for feature in features if feature['observed'] == 'no'}
    return {feature['id'] for feature in individual.features or []} == present_features and \
           {feature['id'] for feature in individual.absent_features or []} == absent_features


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_individual_hpo_terms(request, individual_guid):
    individual = Individual.objects.get(guid=individual_guid)

    project = individual.family.project

    check_permissions(project, request.user, CAN_EDIT)

    features = json.loads(request.body)

    _create_patient_if_missing(project, individual)

    patient_json = _get_patient_data(project, individual)
    patient_json["features"] = features
    patient_json_string = json.dumps(patient_json)

    url = phenotips_patient_url(individual)
    auth_tuple = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    make_phenotips_api_call('PUT', url, data=patient_json_string, auth_tuple=auth_tuple, expected_status_code=204)

    _update_individual_phenotips_data(individual, patient_json)

    return create_json_response({
        individual.guid: _get_json_for_individual(individual, user=request.user, add_hpo_details=True)
    })


def _create_patient_if_missing(project, individual):
    """Create a new PhenoTips patient record with the given patient id.

    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
    Returns:
        True if patient created
    Raises:
        PhenotipsException: if unable to create patient record
    """
    if phenotips_patient_exists(individual):
        return False

    url = '/rest/patients'
    headers = {"Content-Type": "application/json"}
    data = json.dumps({'external_id': individual.guid})
    auth_tuple = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id)

    response_items = make_phenotips_api_call('POST', url, auth_tuple=auth_tuple, http_headers=headers, data=data, expected_status_code=201, parse_json_resonse=False)
    patient_id = response_items['Location'].split('/')[-1]
    logger.info("Created PhenoTips record with patient id {patient_id} and external id {external_id}".format(patient_id=patient_id, external_id=individual.guid))

    username_read_only, _ = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    _add_user_to_patient(username_read_only, patient_id, allow_edit=False)
    logger.info("Added PhenoTips user {username} to {patient_id}".format(username=username_read_only, patient_id=patient_id))

    individual.phenotips_patient_id = patient_id
    individual.phenotips_eid = individual.guid
    individual.save()

    return True


def _set_phenotips_patient_id_if_missing(project, individual):
    if individual.phenotips_patient_id:
        return
    patient_json = _get_patient_data(project, individual)
    individual.phenotips_patient_id = patient_json['id']
    individual.save()


def _get_patient_data(project, individual):
    """Retrieves patient data from PhenoTips and returns a json obj.
    Args:
        project (Model): seqr Project - used to retrieve PhenoTips credentials
        individual (Model): seqr Individual
    Returns:
        dict: json dictionary containing all PhenoTips information for this patient
    Raises:
        PhenotipsException: if unable to retrieve data from PhenoTips
    """
    url = phenotips_patient_url(individual)

    auth_tuple = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id)
    return make_phenotips_api_call('GET', url, auth_tuple=auth_tuple, verbose=False)


def _add_user_to_patient(username, patient_id, allow_edit=True):
    """Grant a PhenoTips user access to the given patient.

    Args:
        username (string): PhenoTips username to grant access to.
        patient_id (string): PhenoTips internal patient id.
    """
    return _update_user_on_patient(patient_id, {
        'collaborator': 'XWiki.' + str(username),
        'accessLevel': 'edit' if allow_edit else 'view',
    })


def _update_user_on_patient(patient_id, data):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data.update({
        'patient': patient_id,
        'xaction': 'update',
        'submit': 'Update'
    })

    url = '/bin/get/PhenoTips/PatientAccessRightsManagement?outputSyntax=plain'
    make_phenotips_api_call(
        'POST',
        url,
        http_headers=headers,
        data=data,
        auth_tuple=(PHENOTIPS_ADMIN_UNAME, PHENOTIPS_ADMIN_PWD),
        expected_status_code=204,
        parse_json_resonse=False,
    )


@login_required
@csrf_exempt
def _phenotips_view_handler(request, project_guid, individual_guid, url_template, permission_level=CAN_VIEW):
    """Requests the PhenoTips PDF for the given patient_id, and forwards PhenoTips' response to the client.

    Args:
        request: Django HTTP request object
        project_guid (string): project GUID for the seqr project containing this individual
        individual_guid (string): individual GUID for the seqr individual corresponding to the desired patient
    """

    project = Project.objects.get(guid=project_guid)
    check_permissions(project, request.user, CAN_VIEW)

    individual = Individual.objects.get(guid=individual_guid)
    _create_patient_if_missing(project, individual)
    _set_phenotips_patient_id_if_missing(project, individual)

    # query string forwarding needed for PedigreeEditor button
    query_string = request.META["QUERY_STRING"]
    url = url_template.format(patient_id=individual.phenotips_patient_id, query_string=query_string)

    auth_tuple = _get_phenotips_username_and_password(request.user, project, permissions_level=permission_level)

    return proxy_request(request, url, headers={}, auth_tuple=auth_tuple, host=PHENOTIPS_SERVER)


@login_required
@csrf_exempt
def phenotips_pdf_handler(request, project_guid, individual_guid):
    """Requests the PhenoTips PDF for the given patient_id, and forwards PhenoTips' response to the client.

    Args:
        request: Django HTTP request object
        project_guid (string): project GUID for the seqr project containing this individual
        individual_guid (string): individual GUID for the seqr individual corresponding to the desired patient
    """
    url_template = "/bin/export/data/{patient_id}?format=pdf&pdfcover=0&pdftoc=0&pdftemplate=PhenoTips.PatientSheetCode"

    return _phenotips_view_handler(request, project_guid, individual_guid, url_template)


@login_required
@csrf_exempt
def phenotips_edit_handler(request, project_guid, individual_guid):
    """Request the PhenoTips Edit page for the given patient_id, and forwards PhenoTips' response to the client.

    Args:
        request: Django HTTP request object
        project_guid (string): project GUID for the seqr project containing this individual
        individual_guid (string): individual GUID for the seqr individual corresponding to the desired patient
    """

    url_template = "/bin/edit/data/{patient_id}?{query_string}"

    return _phenotips_view_handler(request, project_guid, individual_guid, url_template, permission_level=CAN_EDIT)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def proxy_to_phenotips(request):
    """This django view accepts GET and POST requests and forwards them to PhenoTips"""

    url = request.get_full_path()
    if any([k for k in DO_NOT_PROXY_URL_KEYWORDS if k.lower() in url.lower()]):
        logger.warn("Blocked proxy url: " + str(url))
        return HttpResponse(status=204)
    logger.info("Proxying url: " + str(url))

    # Some PhenoTips endpoints that use HTTP redirects lose the phenotips JSESSION auth cookie
    # along the way, and don't proxy correctly. Using a Session object as below to store the cookies
    # provides a work-around.
    phenotips_session = requests.Session()
    for key, value in request.COOKIES.items():
        phenotips_session.cookies.set(key, value)

    http_response = proxy_request(request, url, data=request.body, session=phenotips_session,
                                  host=PHENOTIPS_SERVER, filter_request_headers=True)

    # if this is the 'Quick Save' request, also save a copy of phenotips data in the seqr SQL db.
    match = re.match(PHENOTIPS_QUICK_SAVE_URL_REGEX, url)
    if match:
        _handle_phenotips_save_request(request, patient_id=match.group(1))

    return http_response


def _handle_phenotips_save_request(request, patient_id):
    """Update the seqr SQL database record for this patient with the just-saved phenotype data."""

    url = '/rest/patients/%s' % patient_id

    cookie_header = request.META.get('HTTP_COOKIE')
    http_headers = {'Cookie': cookie_header} if cookie_header else {}
    response = proxy_request(request, url, headers=http_headers, method='GET', scheme='http', host=PHENOTIPS_SERVER)
    if response.status_code != 200:
        logger.error("ERROR: unable to retrieve patient json. %s %s %s" % (
            url, response.status_code, response.reason_phrase))
        return

    patient_json = json.loads(response.content)

    try:
        if patient_json.get('external_id'):
            # prefer to use the external id for legacy reasons: some projects shared phenotips
            # records by sharing the phenotips internal id, so in rare cases, the
            # Individual.objects.get(phenotips_patient_id=...) may match multiple Individual records
            individual = Individual.objects.get(phenotips_eid=patient_json['external_id'])
        else:
            individual = Individual.objects.get(phenotips_patient_id=patient_json['id'])

    except ObjectDoesNotExist as e:
        logger.error("ERROR: PhenoTips patient id %s not found in seqr Individuals." % patient_json['id'])
        return

    _update_individual_phenotips_data(individual, patient_json)


def _update_individual_phenotips_data(individual, patient_json):
    """Process and store the given patient_json in the given Individual model.

    Args:
        individual (Individual): Django Individual model
        patient_json (json): json dict representing the patient record in PhenoTips
    """

    individual.phenotips_data = json.dumps(patient_json)
    individual.phenotips_patient_id = patient_json['id']  # phenotips internal id
    individual.phenotips_eid = patient_json.get('external_id')  # phenotips external id
    _update_individual_phenotips_fields(individual, patient_json)
    individual.save()


def _update_individual_phenotips_fields(indiv, phenotips_json):
    if phenotips_json.get('date_of_birth'):
        indiv.birth_year = datetime.strptime(phenotips_json['date_of_birth'], '%Y-%m-%d').year
    if phenotips_json.get('life_status') == 'deceased':
        indiv.death_year = datetime.strptime(phenotips_json['date_of_death'], '%Y-%m-%d').year \
            if phenotips_json.get('date_of_death') else 0

    if phenotips_json.get('global_age_of_onset'):
        onset_label = phenotips_json['global_age_of_onset'][0]['label']
        indiv.onset_age = Individual.ONSET_AGE_REVERSE_LOOKUP[onset_label]
    if phenotips_json.get('global_mode_of_inheritance'):
        indiv.expected_inheritance = [
            Individual.INHERITANCE_REVERSE_LOOKUP[i['label']] for i in phenotips_json['global_mode_of_inheritance']]

    if phenotips_json['ethnicity']['maternal_ethnicity']:
        indiv.maternal_ethnicity = phenotips_json['ethnicity']['maternal_ethnicity']
    if phenotips_json['ethnicity']['paternal_ethnicity']:
        indiv.paternal_ethnicity = phenotips_json['ethnicity']['paternal_ethnicity']

    family_history = phenotips_json.get('family_history') or {}
    if family_history.get('consanguinity') is not None:
        indiv.cosanguinity = family_history['consanguinity']
    if family_history.get('affectedRelatives') is not None:
        indiv.affected_relatives = family_history['affectedRelatives']

    present_features = []
    absent_features = []
    nonstandard_features = []
    absent_nonstandard_features = []
    for feature in phenotips_json.get('features') or []:
        feature_list = present_features if feature['observed'] == 'yes' else absent_features
        feature_list.append(_get_parsed_feature(feature))
    for feature in phenotips_json.get('nonstandard_features') or []:
        feature_list = nonstandard_features if feature['observed'] == 'yes' else absent_nonstandard_features
        feature_list.append(
            _get_parsed_feature(feature, id=feature['label'], additional_fields=['categories']))
    if present_features:
        indiv.features = present_features
    if absent_features:
        indiv.absent_features = absent_features
    if nonstandard_features:
        indiv.nonstandard_features = nonstandard_features
    if absent_nonstandard_features:
        indiv.absent_nonstandard_features = absent_nonstandard_features

    if phenotips_json.get('disorders'):
        mim_ids = map(lambda d: int(d['id'].lstrip('MIM:')), phenotips_json['disorders'])
        indiv.disorders = mim_ids

    if phenotips_json.get('genes'):
        indiv.candidate_genes = phenotips_json['genes']
    if phenotips_json.get('rejectedGenes'):
        indiv.rejected_genes = phenotips_json['rejectedGenes']

    prenatal = phenotips_json['prenatal_perinatal_history']
    for field in [
        'assistedReproduction_fertilityMeds', 'assistedReproduction_iui', 'ivf', 'icsi',
        'assistedReproduction_surrogacy', 'assistedReproduction_donoregg', 'assistedReproduction_donorsperm',
    ]:
        if prenatal.get(field) is not None:
            indiv_field = 'ar_{}'.format(_to_snake_case(field.replace('assistedReproduction_', '')))
            setattr(indiv, indiv_field, prenatal[field])


def _get_parsed_feature(feature, id=None, additional_fields=None):
    optional_fields = ['notes', 'qualifiers']
    if additional_fields:
        optional_fields += additional_fields
    if not id:
        id = feature['id']
    feature_json = {'id': id}

    for field in optional_fields:
        if field in feature:
            feature_json[field] = feature[field]

    return feature_json


def _get_phenotips_username_and_password(user, project, permissions_level):
    """Checks if user has permission to access the given project, and raises an exception if not.

    Args:
        user (User): the django user object
        project(Model): Project model
        permissions_level (string): 'edit' or 'view'
    Raises:
        PermissionDenied: if user doesn't have permission to access this project.
    Returns:
        2-tuple: PhenoTips username, password that can be used to access patients in this project.
    """
    if permissions_level == CAN_EDIT:
        uname, pwd = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    elif permissions_level == CAN_VIEW:
        uname, pwd = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    else:
        raise ValueError("Unexpected auth_permissions value: %s" % permissions_level)

    auth_tuple = (uname, pwd)

    return auth_tuple
