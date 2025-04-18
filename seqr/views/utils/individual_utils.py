"""
APIs for retrieving, updating, creating, and deleting Individual records
"""
from collections import defaultdict

from matchmaker.models import MatchmakerSubmission, MatchmakerResult
from seqr.models import Sample, IgvSample, RnaSample, Individual, Family, FamilyNote
from seqr.utils.middleware import ErrorsWarningsException
from seqr.utils.search.utils import backend_specific_call
from seqr.views.utils.json_to_orm_utils import update_individual_from_json, update_individual_parents, create_model_from_json, \
    update_family_from_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals, _get_json_for_families, get_json_for_family_notes
from seqr.views.utils.pedigree_info_utils import JsonConstants


def _get_record_family_id(record):
    # family id will be in different places in the json depending on whether it comes from a flat uploaded file or from the nested individual object
    return record.get(JsonConstants.FAMILY_ID_COLUMN) or record.get('family', {})['familyId']


def _get_record_individual_id(record):
    return record.get(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN) or record[JsonConstants.INDIVIDUAL_ID_COLUMN]


def add_or_update_individuals_and_families(project, individual_records, user, get_update_json=True, get_updated_individual_db_ids=False, get_created_counts=False, allow_features_update=False):
    """
    Add or update individual and family records in the given project.

    Args:
        project (object): Django ORM model for the project to add families to
        individual_records (list): A list of JSON records representing individuals. See
            the return value of pedigree_info_utils#convert_fam_file_rows_to_json(..)
        user (object): current user model

    Return:
        3-tuple: updated Individual models, updated Family models, and updated FamilyNote models

    """
    updated_family_ids = set()
    updated_individuals = set()
    updated_note_ids = []
    parent_updates = []
    num_created_families = 0
    num_created_individuals = 0

    family_ids = {_get_record_family_id(record) for record in individual_records}
    families_by_id = {f.family_id: f for f in Family.objects.filter(project=project, family_id__in=family_ids)}

    missing_family_ids = family_ids - set(families_by_id.keys())
    for family_id in sorted(missing_family_ids):
        family = create_model_from_json(Family, {'project': project, 'family_id': family_id}, user)
        num_created_families += 1
        families_by_id[family_id] = family
        updated_family_ids.add(family.id)

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
        created_individual = _update_from_record(
            record, user, families_by_id, individual_lookup, updated_family_ids, updated_individuals, parent_updates, updated_note_ids, allow_features_update)
        if created_individual:
            num_created_individuals += 1

    for update in parent_updates:
        individual = update.pop('individual')
        is_updated = update_individual_parents(individual, update, user=user)
        if is_updated:
            updated_individuals.add(individual)
            if individual.family.pedigree_image:
                updated_family_ids.add(individual.family_id)

    updated_family_models = Family.objects.filter(id__in=updated_family_ids)
    _remove_pedigree_images(updated_family_models, user)

    pedigree_json = None
    if get_update_json:
        pedigree_json = _get_updated_pedigree_json(updated_individuals, updated_family_models, updated_note_ids, user)

    if get_updated_individual_db_ids:
        return pedigree_json, {i.id for i in updated_individuals}

    if get_created_counts:
        return pedigree_json, num_created_families, num_created_individuals

    return pedigree_json


def _update_from_record(record, user, families_by_id, individual_lookup, updated_family_ids, updated_individuals, parent_updates, updated_note_ids, allow_features_update):
    family_id = _get_record_family_id(record)
    family = families_by_id.get(family_id)
    created_individual = False

    if record.get('individualGuid'):
        individual = individual_lookup[record.pop('individualGuid')]
    else:
        # uploaded files do not have unique guid's so fall back to a combination of family and individualId
        individual_id = _get_record_individual_id(record)
        individual = individual_lookup[individual_id].get(family)
        if not individual:
            # Individual is being moved to a different family
            individual = next((iter(individual_lookup[individual_id].values())), None)
        if not individual:
            individual = create_model_from_json(
                Individual, {'family': family, 'individual_id': individual_id, 'case_review_status': 'I'}, user)
            updated_family_ids.add(family.id)
            updated_individuals.add(individual)
            individual_lookup[individual_id][family] = individual
            created_individual = True

    record['family'] = family
    record.pop('familyId', None)
    if individual.family != family:
        updated_family_ids.add(family.id)
        updated_family_ids.add(individual.family_id)
        family = individual.family

    previous_id = record.pop(JsonConstants.PREVIOUS_INDIVIDUAL_ID_COLUMN, None)
    if previous_id:
        updated_individuals.update(individual.maternal_children.all())
        updated_individuals.update(individual.paternal_children.all())
        record['displayName'] = ''

    # Update the parent ids last, so if they are referencing updated individuals they will check for the correct ID
    if 'father' in record or 'mother' in record:
        parent_updates.append({
            'individual': individual,
            'mother': record.pop('mother', None),
            'father': record.pop('father', None),
        })
    elif record.get('maternalId') or record.get('paternalId'):
        parent_updates.append({
            'individual': individual,
            'maternalId': record.pop('maternalId', None),
            'paternalId': record.pop('paternalId', None),
        })

    family_notes = record.pop(JsonConstants.FAMILY_NOTES_COLUMN, None)
    if family_notes:
        note = create_model_from_json(FamilyNote, {'note': family_notes, 'note_type': 'C', 'family': family}, user)
        updated_note_ids.append(note.id)

    family_record = {
        k: record.pop(k) for k in [JsonConstants.CODED_PHENOTYPE_COLUMN, JsonConstants.MONDO_ID_COLUMN] if k in record
    }
    if family_record:
        is_updated = update_family_from_json(family, family_record, user=user)
        if is_updated:
            updated_family_ids.add(family.id)

    is_updated = update_individual_from_json(individual, record, user=user, allow_unknown_keys=True, allow_features_update=allow_features_update)
    if is_updated:
        updated_individuals.add(individual)
        if family.pedigree_image:
            updated_family_ids.add(family.id)

    return created_individual


def delete_individuals(project, individual_guids, user):
    """Delete one or more individuals

    Args:
        project (object): Django ORM model for project
        individual_guids (list): GUIDs of individuals to delete

    Returns:
        list: Family objects for families with deleted individuals
    """
    errors, individuals_to_delete = check_project_individuals_deletable(project, individual_guids=individual_guids)
    if errors:
        raise ErrorsWarningsException(errors)

    Sample.bulk_delete(user, individual__in=individuals_to_delete)
    IgvSample.bulk_delete(user, individual__in=individuals_to_delete)
    RnaSample.bulk_delete(user, individual__in=individuals_to_delete)
    MatchmakerResult.bulk_delete(user, submission__individual__in=individuals_to_delete, submission__deleted_date__isnull=False)
    MatchmakerSubmission.bulk_delete(user, individual__in=individuals_to_delete, deleted_date__isnull=False)

    deleted_individual_family_ids = list(Family.objects.filter(individual__in=individuals_to_delete).values_list('id', flat=True))
    Individual.bulk_delete(user, queryset=individuals_to_delete)

    families_with_deleted_individuals = Family.objects.filter(id__in=deleted_individual_family_ids)

    _remove_pedigree_images(families_with_deleted_individuals, user)

    return families_with_deleted_individuals


def check_project_individuals_deletable(project, individual_guids=None):
    individuals_to_delete = Individual.objects.filter(family__project=project)
    if individual_guids is not None:
        individuals_to_delete = individuals_to_delete.filter(guid__in=individual_guids)

    errors = backend_specific_call(_validate_no_submissions, _validate_no_sumissions_no_search_samples, _validate_no_sumissions_no_search_samples)(individuals_to_delete)
    return errors, individuals_to_delete


def _validate_delete_individuals(individuals_to_delete, error_type, query):
    errors = []
    invalid_individuals = individuals_to_delete.filter(**query).distinct().values_list('individual_id', flat=True)
    if invalid_individuals:
        errors.append(f'Unable to delete individuals with active {error_type}: {", ".join(sorted(invalid_individuals))}')
    return errors


def _validate_no_submissions(individuals_to_delete):
    return _validate_delete_individuals(
        individuals_to_delete, 'MME submission',
        dict(matchmakersubmission__isnull=False, matchmakersubmission__deleted_date__isnull=True)
    )


def _validate_no_sumissions_no_search_samples(individuals_to_delete):
    return _validate_no_submissions(individuals_to_delete) + _validate_delete_individuals(
        individuals_to_delete, 'search sample', dict(sample__is_active=True)
    )


def _remove_pedigree_images(families, user):
    Family.bulk_update(user, {'pedigree_image': None}, queryset=families)


def _get_updated_pedigree_json(updated_individuals, updated_families, updated_note_ids, user):
    individuals_by_guid = {
        individual['individualGuid']: individual for individual in
        _get_json_for_individuals(Individual.objects.filter(id__in=[
            i.id for i in updated_individuals
        ]), user, add_sample_guids_field=True)
    }
    families_by_guid = {
        family['familyGuid']: family for family in
        _get_json_for_families(updated_families, user, add_individual_guids_field=True)
    }

    response = {
        'individualsByGuid': individuals_by_guid,
        'familiesByGuid': families_by_guid,
    }
    if updated_note_ids:
        family_notes_by_guid = {note['noteGuid']: note for note in get_json_for_family_notes(
            FamilyNote.objects.filter(id__in=updated_note_ids)
        )}
        response['familyNotesByGuid'] = family_notes_by_guid

    return response
