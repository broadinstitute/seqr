import logging

#  TODO get rud of these helpers


def _update_model(model_obj, **kwargs):
    for field, value in kwargs.items():
        setattr(model_obj, field, value)

    model_obj.save()


def _is_seqr_model(obj):
    return type(obj).__module__ == "seqr.models"


def update_seqr_model(seqr_model, **kwargs):
    logging.info("update_seqr_model(%s, %s)" % (seqr_model, kwargs))
    _update_model(seqr_model, **kwargs)
