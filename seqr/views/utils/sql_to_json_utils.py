import os

"""
Utility functions for converting raw SQL records to JSON. The SQL records must
be passed in as python dicts, with keys that are snake_case and where each key is the
SQL column name, prefixed by the table name. For example, keys should look like:

    individual_guid, family_display_name, family_analysis_summary, etc.

This module is complementary to json_from_orm_utils.py and the two should return identical JSON
for a given record regardless of whether the record was retrieved using the ORM or through raw SQL.

One difference from the ORM-based functions is that the ORM retrieves all columns in a record,
while these raw-record-based functions allow querying for a subset of columns, and creating JSON
objects that just contain keys/values for the queried columns.
"""
import os

def _get_json_for_family_fields(family_record, user=None):
    """Returns a JSON representation of the given family record.

    Args:
        family_record (dict): SQL record
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """

    family_keys = [
        ('family_guid', 'familyGuid'),
        ('family_id',   'familyId'),
        ('family_display_name', 'displayName'),
        ('family_description', 'description'),
        ('family_pedigree_image', 'pedigreeImage'),
        ('family_analysis_notes', 'analysisNotes'),
        ('family_analysis_summary', 'analysisSummary'),
        ('family_causal_inheritance_mode', 'causalInheritanceMode'),
        ('family_analysis_status', 'analysisStatus'),
    ]

    if user and user.is_staff:
        family_keys += [
            ('family_internal_analysis_status', 'internalAnalysisStatus'),
            ('family_internal_case_review_notes', 'internalCaseReviewNotes'),
            ('family_internal_case_review_summary', 'internalCaseReviewSummary')
        ]

    result = {json_key: family_record[key] for key, json_key in family_keys if key in family_record}

    # fix pedigree image url
    if result.get('pedigreeImage', None):
        result['pedigreeImage'] = os.path.join('/media', result['pedigreeImage'])

    return result


def _get_json_for_individual_fields(individual_record, user=None):
    """Returns a JSON representation of the given individual.

    Args:
        individual_record (dict): SQL record
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """

    individual_keys = [
        ('individual_guid', 'individualGuid'),
        ('individual_id', 'individualId'),
        ('individual_maternal_id', 'maternalId'),
        ('individual_paternal_id', 'paternalId'),
        ('individual_sex', 'sex'),
        ('individual_affected', 'affected'),
        ('individual_display_name', 'displayName'),
        ('individual_notes', 'notes'),
        ('individual_case_review_status', 'caseReviewStatus'),
        ('individual_case_review_status_accepted_for', 'caseReviewStatusAcceptedFor'),
        ('individual_case_review_status_last_modified_by', 'caseReviewStatusLastModifiedBy'),
        ('individual_case_review_status_last_modified_date', 'caseReviewStatusLastModifiedDate'),
        ('individual_case_review_discussion', 'caseReviewDiscussion'),
        #('individual_phenotips_eid', 'phenotipsPatientExternalId'),
        ('individual_phenotips_patient_id', 'phenotipsPatientId'),
        ('individual_phenotips_data', 'phenotipsData'),
        ('individual_created_date', 'createdDate'),
        ('individual_last_modified_date', 'lastModifiedDate')
    ]

    result = {json_key: individual_record[key] for key, json_key in individual_keys if key in individual_record}

    return result


def _get_json_for_sample_fields(sample_record, user=None):
    """Returns a JSON representation of the given sample.

    Args:
        sample_record (dict): SQL record
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    sample_keys = [
        ('sample_guid', 'sampleGuid'),
        ('sample_created_date', 'createdDate'),
        ('sample_type',   'sampleType'),
        ('sample_id',     'sampleId'),
        ('sample_status', 'sampleStatus'),
    ]

    result = {json_key: sample_record[key] for key, json_key in sample_keys if key in sample_record}

    return result


def _get_json_for_dataset_fields(dataset_record, user=None):
    """Returns a JSON representation of the given Dataset.

    Args:
        dataset_record (dict): SQL record
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    dataset_keys = [
        ('sample_type',               'sampleType'),   # sample type isn't strictly a dataset field, but it should have a single value per dataset, and is useful
        ('dataset_guid',              'datasetGuid'),
        ('dataset_created_date',      'createdDate'),
        ('dataset_analysis_type',     'analysisType'),
        ('dataset_is_loaded',         'isLoaded'),
        ('dataset_loaded_date',       'loadedDate'),
        ('dataset_source_file_path',  'sourceFilePath'),
    ]

    result = {json_key: dataset_record[key] for key, json_key in dataset_keys if key in dataset_record}

    return result
