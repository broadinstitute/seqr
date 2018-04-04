"""
Utility functions for converting Django ORM object to JSON
"""

import json
import logging
import os
from django.db.models.fields.files import ImageFieldFile

from seqr.models import CAN_EDIT
from seqr.views.utils.json_utils import _to_camel_case
from family_info_utils import retrieve_family_analysed_by
logger = logging.getLogger(__name__)


def _get_json_for_record(record, fields, processed_fields={}, get_record_field=None, get_parent_guid=None):
    if not get_record_field:
        def get_record_field(record, field):
            return getattr(record, field)

    result = {_to_camel_case(field): get_record_field(record, field) for field in fields}
    result.update({field: process(result.pop(pop_field)) for field, (pop_field, process) in processed_fields.items()})
    result.update(get_parent_guid(record))
    return result


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

    result = _get_json_for_record(project, PROJECT_FIELDS, get_parent_guid=lambda project: {'projectGuid': project.guid})
    result.update({
        'projectCategoryGuids': [c.guid for c in project.projectcategory_set.all()],
        'canEdit': user.is_staff or user.has_perm(CAN_EDIT, project),
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

    result = _get_json_for_family_helper(family, user)

    if add_individual_guids_field:
        result['individualGuids'] = [i.guid for i in family.individual_set.all()]

    return result


def _get_json_for_family_helper(family, user, get_record_field=None, get_project_guid=None):
    def _get_pedigree_image_url(pedigree_image):
        if isinstance(pedigree_image, ImageFieldFile) and pedigree_image:
            pedigree_image = pedigree_image.url
        return os.path.join("/media/", pedigree_image) if pedigree_image else None

    fields = [
        'guid', 'id', 'family_id', 'display_name', 'description', 'analysis_notes', 'analysis_summary',
        'causal_inheritance_mode', 'analysis_status', 'pedigree_image',
    ]
    if user and user.is_staff:
        fields += ['internal_analysis_status', 'internal_case_review_notes', 'internal_case_review_summary']

    processed_fields = {
        'familyGuid': ('guid', lambda x: x),
        'analysedBy': ('id', retrieve_family_analysed_by),
        'pedigreeImage': ('pedigreeImage', _get_pedigree_image_url),
    }

    return _get_json_for_record(family, fields, processed_fields, get_record_field,
                                get_parent_guid=lambda family: {
                                    'projectGuid': get_project_guid(family) if get_project_guid else family.project.guid
                                })


def _get_json_for_individual(individual):
    """Returns a JSON representation of the given Individual.

    Args:
        individual (object): django model for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """

    return _get_json_for_individual_helper(individual)


def _get_json_for_individual_helper(individual, get_record_field=None, get_parent_guid=None):
    def _get_case_review_status_modified_by(modified_by):
        return modified_by.email or modified_by.username if hasattr(modified_by, 'email') else modified_by

    def _load_phenotips_data(phenotips_data):
        phenotips_json = None
        if phenotips_data:
            try:
                phenotips_json = json.loads(individual.phenotips_data)
            except Exception as e:
                logger.error("Couldn't parse phenotips: %s", e)
        return phenotips_json

    fields = [
        'guid', 'individual_id', 'paternal_id', 'maternal_id', 'sex', 'affected', 'display_name', 'notes',
        'case_review_status', 'case_review_status_accepted_for', 'case_review_status_last_modified_date',
        'case_review_status_last_modified_by', 'case_review_discussion', 'phenotips_patient_id', 'phenotips_data',
        'created_date', 'last_modified_date'
    ]
    processed_fields = {
        'individualGuid': ('guid', lambda x: x),
        'caseReviewStatusLastModifiedBy': ('caseReviewStatusLastModifiedBy', _get_case_review_status_modified_by),
        'phenotipsData': ('phenotipsData', _load_phenotips_data)
    }

    if not get_parent_guid:
        def get_parent_guid(individual):
            return {
                'projectGuid': individual.family.project.guid,
                'familyGuid': individual.family.guid
            }

    return _get_json_for_record(individual, fields, processed_fields, get_record_field, get_parent_guid)


def _get_json_for_sample(sample):
    """Returns a JSON representation of the given Sample.

    Args:
        sample (object): django model for the Sample.
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    return _get_json_for_sample_helper(sample)


def _get_json_for_sample_helper(sample, get_record_field=None, get_individual_guid=None):
    fields = [
        'guid', 'created_date', 'sample_type', 'sample_id', 'sample_status',
    ]
    processed_fields = {
        'sampleGuid': ('guid', lambda x: x),
    }

    return _get_json_for_record(sample, fields, processed_fields, get_record_field,
                                get_parent_guid=lambda sample: {
                                    'individualId': get_individual_guid(sample) if get_individual_guid else sample.individual.guid
                                })


def _get_json_for_dataset(dataset):
    """Returns a JSON representation of the given Dataset.

    Args:
        dataset (object): django model for the Dataset.
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    return _get_json_for_dataset_helper(dataset)


def _get_json_for_dataset_helper(sample, get_record_field=None, get_sample_type=None):
    fields = [
        'guid', 'created_date', 'analysis_type', 'is_loaded', 'loaded_date', 'source_file_path',
    ]
    processed_fields = {
        'datasetGuid': ('guid', lambda x: x),
    }

    return _get_json_for_record(sample, fields, processed_fields, get_record_field,
                                get_parent_guid=lambda dataset: {
                                    'sampleType': get_sample_type(dataset) if get_sample_type else dataset.sample_set.first().sample_type
                                })