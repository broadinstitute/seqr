import logging
import re
import traceback

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from seqr.models import Project as SeqrProject, Family as SeqrFamily, Individual as SeqrIndividual, \
    VariantTagType as SeqrVariantTagType, VariantTag as SeqrVariantTag, VariantNote as SeqrVariantNote, \
    VariantFunctionalData as SeqrVariantFunctionalData, LocusList as SeqrLocusList, LocusListGene as SeqrLocusListGene
from seqr.utils.model_sync_utils import get_or_create_saved_variant


XBROWSE_TO_SEQR_CLASS_MAPPING = {
    "Project": SeqrProject,
    "Family": SeqrFamily,
    "Individual": SeqrIndividual,
    "ProjectTag": SeqrVariantTagType,
    "VariantTag": SeqrVariantTag,
    "VariantFunctionalData": SeqrVariantFunctionalData,
    "VariantNote": SeqrVariantNote,
    "GeneList": SeqrLocusList,
    "GeneListItem": SeqrLocusListGene,
}

_DELETED_FIELD = "__DELETED__"

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
        "project": _DELETED_FIELD,
        "indiv_id": "individual_id",
        "gender": "sex",
        "nickname": "display_name",
        "phenotips_id": "phenotips_eid",
        "other_notes": "notes",
    },
    "ProjectTag": {
        "tag": "name",
        "title": "description",
    },
    "VariantTag": {
        "project_tag": "variant_tag_type",
        "search_url": "search_parameters",
        "user": "created_by",
        "date_saved": _DELETED_FIELD,
        "xpos": _DELETED_FIELD,
        "ref": _DELETED_FIELD,
        "alt": _DELETED_FIELD,
        "family": _DELETED_FIELD,
    },
    "VariantFunctionalData": {
        "search_url": "search_parameters",
        "user": "created_by",
        "date_saved": _DELETED_FIELD,
        "xpos": _DELETED_FIELD,
        "ref": _DELETED_FIELD,
        "alt": _DELETED_FIELD,
        "family": _DELETED_FIELD,
    },
    "VariantNote": {
        "search_url": "search_parameters",
        "user": "created_by",
        "date_saved": _DELETED_FIELD,
        "xpos": _DELETED_FIELD,
        "ref": _DELETED_FIELD,
        "alt": _DELETED_FIELD,
        "family": _DELETED_FIELD,
        "project": _DELETED_FIELD,
    },
    "GeneList": {
        "owner": "created_by",
        "last_updated": _DELETED_FIELD,
        "slug": _DELETED_FIELD,
    },
    "GeneListItem": {
        "gene_list": "locus_list",
    },
}

XBROWSE_TO_SEQR_ADDITIONAL_ENTITIES_MAPPING = {
    "VariantTag": {
        "saved_variant": get_or_create_saved_variant
    },
    "VariantFunctionalData": {
        "saved_variant": get_or_create_saved_variant
    },
    "VariantNote": {
        "saved_variant": get_or_create_saved_variant
    }
}


def _update_model(model_obj, **kwargs):
    for field, value in kwargs.items():
        setattr(model_obj, field, value)

    model_obj.save()


def _is_xbrowse_model(obj):
    return type(obj).__module__ in ("xbrowse_server.base.models", "xbrowse_server.gene_lists.models")


def find_matching_seqr_model(xbrowse_model):
    logging.info("find matching seqr %s for %s" % (type(xbrowse_model).__name__, xbrowse_model))
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
                Q(project__deprecated_project_id=xbrowse_model.project.project_id) | Q(project__isnull=True),
                Q(name=xbrowse_model.tag))
        elif xbrowse_class_name == "VariantTag":
            if xbrowse_model.seqr_variant_tag:
                return xbrowse_model.seqr_variant_tag

            criteria = {
                'variant_tag_type__name': xbrowse_model.project_tag.tag,
                'saved_variant__project__deprecated_project_id': xbrowse_model.project_tag.project.project_id,
                'saved_variant__xpos_start': xbrowse_model.xpos,
                'saved_variant__ref': xbrowse_model.ref,
                'saved_variant__alt': xbrowse_model.alt,
            }
            if xbrowse_model.family:
                criteria['saved_variant__family__family_id'] = xbrowse_model.family.family_id
            return SeqrVariantTag.objects.get(**criteria)
        elif xbrowse_class_name == "VariantFunctionalData":
            if xbrowse_model.seqr_variant_functional_data:
                return xbrowse_model.seqr_variant_functional_data

            criteria = {
                'functional_data_tag': xbrowse_model.functional_data_tag,
                'saved_variant__xpos_start': xbrowse_model.xpos,
                'saved_variant__ref': xbrowse_model.ref,
                'saved_variant__alt': xbrowse_model.alt,
            }
            if xbrowse_model.family:
                criteria['saved_variant__family__family_id'] = xbrowse_model.family.family_id
                criteria['saved_variant__project__deprecated_project_id'] = xbrowse_model.family.project.project_id
            return SeqrVariantFunctionalData.objects.get(**criteria)
        elif xbrowse_class_name == "VariantNote":
            if xbrowse_model.seqr_variant_note:
                return xbrowse_model.seqr_variant_note

            criteria = {
                'note': xbrowse_model.note,
                'saved_variant__project__deprecated_project_id': xbrowse_model.project.project_id,
                'saved_variant__xpos_start': xbrowse_model.xpos,
                'saved_variant__ref': xbrowse_model.ref,
                'saved_variant__alt': xbrowse_model.alt,
            }
            if xbrowse_model.family:
                criteria['saved_variant__family__family_id'] = xbrowse_model.family.family_id
            return SeqrVariantNote.objects.get(**criteria)
        elif xbrowse_class_name == "GeneList":
            return xbrowse_model.seqr_locus_list or SeqrLocusList.objects.get(
                name=xbrowse_model.name,
                description=xbrowse_model.description,
                is_public=xbrowse_model.is_public,
                owner=xbrowse_model.created_by)
        elif xbrowse_class_name == "GeneListItem":
            return SeqrLocusListGene.objects.get(
                locus_list=xbrowse_model.gene_list.seqr_locus_list or find_matching_seqr_model(xbrowse_model.gene_list),
                description=xbrowse_model.description,
                gene_id=xbrowse_model.gene_id)

    except ObjectDoesNotExist:
        pass
    except Exception as e:
        logging.error("ERROR: when looking up seqr model for xbrowse %s model: %s" % (xbrowse_model, e))
        traceback.print_exc()

    return None


def _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, include_all=False, **kwargs):
    # rename fields
    xbrowse_class_name = type(xbrowse_model).__name__
    field_mapping = XBROWSE_TO_SEQR_FIELD_MAPPING[xbrowse_class_name]
    if include_all:
        field_mapping = {k: v for k, v in field_mapping.items() if v != _DELETED_FIELD}

    seqr_kwargs = {
        field_mapping.get(field, field): value for field, value in kwargs.items()
        if not field_mapping.get(field, field) == _DELETED_FIELD
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


def _create_additional_seqr_entities(xbrowse_model, **kwargs):
    xbrowse_class_name = type(xbrowse_model).__name__
    additional_entities_mapping = XBROWSE_TO_SEQR_ADDITIONAL_ENTITIES_MAPPING.get(xbrowse_class_name)
    if not additional_entities_mapping:
        return {}
    seqr_kwargs = _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, include_all=True, **kwargs)
    return {field: entity_func(**seqr_kwargs) for field, entity_func in additional_entities_mapping.items()}


def update_xbrowse_model(xbrowse_model, **kwargs):
    logging.info("update_xbrowse_model(%s, %s)" % (xbrowse_model, kwargs))
    seqr_model = find_matching_seqr_model(xbrowse_model)
    _update_model(xbrowse_model, **kwargs)

    if not seqr_model:
        return

    seqr_kwargs = _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, **kwargs)

    _update_model(seqr_model, **seqr_kwargs)


def _to_snake_case(camel_case_str):
    """Convert CamelCase string to snake_case (from https://gist.github.com/jaytaylor/3660565)"""

    return re.sub("([A-Z])", "_\\1", camel_case_str).lower().lstrip("_")


def _create_seqr_model(xbrowse_model, **kwargs):
    try:
        xbrowse_model_class = xbrowse_model.__class__
        xbrowse_model_class_name = xbrowse_model_class.__name__
        seqr_kwargs = _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, **kwargs)
        seqr_kwargs.update(_create_additional_seqr_entities(xbrowse_model, **kwargs))
        seqr_model_class = XBROWSE_TO_SEQR_CLASS_MAPPING[xbrowse_model_class_name]
        seqr_model_class_name = seqr_model_class.__name__
        logging.info("_create_seqr_model(%s, %s)" % (seqr_model_class_name, seqr_kwargs))
        seqr_model = seqr_model_class.objects.create(**seqr_kwargs)
        xbrowse_model_foreign_key_name = "seqr_"+_to_snake_case(seqr_model_class_name)
        if hasattr(xbrowse_model, xbrowse_model_foreign_key_name):
            setattr(xbrowse_model, xbrowse_model_foreign_key_name, seqr_model)
            xbrowse_model.save()
        return seqr_model

    except Exception as e:
        logging.error("ERROR: error when creating seqr model %s: %s" % (xbrowse_model, e))
        traceback.print_exc()
        return None


def create_xbrowse_model(xbrowse_model_class, **kwargs):
    logging.info("create_xbrowse_model(%s, %s)" % (xbrowse_model_class.__name__, kwargs))
    xbrowse_model = xbrowse_model_class.objects.create(**kwargs)
    _create_seqr_model(xbrowse_model, **kwargs)

    return xbrowse_model


def get_or_create_xbrowse_model(xbrowse_model_class, **kwargs):
    logging.info("get_or_create_xbrowse_model(%s, %s)" % (xbrowse_model_class, kwargs))
    xbrowse_model, created = xbrowse_model_class.objects.get_or_create(**kwargs)

    seqr_model = find_matching_seqr_model(xbrowse_model)
    if created or seqr_model is None:
        if seqr_model is not None:
            logging.error("ERROR: created xbrowse model: %s while seqr model already exists: %s" % (xbrowse_model, seqr_model))
        elif xbrowse_model_class.__name__ not in XBROWSE_TO_SEQR_CLASS_MAPPING:
            logging.error("ERROR: create operation not implemented for xbrowse model: %s" % (xbrowse_model_class.__name__))
        else:
            _create_seqr_model(xbrowse_model, **kwargs)

    return xbrowse_model, created


def delete_xbrowse_model(xbrowse_model):
    logging.info("delete_xbrowse_model(%s)" % xbrowse_model)
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
        traceback.print_exc()