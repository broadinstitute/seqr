import logging
from django.utils import timezone

from seqr.views.utils.json_utils import _to_snake_case

logger = logging.getLogger(__name__)


def update_project_from_json(project, json, verbose=False):

    _update_model_from_json(project, json, verbose=verbose)


def update_family_from_json(family, json, verbose=False, user=None, allow_unknown_keys=False):
    _update_model_from_json(
        family, json, user=user, verbose=verbose, allow_unknown_keys=allow_unknown_keys, restricted_keys=['pedigree_image']
    )


def update_individual_from_json(individual, json, verbose=False, user=None, allow_unknown_keys=False):
    if json.get('caseReviewStatus') and json['caseReviewStatus'] != individual.case_review_status:
        json['caseReviewStatusLastModifiedBy'] = user
        json['caseReviewStatusLastModifiedDate'] = timezone.now()
    else:
        json.pop('caseReviewStatusLastModifiedBy', None)
        json.pop('caseReviewStatusLastModifiedDate', None)

    _update_model_from_json(
        individual, json, user=user, verbose=verbose, allow_unknown_keys=allow_unknown_keys, restricted_keys=['phenotips_data']
    )


def _update_model_from_json(model_obj, json, user=None, verbose=False, allow_unknown_keys=False, restricted_keys=[]):
    modified = False
    for json_key, value in json.items():
        orm_key = _to_snake_case(json_key)
        if orm_key in restricted_keys:
            if allow_unknown_keys:
                continue
            raise ValueError('Cannot edit field field {}'.format(orm_key))
        if allow_unknown_keys and not hasattr(model_obj, orm_key):
            continue
        if getattr(model_obj, orm_key) != value:
            if orm_key in model_obj._meta.internal_json_fields and not (user and user.is_staff):
                raise ValueError('User {0} is not authorized to edit the internal field {1}'.format(user, orm_key))
            modified = True
            if verbose:
                model_obj_name = getattr(model_obj, 'guid', model_obj.__name__)
                logger.info("Setting {0}.{1} to {2}".format(model_obj_name, orm_key, value))
            setattr(model_obj, orm_key, value)

    if modified:
        model_obj.save()
