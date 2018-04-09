from seqr.views.utils.orm_to_json_utils import _get_json_for_family_helper, _get_json_for_individual_helper, \
    _get_json_for_sample_helper, _get_json_for_dataset_helper

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


def _get_json_for_family_fields(family_record, user=None):
    """Returns a JSON representation of the given family record.

    Args:
        family_record (dict): SQL record
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """

    return _get_json_for_family_helper(family_record, user,
                                       get_record_field=lambda record, field: record.get('family_' + field),
                                       get_project_guid=lambda record: record['project_guid'])


def _get_json_for_individual_fields(individual_record):
    """Returns a JSON representation of the given individual.

    Args:
        individual_record (dict): SQL record
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """

    return _get_json_for_individual_helper(
        individual_record, get_record_field=lambda record, field: record.get('individual_' + field),
        get_parent_guid=lambda record: {
                'projectGuid': record['project_guid'],
                'familyGuid': record['family_guid'],
            })


def _get_json_for_sample_fields(sample_record):
    """Returns a JSON representation of the given sample.

    Args:
        sample_record (dict): SQL record
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    return _get_json_for_sample_helper(
        sample_record, get_record_field=lambda record, field: record.get('sample_' + field),
        get_parent_guid=lambda record: {
            'projectGuid': record['project_guid'],
            'individualGuid': record['individual_guid'],
        })


def _get_json_for_dataset_fields(dataset_record):
    """Returns a JSON representation of the given Dataset.

    Args:
        dataset_record (dict): SQL record
        user (object): Django User object for determining whether to include any restricted/internal-only fields
    Returns:
        dict: json object
    """

    return _get_json_for_dataset_helper(
        dataset_record, get_record_field=lambda record, field: record.get('dataset_' + field),
        get_parent_guid=lambda record:  {
            'projectGuid': record['project_guid'],
            'sampleType': record['sample_sample_type'],
        })
