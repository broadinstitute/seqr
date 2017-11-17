"""
APIs used to retrieve, update, and create Individual records
"""

import gzip
import hashlib
import json
import logging
import os
import tempfile

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Individual, Family, CAN_EDIT
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.pedigree_image_api import update_pedigree_image
from seqr.views.apis.phenotips_api import create_patient, set_patient_hpo_terms
from seqr.views.utils.export_table_utils import _convert_html_to_plain_text, export_table
from seqr.views.utils.json_to_orm_utils import update_individual_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table
from seqr.views.utils.request_utils import _get_project_and_check_permissions

from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual

logger = logging.getLogger(__name__)

_SEX_TO_EXPORT_VALUE = dict(Individual.SEX_LOOKUP)
_SEX_TO_EXPORT_VALUE['U'] = ''

_AFFECTED_TO_EXPORT_VALUE = dict(Individual.AFFECTED_STATUS_LOOKUP)
_AFFECTED_TO_EXPORT_VALUE['U'] = ''


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_individual_field_handler(request, individual_guid, field_name):
    """Updates an Individual record.

    Args:
        individual_guid (string): GUID of the individual.
        field_name (string): Name of Individual record field to update (eg. "affected").
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

    # parse file
    stream = request.FILES.values()[0]
    filename = stream._name
    #file_size = stream._size
    #content_type = stream.content_type
    #content_type_extra = stream.content_type_extra
    #for chunk in value.chunks():
    #   destination.write(chunk)

    json_records, errors, warnings = parse_pedigree_table(filename, stream)

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
        json_records = json.load(f)

    add_or_update_individuals_and_families(project, individual_records=json_records)

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

            logger.info("Created family: %s" % (family,))

        individual, created = Individual.objects.get_or_create(family=family, individual_id=record['individualId'])

        update_individual_from_json(individual, record, allow_unknown_keys=True)

        # apply additional json fields which don't directly map to Individual model fields
        individual.phenotips_eid = individual.guid  # use this instead of individual_id to avoid chance of collisions

        if created:
            # create new PhenoTips patient record
            patient_record = create_patient(project, individual.phenotips_eid)
            individual.phenotips_patient_id = patient_record['id']
            individual.case_review_status = 'I'
            
            logger.info("Created PhenoTips record with patient id %s and external id %s" % (
                str(individual.phenotips_patient_id), str(individual.phenotips_eid)))

        if record.get('hpoTerms'):
            # update phenotips hpo ids
            logger.info("Setting PhenoTips HPO Terms to: %s" % (record.get('hpoTerms'),))
            set_patient_hpo_terms(project, individual.phenotips_eid, record.get('hpoTerms'), is_external_id=True)

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
        logger.info("Created xbrowse family: %s" % (base_family,))

    base_individual, created = BaseIndividual.objects.get_or_create(project=base_project, family=base_family, indiv_id=individual.individual_id)
    if created:
        logger.info("Created xbrowse individual: %s" % (base_individual,))

    base_individual.created_date = individual.created_date
    base_individual.maternal_id = individual.maternal_id or ''
    base_individual.paternal_id = individual.paternal_id or ''
    base_individual.gender = individual.sex
    base_individual.affected = individual.affected
    base_individual.nickname = individual.display_name
    base_individual.case_review_status = individual.case_review_status

    if created or not base_individual.phenotips_id:
        base_individual.phenotips_id = individual.phenotips_eid

    base_individual.phenotips_data = individual.phenotips_data
    base_individual.save()


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
            _SEX_TO_EXPORT_VALUE.get(i.sex),
            _AFFECTED_TO_EXPORT_VALUE.get(i.affected),
            _convert_html_to_plain_text(i.notes),
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


def _parse_phenotips_data(phenotips_json):
    """Takes the phenotips_json dictionary for a give Individual and converts it to a flat
    dictionary of key-value pairs for populating phenotips-related columns in a table.

    Args:
        phenotips_json (dict): The PhenoTips json from an Individual

    Returns:
        Dictionary of key-value pairs
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
        result['candidate_genes'] =  ', '.join(result['candidate_genes'])

    if phenotips_json.get('ethnicity'):
        ethnicity = phenotips_json.get('ethnicity')
        if ethnicity.get('paternal_ethnicity'):
            result['paternal_ancestry'] = ", ".join(ethnicity.get('paternal_ethnicity'))

        if ethnicity.get('maternal_ethnicity'):
            result['maternal_ancestry'] = ", ".join(ethnicity.get('maternal_ethnicity'))

    if phenotips_json.get('global_age_of_onset'):
        result['age_of_onset'] = ", ".join((a.get('label') for a in phenotips_json.get('global_age_of_onset') if a))

    return result
