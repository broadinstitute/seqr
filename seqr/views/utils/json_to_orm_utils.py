import logging
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from seqr.models import Individual
from seqr.utils.logging_utils import log_model_update
from seqr.views.utils.json_utils import _to_snake_case

logger = logging.getLogger(__name__)


def update_project_from_json(project, json, user, allow_unknown_keys=False):

    update_model_from_json(project, json, user, allow_unknown_keys=allow_unknown_keys, immutable_keys=['genome_version'])


def update_family_from_json(family, json, user, allow_unknown_keys=False):
    if json.get('displayName') and json['displayName'] == family.family_id:
        json['displayName'] = ''

    update_model_from_json(
        family, json, user=user, allow_unknown_keys=allow_unknown_keys,
        immutable_keys=['pedigree_image', 'assigned_analyst'],
    )


def update_individual_from_json(individual, json, user, allow_unknown_keys=False):
    if json.get('caseReviewStatus') and json['caseReviewStatus'] != individual.case_review_status:
        json['caseReviewStatusLastModifiedBy'] = user
        json['caseReviewStatusLastModifiedDate'] = timezone.now()
    else:
        json.pop('caseReviewStatusLastModifiedBy', None)
        json.pop('caseReviewStatusLastModifiedDate', None)

    _parse_parent_field(json, individual, 'mother', 'maternalId')
    _parse_parent_field(json, individual, 'father', 'paternalId')

    if json.get('displayName') and json['displayName'] == individual.individual_id:
        json['displayName'] = ''

    return update_model_from_json(
        individual, json, user=user, allow_unknown_keys=allow_unknown_keys,
        immutable_keys=[
            'filter_flags', 'pop_platform_filters', 'population', 'sv_flags',
            'features', 'absent_features', 'nonstandard_features', 'absent_nonstandard_features',
        ],
    )


def _parse_parent_field(json, individual, parent_key, parent_id_key):
    parent = getattr(individual, parent_key, None)
    if parent_id_key in json:
        parent_id = json.pop(parent_id_key)
        if parent_id != (parent.individual_id if parent else None):
            json[parent_key] = Individual.objects.get(individual_id=parent_id, family=individual.family) if parent_id else None


def update_model_from_json(model_obj, json, user, allow_unknown_keys=False, immutable_keys=None, updated_fields=None, verbose=True):
    immutable_keys = (immutable_keys or []) + ['created_by', 'created_date', 'last_modified_date', 'id']
    internal_fields = model_obj._meta.internal_json_fields if hasattr(model_obj._meta, 'internal_json_fields') else []

    if not updated_fields:
        updated_fields = set()
    for json_key, value in json.items():
        orm_key = _to_snake_case(json_key)
        if orm_key in immutable_keys:
            if allow_unknown_keys:
                continue
            raise ValueError('Cannot edit field {}'.format(orm_key))
        if allow_unknown_keys and not hasattr(model_obj, orm_key):
            continue
        if getattr(model_obj, orm_key) != value:
            if orm_key in internal_fields and not user.is_staff:
                raise PermissionDenied('User {0} is not authorized to edit the internal field {1}'.format(user, orm_key))
            updated_fields.add(orm_key)
            setattr(model_obj, orm_key, value)

    if updated_fields:
        model_obj.save()
        if verbose:
            log_model_update(logger, model_obj, user, 'update', updated_fields)
    return bool(updated_fields)


def create_model_from_json(model_class, json, user):
    model = model_class.objects.create(created_by=user, **json)
    log_model_update(logger, model, user, 'create', json.keys())
    return model


def get_or_create_model_from_json(model_class, create_json, update_json, user):
    model, created = model_class.objects.get_or_create(**create_json)
    updated_fields = set()
    if created:
        if 'created_by' not in create_json and hasattr(model, 'created_by'):
            model.created_by = user
            updated_fields.add('created_by')
        log_update_fields = list(create_json.keys()) + list(updated_fields)
        if update_json:
            log_update_fields += list(update_json.keys())
        log_model_update(logger, model, user, 'create', log_update_fields)
    if update_json or updated_fields:
        update_model_from_json(model, update_json or {}, user, updated_fields=updated_fields, verbose=not created)
    return model, created
