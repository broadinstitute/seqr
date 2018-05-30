import logging

from seqr.model_utils import find_matching_xbrowse_model, convert_seqr_kwargs_to_xbrowse_kwargs
from seqr.views.utils.json_utils import _to_snake_case

logger = logging.getLogger(__name__)


def update_project_from_json(project, json, verbose=False):

    _update_model_from_json(project, json, verbose=verbose)


def update_family_from_json(family, json, verbose=False, user=None, allow_unknown_keys=False):

    _update_model_from_json(family, json, user=user, verbose=verbose, allow_unknown_keys=allow_unknown_keys)


def update_individual_from_json(individual, json, verbose=False, user=None, allow_unknown_keys=False):

    _update_model_from_json(individual, json, user=user, verbose=verbose, allow_unknown_keys=allow_unknown_keys)


def _update_model_from_json(model_obj, json, user=None, verbose=False, allow_unknown_keys=False):
    modified = False

    xbrowse_model = None
    try:
        xbrowse_model = find_matching_xbrowse_model(model_obj)
    except Exception as e:
        logger.error("Unable to find matching xbrowse model for {0}: {1}".format(model_obj, e))

    for json_key, value in json.items():
        orm_key = _to_snake_case(json_key)
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
            try:
                if xbrowse_model is not None:
                    xbrowse_kwargs = convert_seqr_kwargs_to_xbrowse_kwargs(xbrowse_model, **{orm_key: value})
                    for key, value in xbrowse_kwargs.items():
                        setattr(model_obj, key, value)
            except Exception as e:
                logger.error("Unable to update xbrowse model {0}: {1}".format(xbrowse_model, e))

    if modified:
        model_obj.save()

        if xbrowse_model is not None:
            xbrowse_model.save()
