"""
APIs for retrieving, updating, creating, and deleting Individual records
"""

import logging
from collections import defaultdict

from seqr.models import Sample, IgvSample, Individual, Family
from seqr.views.utils.pedigree_image_utils import update_pedigree_images
from seqr.views.utils.json_to_orm_utils import update_individual_from_json, update_family_from_json, \
    create_model_from_json
from seqr.views.utils.pedigree_info_utils import JsonConstants

logger = logging.getLogger(__name__)

_SEX_TO_EXPORTED_VALUE = dict(Individual.SEX_LOOKUP)
_SEX_TO_EXPORTED_VALUE['U'] = ''

__AFFECTED_TO_EXPORTED_VALUE = dict(Individual.AFFECTED_STATUS_LOOKUP)
__AFFECTED_TO_EXPORTED_VALUE['U'] = ''


def _get_record_family_id(record):
    # family id will be in different places in the json depending on whether it comes from a flat uploaded file or from the nested individual object
    return record.get(JsonConstants.FAMILY_ID_COLUMN) or record.get('family', {})['familyId']


def _get_record_individual_id(record):
    return record.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN) or record[JsonConstants.INDIVIDUAL_ID_COLUMN]


def add_or_update_individuals_and_families(project, individual_records, user):
    """
    Add or update individual and family records in the given project.

    Args:
        project (object): Django ORM model for the project to add families to
        individual_records (list): A list of JSON records representing individuals. See
            the return value of pedigree_info_utils#convert_fam_file_rows_to_json(..)

    Return:
        2-tuple: updated_families, updated_individuals containing Django ORM models

    """
    updated_families = set()
    updated_individuals = set()
    parent_updates = []

    family_ids = {_get_record_family_id(record) for record in individual_records}
    families_by_id = {f.family_id: f for f in Family.objects.filter(project=project, family_id__in=family_ids)}

    missing_family_ids = family_ids - set(families_by_id.keys())
    for family_id in missing_family_ids:
        family = create_model_from_json(Family, {'project': project, 'family_id': family_id}, user)
        families_by_id[family_id] = family
        updated_families.add(family)
        logger.info('Created family: {}'.format(family))

    individual_models = Individual.objects.filter(family__project=project).prefetch_related(
        'family', 'mother', 'father')
    has_individual_guid = any(record.get('individualGuid') for record in individual_records)
    if has_individual_guid:
        individual_lookup = {
            i.guid: i for i in individual_models.filter(
            guid__in=[record['individualGuid'] for record in individual_records])
        }
    else:
        individual_lookup = defaultdict(dict)
        for i in individual_models.filter(
                individual_id__in=[_get_record_individual_id(record) for record in individual_records]):
            individual_lookup[i.individual_id][i.family] = i

    for record in individual_records:
        family_id = _get_record_family_id(record)
        family = families_by_id.get(family_id)

        if has_individual_guid:
            individual = individual_lookup[record.pop('individualGuid')]
        else:
            # uploaded files do not have unique guid's so fall back to a combination of family and individualId
            individual_id = _get_record_individual_id(record)
            individual = individual_lookup[individual_id].get(family)
            if not individual:
                individual = create_model_from_json(
                    Individual, {'family': family, 'individual_id': individual_id, 'case_review_status': 'I'}, user)

        record['family'] = family
        record.pop('familyId', None)
        if individual.family != family:
            family = individual.family
            updated_families.add(family)

        previous_id = record.pop(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN, None)
        if previous_id:
            updated_individuals.update(individual.maternal_children.all())
            updated_individuals.update(individual.paternal_children.all())
            record['displayName'] = ''

        # Update the parent ids last, so if they are referencing updated individuals they will check for the correct ID
        if record.get('maternalId') or record.get('paternalId'):
            parent_updates.append({
                'individual': individual,
                'maternalId': record.pop('maternalId', None),
                'paternalId': record.pop('paternalId', None),
            })

        family_notes = record.pop(JsonConstants.FAMILY_NOTES_COLUMN, None)
        if family_notes:
            update_family_from_json(family, {'analysis_notes': family_notes}, user)
            updated_families.add(family)

        is_updated = update_individual_from_json(individual, record, user=user, allow_unknown_keys=True)
        if is_updated:
            updated_individuals.add(individual)
            updated_families.add(family)

    for update in parent_updates:
        individual = update.pop('individual')
        is_updated = update_individual_from_json(individual, update, user=user)
        if is_updated:
            updated_individuals.add(individual)
            updated_families.add(individual.family)

    # update pedigree images
    update_pedigree_images(updated_families, user, project_guid=project.guid)

    return list(updated_families), list(updated_individuals)


def delete_individuals(project, individual_guids, user):
    """Delete one or more individuals

    Args:
        project (object): Django ORM model for project
        individual_guids (list): GUIDs of individuals to delete

    Returns:
        list: Family objects for families with deleted individuals
    """

    individuals_to_delete = Individual.objects.filter(
        family__project=project, guid__in=individual_guids)

    Sample.bulk_delete(user, individual__family__project=project, individual__guid__in=individual_guids)
    IgvSample.bulk_delete(user, individual__family__project=project, individual__guid__in=individual_guids)

    families = {individual.family for individual in individuals_to_delete}

    Individual.bulk_delete(user, queryset=individuals_to_delete)

    update_pedigree_images(families, user)

    families_with_deleted_individuals = list(families)

    return families_with_deleted_individuals


def get_parsed_feature(feature):
    optional_fields = ['notes', 'qualifiers']
    feature_json = {'id': feature['id']}

    for field in optional_fields:
        if field in feature:
            feature_json[field] = feature[field]

    return feature_json
