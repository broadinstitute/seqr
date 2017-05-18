"""
Utility functions for converting Django ORM object to JSON
"""

import json

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
        key: value
        for key, value in user.__dict__.items()
        if not key.startswith("_") and key != "password"
    }

    return json_obj


def _get_json_for_project(project, user=None):
    """Returns JSON representation of the given Project.

    Args:
        project (object): django model for the project
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    result = {
        'projectGuid': project.guid,
        'name': project.name,
        'description': project.description,
        'createdDate': project.created_date,
        'lastModifiedDate': project.last_modified_date,
        'deprecatedProjectId': project.deprecated_project_id,
        'projectCategoryGuids': [c.guid for c in project.projectcategory_set.all()],
        'isPhenotipsEnabled': project.is_phenotips_enabled,
        'phenotipsUserId': project.phenotips_user_id,
        'isMmeEnabled': project.is_mme_enabled,
        'mmePrimaryDataOwner': project.mme_primary_data_owner,
    }

    if user and user.is_staff:
        result.update({
            'deprecatedLastAccessedDate': project.deprecated_last_accessed_date
        })

    return result


def _get_json_for_family(family, user=None):
    """Returns a JSON representation of the given Family.

    Args:
        family (object): django model representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """

    result = {
        'familyGuid':      family.guid,
        'familyId':        family.family_id,
        'displayName':     family.display_name,
        'description':     family.description,
        'pedigreeImage':   family.pedigree_image.url if family.pedigree_image else None,
        'analysisNotes':   family.analysis_notes,
        'analysisSummary': family.analysis_summary,
        'causalInheritanceMode': family.causal_inheritance_mode,
        'analysisStatus':  family.analysis_status,

    }

    if user and user.is_staff:
        result.update({
            'internalAnalysisStatus': family.internal_analysis_status,
            'internalCaseReviewNotes': family.internal_case_review_notes,
            'internalCaseReviewSummary': family.internal_case_review_summary,
        })

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

    return {
        'individualGuid': individual.guid,
        'individualId': individual.individual_id,
        'paternalId': individual.paternal_id,
        'maternalId': individual.maternal_id,
        'sex': individual.sex,
        'affected': individual.affected,
        'displayName': individual.display_name,
        'notes': individual.notes,
        'caseReviewStatus': individual.case_review_status,
        'caseReviewStatusAcceptedFor': individual.case_review_status_accepted_for,
        'caseReviewStatusLastModifiedBy': case_review_status_last_modified_by,
        'caseReviewStatusLastModifiedDate': individual.case_review_status_last_modified_date,
        'caseReviewRequestedInfo': individual.case_review_requested_info,
        'phenotipsPatientId': individual.phenotips_patient_id,
        'phenotipsData': json.loads(individual.phenotips_data) if individual.phenotips_data else None,
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
        'sampleId': sample.sample_id,
        'sampleStatus': sample.sample_status,
        'individualId': sample.individual_id,
        'isLoaded': sample.is_loaded,
        'loadedDate': sample.loaded_date,
        'createdDate': sample.created_date,
        'lastModifiedDate': sample.last_modified_date,
        'sourceFilePath': sample.source_file_path,

    }


def _get_json_for_sample_batch(sample_batch, user=None):
    """Returns a JSON representation of the given SampleBatch.

    Args:
        sample_batch (object): django model for the SampleBatch.
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    return {
        'sampleBatchGuid': sample_batch.guid,
        'name': sample_batch.name,
        'description': sample_batch.description,
        'sampleType': sample_batch.sample_type,
        'genomeBuildId': sample_batch.genome_build_id,
    }

