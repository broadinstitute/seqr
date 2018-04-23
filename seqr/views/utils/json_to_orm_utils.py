import logging

from seqr.views.utils.json_utils import _to_snake_case

logger = logging.getLogger(__name__)


def update_project_from_json(project, json, verbose=False):

    _update_model_from_json(project, json, verbose=verbose)


def update_family_from_json(family, json, verbose=False, user=None):

    _update_model_from_json(family, json, user=user, verbose=verbose)


def update_individual_from_json(individual, json, verbose=False, user=None):

    _update_model_from_json(individual, json, user=user, verbose=verbose)


def _update_model_from_json(model_obj, json, user=None, verbose=False):
    modified = False
    for json_key, value in json.items():
        orm_key = _to_snake_case(json_key)
        if orm_key in model_obj._meta.internal_json_fields and not (user and user.is_staff):
            raise ValueError('User {0} is not authorized to edit the internal field {1}'.format(user, orm_key))
        if getattr(model_obj, orm_key) != value:
            modified = True
            if verbose:
                model_obj_name = getattr(model_obj, 'guid', model_obj.__name__)
                logger.info("Setting {0}.{1} to {2}".format(model_obj_name, orm_key, value))
            setattr(model_obj, orm_key, value)

    if modified:
        model_obj.save()
