import logging
from django.utils import timezone

from seqr.models import Individual
from seqr.model_utils import update_seqr_model
from seqr.utils.model_sync_utils import can_edit_family_id, can_edit_individual_id
from seqr.views.utils.json_utils import _to_snake_case

logger = logging.getLogger(__name__)


def update_project_from_json(project, json, verbose=False, allow_unknown_keys=False):

    update_model_from_json(project, json, verbose=verbose, allow_unknown_keys=allow_unknown_keys, immutable_keys=['genome_version'])


def update_family_from_json(family, json, verbose=False, user=None, allow_unknown_keys=False):
    if json.get('displayName') and json['displayName'] == family.family_id:
        json['displayName'] = ''

    update_model_from_json(
        family, json, user=user, verbose=verbose, allow_unknown_keys=allow_unknown_keys,
        immutable_keys=['pedigree_image', 'assigned_analyst'], conditional_edit_keys={'family_id': can_edit_family_id}
    )


def update_individual_from_json(individual, json, verbose=False, user=None, allow_unknown_keys=False):
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

    update_model_from_json(
        individual, json, user=user, verbose=verbose, allow_unknown_keys=allow_unknown_keys,
        immutable_keys=['phenotips_data', 'filter_flags', 'pop_platform_filters', 'population'],
        conditional_edit_keys={'individual_id': can_edit_individual_id}
    )


def _parse_parent_field(json, individual, parent_key, parent_id_key):
    parent = getattr(individual, parent_key, None)
    if parent_id_key in json:
        parent_id = json.pop(parent_id_key)
        if parent_id != (parent.individual_id if parent else None):
            json[parent_key] = Individual.objects.get(individual_id=parent_id, family=individual.family) if parent_id else None


def update_model_from_json(model_obj, json, user=None, verbose=False, allow_unknown_keys=False, immutable_keys=None, conditional_edit_keys=None):
    immutable_keys = (immutable_keys or []) + ['created_by', 'created_date', 'last_modified_date', 'id']
    seqr_update_fields = {}
    internal_fields = model_obj._meta.internal_json_fields if hasattr(model_obj._meta, 'internal_json_fields') else []

    for json_key, value in json.items():
        orm_key = _to_snake_case(json_key)
        if orm_key in immutable_keys:
            if allow_unknown_keys:
                continue
            raise ValueError('Cannot edit field {}'.format(orm_key))
        if allow_unknown_keys and not hasattr(model_obj, orm_key):
            continue
        if getattr(model_obj, orm_key) != value:
            if orm_key in internal_fields and not (user and user.is_staff):
                raise ValueError('User {0} is not authorized to edit the internal field {1}'.format(user, orm_key))
            if conditional_edit_keys and orm_key in conditional_edit_keys:
                conditional_edit_keys[orm_key](model_obj)
            if verbose:
                model_obj_name = getattr(model_obj, 'guid', None) or model_obj.__name__
                logger.info("Setting {0}.{1} to {2}".format(model_obj_name, orm_key, value))
            seqr_update_fields[orm_key] = value

    if seqr_update_fields:
        update_seqr_model(model_obj, **seqr_update_fields)