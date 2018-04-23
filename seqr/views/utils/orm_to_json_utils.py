"""
Utility functions for converting Django ORM object to JSON
"""

import json
import logging
import os
from django.db.models import Model
from django.db.models.fields.files import ImageFieldFile

from seqr.models import CAN_EDIT
from seqr.views.utils.json_utils import _to_camel_case
from family_info_utils import retrieve_family_analysed_by
logger = logging.getLogger(__name__)


def _record_to_dict(record, fields, prefix):
    converted = False
    if isinstance(record, Model):
        record = {'%s_%s' % (prefix, field): getattr(record, field) for field in fields}
        converted = True
    return record, converted


def _get_json_for_record(record, fields, prefix):
    return {_to_camel_case(field): record.get('%s_%s' % (prefix, field)) for field in fields}


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
    'deprecated_project_id', 'deprecated_last_accessed_date', 'is_mme_enabled', 'mme_primary_data_owner', 'guid'
]


def _get_json_for_project(project, user):
    """Returns JSON representation of the given Project.

    Args:
        project (object): dictionary or django model for the project
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    project_dict, converted = _record_to_dict(project, PROJECT_FIELDS, 'project')
    result = _get_json_for_record(project_dict, PROJECT_FIELDS, 'project')
    result.update({
        'projectGuid': result.pop('guid'),
        'projectCategoryGuids': [c.guid for c in project.projectcategory_set.all()] if converted else [],
        'canEdit': user.is_staff or user.has_perm(CAN_EDIT, project),
    })
    return result


def _get_json_for_family(family, user, add_individual_guids_field=False):
    """Returns a JSON representation of the given Family.

    Args:
        family (object): dictionary or django model representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
    Returns:
        dict: json object
    """

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

    family_dict, converted = _record_to_dict(family, fields, 'family')
    if converted:
        family_dict['project_guid'] = family.project.guid

    result = _get_json_for_record(family_dict, fields, 'family')
    result.update({
        'projectGuid': family_dict['project_guid'],
        'familyGuid': result.pop('guid'),
        'analysedBy': retrieve_family_analysed_by(result.pop('id')),
        'pedigreeImage': _get_pedigree_image_url(result['pedigreeImage']),
    })

    if add_individual_guids_field:
        result['individualGuids'] = [i.guid for i in family.individual_set.all()]

    return result


def _get_json_for_individual(individual):
    """Returns a JSON representation of the given Individual.

    Args:
        individual (object): dictionary or django model for the individual.
    Returns:
        dict: json object
    """

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

    individual_dict, converted = _record_to_dict(individual, fields, 'individual')
    if converted:
        individual_dict.update({
            'project_guid': individual.family.project.guid,
            'family_guid': individual.family.guid,
        })

    result = _get_json_for_record(individual_dict, fields, 'individual')
    result.update({
        'projectGuid': individual_dict['project_guid'],
        'familyGuid': individual_dict['family_guid'],
        'individualGuid': result.pop('guid'),
        'caseReviewStatusLastModifiedBy': _get_case_review_status_modified_by(result['caseReviewStatusLastModifiedBy']),
        'phenotipsData': _load_phenotips_data(result['phenotipsData'])
    })
    return result


def _get_json_for_sample(sample):
    """Returns a JSON representation of the given Sample.

    Args:
        sample (object): dictionary or django model for the Sample.
    Returns:
        dict: json object
    """

    fields = [
        'guid', 'created_date', 'sample_type', 'sample_id', 'sample_status',
    ]

    sample_dict, converted = _record_to_dict(sample, fields, 'sample')
    if converted:
        sample_dict.update({
            'project_guid': sample.individual.family.project.guid,
            'individual_guid': sample.individual.guid,
        })

    result = _get_json_for_record(sample_dict, fields, 'sample')
    result.update({
        'projectGuid': sample_dict['project_guid'],
        'individualGuid': sample_dict['individual_guid'],
        'sampleGuid': result.pop('guid'),
    })
    return result


def _get_json_for_dataset(dataset):
    """Returns a JSON representation of the given Dataset.

    Args:
        dataset (object): dictionary or django model for the Dataset.
    Returns:
        dict: json object
    """

    fields = [
        'guid', 'created_date', 'analysis_type', 'is_loaded', 'loaded_date', 'source_file_path',
    ]

    dataset_dict, converted = _record_to_dict(dataset, fields, 'dataset')
    if converted:
        dataset_dict.update({
            'project_guid': dataset.sample_set.first().individual.family.project.guid,
            'sample_sample_type': dataset.sample_set.first().sample_type,
        })

    result = _get_json_for_record(dataset_dict, fields, 'dataset')
    result.update({
        'projectGuid': dataset['project_guid'],
        'sampleType': dataset['sample_sample_type'],
        'datasetGuid': result.pop('guid'),
    })
    return result
