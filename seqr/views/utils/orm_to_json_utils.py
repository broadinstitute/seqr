"""
Utility functions for converting Django ORM object to JSON
"""

import json
import logging
import os

from seqr.models import CAN_EDIT
from seqr.views.utils.json_utils import _to_camel_case
from family_info_utils import retrieve_family_analysed_by
logger = logging.getLogger(__name__)


def _get_json_for_user(user):
    """Returns JSON representation of the given User object

    Args:
        user (object): Django user model

    Returns:
        dict: json object
    """

    if hasattr(user, '_wrapped'):
        user = user._wrapped   # Django request.user actually stores the Django User objects in a ._wrapped attribute

    json_obj = {
        key: getattr(user, key)
        for key in ['id', 'username', 'email', 'first_name', 'last_name', 'last_login', 'is_staff', 'is_active', 'date_joined']
    }

    return json_obj


PROJECT_FIELDS = [
    'name', 'description', 'created_date', 'last_modified_date', 'is_phenotips_enabled', 'phenotips_user_id',
    'deprecated_project_id', 'deprecated_last_accessed_date', 'is_mme_enabled', 'mme_primary_data_owner',
]


def _get_json_for_project(project, user):
    """Returns JSON representation of the given Project.

    Args:
        project (object): django model for the project
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    result = {
        'projectGuid': project.guid,
        'projectCategoryGuids': [c.guid for c in project.projectcategory_set.all()],
        'canEdit': user.is_staff or user.has_perm(CAN_EDIT, project),
    }

    result.update({_to_camel_case(field): getattr(project, field) for field in PROJECT_FIELDS})

    if user.is_staff:
        result.update({
            'deprecatedLastAccessedDate': project.deprecated_last_accessed_date
        })

    return result


def _get_json_for_family(family, user=None, add_individual_guids_field=False):
    """Returns a JSON representation of the given Family.

    Args:
        family (object): django model representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
    Returns:
        dict: json object
    """

    result = {
        'familyGuid':      family.guid,
        'familyId':        family.family_id,
        'displayName':     family.display_name,
        'description':     family.description,
        'pedigreeImage':   os.path.join("/media/", family.pedigree_image.url) if family.pedigree_image and family.pedigree_image.url else None,
        'analysisNotes':   family.analysis_notes,
        'analysisSummary': family.analysis_summary,
        'causalInheritanceMode': family.causal_inheritance_mode,
        'analysisStatus':  family.analysis_status,
        'analysedBy': retrieve_family_analysed_by(family.id),
    }

    if user and user.is_staff:
        result.update({
            'internalAnalysisStatus': family.internal_analysis_status,
            'internalCaseReviewNotes': family.internal_case_review_notes,
            'internalCaseReviewSummary': family.internal_case_review_summary,
        })

    if add_individual_guids_field:
        result['individualGuids'] = [i.guid for i in family.individual_set.all()]

    return result


def _get_json_for_individual(individual, user=None):
    """Returns a JSON representation of the given Individual.

    Args:
        individual (object): django model for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """

    case_review_status_last_modified_by = None
    if individual.case_review_status_last_modified_by:
        u = individual.case_review_status_last_modified_by
        case_review_status_last_modified_by = u.email or u.username

    try:
        phenotips_json = None
        if individual.phenotips_data:
            phenotips_json = json.loads(individual.phenotips_data)
    except Exception as e:
        logger.error("Unable to parse %s individual.phenotips_data: '%s': %s",
            individual.individual_id, individual.phenotips_data, e)

    return {
        'individualGuid': individual.guid,
        'individualId': individual.individual_id,
        'paternalId': individual.paternal_id,
        'maternalId': individual.maternal_id,
        'sex': individual.sex,
        'affected': individual.affected,
        'displayName': individual.display_name,
        'notes': individual.notes or '',
        'caseReviewStatus': individual.case_review_status,
        'caseReviewStatusAcceptedFor': individual.case_review_status_accepted_for,
        'caseReviewStatusLastModifiedDate': individual.case_review_status_last_modified_date,
        'caseReviewStatusLastModifiedBy': case_review_status_last_modified_by,
        'caseReviewDiscussion': individual.case_review_discussion,
        #'phenotipsPatientExternalId': individual.phenotips_eid,
        'phenotipsPatientId': individual.phenotips_patient_id,
        'phenotipsData': phenotips_json,
        'createdDate': individual.created_date,
        'lastModifiedDate': individual.last_modified_date,
    }


def _get_json_for_sample(sample, user=None):
    """Returns a JSON representation of the given Sample.

    Args:
        sample (object): django model for the Sample.
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    return {
        'sampleGuid': sample.guid,
        'createdDate': sample.created_date,
        'sampleType': sample.sample_type,
        'sampleId': sample.sample_id,
        'sampleStatus': sample.sample_status,
    }


def _get_json_for_dataset(dataset, user=None):
    """Returns a JSON representation of the given Dataset.

    Args:
        dataset (object): django model for the Dataset.
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    return {
        'datasetGuid': dataset.guid,
        'createdDate': dataset.created_date,
        'analysisType': dataset.analysis_type,
        'isLoaded': dataset.is_loaded,
        'loadedDate': dataset.loaded_date,
        'sourceFilePath': dataset.source_file_path,
    }

