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


def create_seqr_model(seqr_model_class, **kwargs):
    logging.info("create_seqr_model(%s, %s)" % (seqr_model_class.__name__, kwargs))
    seqr_model = seqr_model_class.objects.create(**kwargs)

    return seqr_model


def get_or_create_seqr_model(seqr_model_class, **kwargs):
    logging.info("get_or_create_seqr_model(%s, %s)" % (seqr_model_class, kwargs))
    seqr_model, created = seqr_model_class.objects.get_or_create(**kwargs)

    return seqr_model, created


def delete_seqr_model(seqr_model):
    logging.info("delete_seqr_model(%s)" % seqr_model)
    seqr_model.delete()
