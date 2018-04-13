import logging
from seqr.models import Project as SeqrProject, Family as SeqrFamily, Individual as SeqrIndividual, \
    VariantTagType as SeqrVariantTagType, VariantTag as SeqrVariantTag, VariantNote as SeqrVariantNote

XBROWSE_TO_SEQR_CLASS_MAPPING = {
    "Project": SeqrProject,
    "Family": SeqrFamily,
    "Individual": SeqrIndividual,
    "ProjectTag": SeqrVariantTagType,
    "VariantTag": SeqrVariantTag,
    "VariantNote": SeqrVariantNote,
}

XBROWSE_TO_SEQR_FIELD_MAPPING = {
    "Project": {
        "project_name": "name",
        'project_id': 'deprecated_project_id',
        'last_accessed_date': 'deprecated_last_accessed_date',
    },
    "Family": {
        "family_name": "display_name",
        "short_description": "description",
        "about_family_content": "analysis_notes",
        "analysis_summary_content": "analysis_summary",
    },
    "Individual": {
        'gender': 'sex',
        'nickname': 'display_name',
        'phenotips_id': 'phenotips_eid',
    },
    "ProjectTag": {
        "tag": "name",
        "title": "description",
    },
    "VariantTag": {
        "project_tag": "variant_tag_type",
        "date_saved": "created_date",
        "user": "created_by",
        "xpos": "xpos_start",
    },
    "VariantNote": {
        "project_tag": "variant_tag_type",
        "date_saved": "created_date",
        "user": "created_by",
        "xpos": "xpos_start",
    },
}


def _update_model(model_obj, **kwargs):
    for field, value in kwargs.items():
        setattr(model_obj, field, value)

    model_obj.save()


def _is_xbrowse_model(obj):
    return type(obj).__module__ == "xbrowse_server.base.models"


def find_matching_seqr_model(xbrowse_model):
    if not _is_xbrowse_model(xbrowse_model):
        raise ValueError("Unexpected model class: %s.%s" % (type(xbrowse_model).__module__, type(xbrowse_model).__name__))

    try:
        xbrowse_class_name = type(xbrowse_model).__name__

        if xbrowse_class_name == "Project":
            return xbrowse_model.seqr_project if xbrowse_model.seqr_project else SeqrProject.objects.get(
                    deprecated_project_id=xbrowse_model.project_id)
        elif xbrowse_class_name == "Family":
            return xbrowse_model.seqr_family if xbrowse_model.seqr_family else SeqrFamily.objects.get(
                project__deprecated_project_id=xbrowse_model.project.project_id,
                family_id=xbrowse_model.family_id)
        elif xbrowse_class_name == "Individual":
            return xbrowse_model.seqr_individual if xbrowse_model.seqr_individual else SeqrIndividual.objects.get(
                family__project__deprecated_project_id=xbrowse_model.project.project_id,
                family__family_id=xbrowse_model.family.family_id,
                individual_id=xbrowse_model.indiv_id)
        elif xbrowse_class_name == "ProjectTag":
            return xbrowse_model.seqr_variant_tag_type if xbrowse_model.seqr_variant_tag_type else SeqrVariantTagType.objects.get(
                project__project_id=xbrowse_model.deprecated_project_id,
                name=xbrowse_model.tag)
        elif xbrowse_class_name == "VariantTag":
            if xbrowse_model.seqr_variant_tag:
                return xbrowse_model.seqr_variant_tag

            if xbrowse_model.family:
                return SeqrVariantTag.objects.get(
                    variant_tag_type__project__project_id=xbrowse_model.deprecated_project_id,
                    xpos_start=xbrowse_model.xpos,
                    ref=xbrowse_model.ref,
                    alt=xbrowse_model.alt,
                    family__family_id=xbrowse_model.family.family_id)
            else:
                return SeqrVariantTag.objects.get(
                    variant_tag_type__project__project_id=xbrowse_model.deprecated_project_id,
                    xpos_start=xbrowse_model.xpos,
                    ref=xbrowse_model.ref,
                    alt=xbrowse_model.alt)
        elif xbrowse_class_name == "VariantNote":
            if xbrowse_model.seqr_variant_note:
                return xbrowse_model.seqr_variant_note

            if xbrowse_model.family:
                return SeqrVariantNote.objects.get(
                    project__project_id=xbrowse_model.deprecated_project_id,
                    xpos_start=xbrowse_model.xpos,
                    ref=xbrowse_model.ref,
                    alt=xbrowse_model.alt,
                    family__family_id=xbrowse_model.family.family_id)
            else:
                return SeqrVariantNote.objects.get(
                    project__project_id=xbrowse_model.deprecated_project_id,
                    xpos_start=xbrowse_model.xpos,
                    ref=xbrowse_model.ref,
                    alt=xbrowse_model.alt)

    except Exception as e:
        logging.error("ERROR: when looking up seqr model for xbrowse %s model: %s" % (xbrowse_model, e))

    return None

def _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, **kwargs):
    # rename fields
    xbrowse_class_name = type(xbrowse_model).__name__
    seqr_kwargs = {
        XBROWSE_TO_SEQR_FIELD_MAPPING[xbrowse_class_name].get(field, field): value for field, value in kwargs.items()
    }

    # handle foreign keys
    for key, value in seqr_kwargs.items():
        if _is_xbrowse_model(value):
            value = find_matching_seqr_model(value)
            if value is not None:
                seqr_kwargs[key] = value
            else:
                logging.info("ERROR: unable to find equivalent seqr model for %s: %s" % (key, value))
                del seqr_kwargs[key]

    return seqr_kwargs

def update_xbrowse_model(xbrowse_model, **kwargs):
    print("update_xbrowse_model(%s, %s)" % (xbrowse_model, kwargs))
    _update_model(xbrowse_model, **kwargs)

    seqr_model = find_matching_seqr_model(xbrowse_model)
    if not seqr_model:
        return

    seqr_kwargs = _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, **kwargs)

    _update_model(seqr_model, **seqr_kwargs)


def get_or_create_xbrowse_model(xbrowse_model_class, **kwargs):
    print("get_or_create_xbrowse_model(%s, %s)" % (xbrowse_model_class, kwargs))
    xbrowse_model, created = xbrowse_model_class.objects.get_or_create(**kwargs)

    if created:
        seqr_model = find_matching_seqr_model(xbrowse_model)
        if seqr_model is not None:
            logging.error("ERROR: created xbrowse model: %s, but seqr model already exists: %s" % (xbrowse_model, seqr_model))
        elif xbrowse_model_class.__name__ not in XBROWSE_TO_SEQR_CLASS_MAPPING:
            logging.error("ERROR: create operation not implemented for xbrowse model: %s" % (xbrowse_model_class.__name__))
        else:
            seqr_kwargs = _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, **kwargs)
            seqr_model_class = XBROWSE_TO_SEQR_CLASS_MAPPING[xbrowse_model_class]
            seqr_model_class.objects.create(**seqr_kwargs)

    return xbrowse_model, created


def delete_xbrowse_model(xbrowse_model):
    print("delete_xbrowse_model(%s)" % (xbrowse_model,))
    seqr_model = find_matching_seqr_model(xbrowse_model)
    xbrowse_model.delete()

    try:
        if type(xbrowse_model).__name__ == "Individual":
            # first delete related samples
            for sample in seqr_model.sample_set.all():
                sample.delete()

        seqr_model.delete()
    except Exception as e:
        logging.error("ERROR: error when deleting seqr model %s: %s" % (seqr_model, e))