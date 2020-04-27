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

import json
import logging
import re
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from reference_data.models import HumanPhenotypeOntology
from seqr.models import CAN_EDIT, Individual
from seqr.views.utils.file_utils import save_uploaded_file
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual
from seqr.views.utils.permissions_utils import check_permissions, get_project_and_check_permissions
from settings import API_LOGIN_REQUIRED_URL

logger = logging.getLogger(__name__)

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

    present_features = []
    absent_features = []
    for feature in features:
        feature_list = present_features if feature['observed'] == 'yes' else absent_features
        feature_list.append({'id': feature['id']})

    individual.features = present_features
    individual.absent_features = absent_features

    individual.save()

    return create_json_response({
        individual.guid: _get_json_for_individual(individual, user=request.user, add_hpo_details=True)
    })
