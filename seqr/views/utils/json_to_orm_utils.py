from django.core.exceptions import PermissionDenied
from django.utils import timezone

from seqr.models import Individual, get_audit_field_names
from seqr.utils.logging_utils import log_model_update, SeqrLogger
from seqr.views.utils.json_utils import _to_snake_case
from seqr.views.utils.permissions_utils import user_is_analyst

logger = SeqrLogger(__name__)


def update_project_from_json(project, json, user, allow_unknown_keys=False, updated_fields=None):

    update_model_from_json(project, json, user, allow_unknown_keys=allow_unknown_keys, updated_fields=updated_fields,
                           immutable_keys=['consent_code', 'genome_version', 'workspace_namespace', 'workspace_name'])


def update_family_from_json(family, json, user, allow_unknown_keys=False, immutable_keys=None):
    if json.get('displayName') and json['displayName'] == family.family_id:
        json['displayName'] = ''

    immutable_keys = (immutable_keys or []) + ['pedigree_image', 'assigned_analyst', 'case_review_summary', 'case_review_notes', 'guid']

    return update_model_from_json(
        family, json, user=user, allow_unknown_keys=allow_unknown_keys, immutable_keys=immutable_keys,
    )


def update_individual_from_json(individual, json, user, allow_unknown_keys=False):
    if json.get('displayName') and json['displayName'] == individual.individual_id:
        json['displayName'] = ''

    return update_model_from_json(
        individual, json, user=user, allow_unknown_keys=allow_unknown_keys,
        immutable_keys=[
            'filter_flags', 'pop_platform_filters', 'population', 'sv_flags',
            'features', 'absent_features', 'nonstandard_features', 'absent_nonstandard_features',
            'case_review_status', 'case_review_discussion'
        ],
    )


def update_individual_parents(individual, json, user):
    has_update_model = 'mother' in json or 'father' in json
    update_json = {}
    _parse_parent_field(update_json, json, individual, 'mother', parent_id_key=None if has_update_model else 'maternalId')
    _parse_parent_field(update_json, json, individual, 'father', parent_id_key=None if has_update_model else 'paternalId')

    return update_model_from_json(individual, update_json, user)


def _parse_parent_field(update_json, all_json, individual, parent_key, parent_id_key):
    updated_parent = all_json.get(parent_id_key) if parent_id_key else all_json.get(parent_key)
    parent = getattr(individual, parent_key, None)
    if parent_id_key:
        parent = parent.individual_id if parent else None
    if updated_parent != parent:
        if parent_id_key:
            updated_parent = Individual.objects.get(individual_id=updated_parent, family=individual.family) if updated_parent else None
        update_json[parent_key] = updated_parent


def update_model_from_json(model_obj, json, user, allow_unknown_keys=False, immutable_keys=None, updated_fields=None, verbose=True):
    immutable_keys = (immutable_keys or []) + ['created_by', 'created_date', 'last_modified_date', 'id']
    internal_fields = model_obj._meta.internal_json_fields if hasattr(model_obj._meta, 'internal_json_fields') else []
    audit_fields = model_obj._meta.audit_fields if hasattr(model_obj._meta, 'audit_fields') else set()
    for audit_field in audit_fields:
        immutable_keys += get_audit_field_names(audit_field)

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
            if orm_key in internal_fields and not user_is_analyst(user):
                raise PermissionDenied('User {0} is not authorized to edit the internal field {1}'.format(user, orm_key))
            updated_fields.add(orm_key)
            setattr(model_obj, orm_key, value)
            if orm_key in audit_fields:
                updated_fields.update(get_audit_field_names(orm_key))
                setattr(model_obj, '{}_last_modified_date'.format(orm_key), timezone.now())
                setattr(model_obj, '{}_last_modified_by'.format(orm_key), user)

    if updated_fields:
        model_obj.save()
        if verbose:
            log_model_update(logger, model_obj, user, 'update', updated_fields)
    return bool(updated_fields)


def create_model_from_json(model_class, json, user):
    model = model_class.objects.create(created_by=user, **json)
    log_model_update(logger, model, user, 'create', json.keys())
    return model


def get_or_create_model_from_json(model_class, create_json, update_json, user, update_on_create_only=False):
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
    elif update_on_create_only:
        update_json = None
    if update_json or updated_fields:
        update_model_from_json(model, update_json or {}, user, updated_fields=updated_fields, verbose=not created)
    return model, created
