import logging
import traceback

from django.db.models.query_utils import Q
from django.utils import timezone

from seqr.views.utils.json_utils import _to_snake_case
from xbrowse_server.base.models import Project as BaseProject, Family as BaseFamily, Individual as BaseIndividual, \
    ProjectTag as BaseProjectTag, VariantTag as BaseVariantTag, VariantNote as BaseVariantNote, \
    VariantFunctionalData as BaseVariantFunctionalData, GeneNote as BaseGeneNote
from xbrowse_server.gene_lists.models import GeneList as BaseGeneList, GeneListItem as BaseGeneListItem

SEQR_TO_XBROWSE_CLASS_MAPPING = {
    "Project": BaseProject,
    "Family": BaseFamily,
    "Individual": BaseIndividual,
    "VariantTagType": BaseProjectTag,
    "VariantTag": BaseVariantTag,
    "VariantFunctionalData": BaseVariantFunctionalData,
    "VariantNote": BaseVariantNote,
    "LocusList": BaseGeneList,
    "LocusListGene": BaseGeneListItem,
    "GeneNote": BaseGeneNote,
}

_DELETED_FIELD = "__DELETED__"

SEQR_TO_XBROWSE_FIELD_MAPPING = {
    "Project": {
        "name": "project_name",
        'deprecated_project_id': 'project_id',
        'deprecated_last_accessed_date': 'last_accessed_date',
    },
    "Family": {
        "display_name": "family_name",
        "description": "short_description",
        "analysis_notes": "about_family_content",
        "analysis_summary": "analysis_summary_content",
    },
    "Individual": {
        "individual_id": "indiv_id",
        "sex": "gender",
        "display_name": "nickname",
        "phenotips_eid": "phenotips_id",
        "notes": "other_notes",
    },
    "VariantTagType": {
        "name": "tag",
        "description": "title",
    },
    "SavedVariant": {
        "xpos_start": "xpos",
    },
    "VariantTag": {
        "variant_tag_type": "project_tag",
        "created_by": "user",
        "search_parameters": "search_url",
    },
    "VariantNote": {
        "created_by": "user",
        "search_parameters": "search_url",
    },
    "VariantFunctionalData": {
        "created_by": "user",
        "search_parameters": "search_url",
    },
    "LocusList": {
        "created_by": "owner",
        "last_modified_by": "last_updated",
    },
    "LocusListGene": {
        "locus_list": "gene_list",
        "created_by": _DELETED_FIELD,
    },
    "GeneNote": {
        "created_by": "user",
    },
}

FLATTENED_MODEL_FIELDS = {
    'VariantTag': {
        'saved_variant': ['xpos_start', 'ref', 'alt', 'family']
    },
    'VariantFunctionalData': {
        'saved_variant': ['xpos_start', 'ref', 'alt', 'family']
    },
    'VariantNote': {
        'saved_variant': ['xpos_start', 'ref', 'alt', 'family', 'project']
    },
}


def _update_model(model_obj, **kwargs):
    for field, value in kwargs.items():
        setattr(model_obj, field, value)

    model_obj.save()


def _is_seqr_model(obj):
    return type(obj).__module__ == "seqr.models"


def find_matching_xbrowse_model(seqr_model):
    logging.info("find matching xbrowse %s for %s" % (type(seqr_model).__name__, seqr_model))
    if not _is_seqr_model(seqr_model):
        raise ValueError("Unexpected model class: %s.%s" % (type(seqr_model).__module__, type(seqr_model).__name__))

    try:
        seqr_class_name = type(seqr_model).__name__

        if seqr_class_name == "Project":
            return BaseProject.objects.get(
                Q(seqr_project=seqr_model) |
                (Q(seqr_project__isnull=True) &
                 Q(project_id=seqr_model.deprecated_project_id)))
        elif seqr_class_name == "Family":
            return BaseFamily.objects.get(
                Q(seqr_family=seqr_model) |
                (Q(seqr_family__isnull=True) &
                 Q(project__project_id=seqr_model.project.deprecated_project_id) &
                 Q(family_id=seqr_model.family_id)))
        elif seqr_class_name == "Individual":
            return BaseIndividual.objects.get(
                Q(seqr_individual=seqr_model) |
                (Q(seqr_individual__isnull=True) &
                 Q(family__project__project_id=seqr_model.family.project.deprecated_project_id) &
                 Q(family__family_id=seqr_model.family.family_id) &
                 Q(indiv_id=seqr_model.individual_id)))
        elif seqr_class_name == "VariantTagType":
            return BaseProjectTag.objects.get(
                Q(project__project_id=seqr_model.project.deprecated_project_id) &
                (Q(seqr_variant_tag_type=seqr_model) |
                 Q(seqr_variant_tag_type__isnull=True,
                   tag=seqr_model.name,
                   category=seqr_model.category,
                   project__project_id=seqr_model.project.deprecated_project_id))
                )
        elif seqr_class_name == "VariantTag":
            match_filter = Q(
                seqr_variant_tag__isnull=True,
                project_tag__project__project_id=seqr_model.saved_variant.project.deprecated_project_id,
                project_tag__tag=seqr_model.variant_tag_type.name,
                xpos=seqr_model.saved_variant.xpos_start,
                ref=seqr_model.saved_variant.ref,
                alt=seqr_model.saved_variant.alt
            )
            if seqr_model.saved_variant.family:
                match_filter &= Q(
                    family__family_id=seqr_model.saved_variant.family.family_id,
                )
            return BaseVariantTag.objects.get(Q(seqr_variant_tag=seqr_model) | match_filter)
        elif seqr_class_name == "VariantFunctionalData":
            match_filter = Q(
                seqr_variant_functional_data__isnull=True,
                functional_data_tag=seqr_model.functional_data_tag,
                xpos=seqr_model.saved_variant.xpos_start,
                ref=seqr_model.saved_variant.ref,
                alt=seqr_model.saved_variant.alt
            )
            if seqr_model.saved_variant.family:
                match_filter &= Q(
                    family__family_id=seqr_model.saved_variant.family.family_id,
                    family__project__project_id=seqr_model.saved_variant.project.deprecated_project_id,
                )
            return BaseVariantFunctionalData.objects.get(Q(seqr_variant_functional_data=seqr_model) | match_filter)
        elif seqr_class_name == "VariantNote":
            match_filter = Q(
                seqr_variant_note__isnull=True,
                note=seqr_model.note,
                project__project_id=seqr_model.saved_variant.project.deprecated_project_id,
                xpos=seqr_model.saved_variant.xpos_start,
                ref=seqr_model.saved_variant.ref,
                alt=seqr_model.saved_variant.alt
            )
            if seqr_model.saved_variant.family:
                match_filter &= Q(family__family_id=seqr_model.saved_variant.family.family_id)
            return BaseVariantNote.objects.get(Q(seqr_variant_note=seqr_model) | match_filter)
        elif seqr_class_name == "LocusList":
            return BaseGeneList.objects.get(
                Q(seqr_locus_list=seqr_model) |
                (Q(seqr_locus_list__isnull=True) &
                 Q(name=seqr_model.name) &
                 Q(description=seqr_model.description) &
                 Q(owner=seqr_model.created_by) &
                 Q(is_public=seqr_model.is_public)))
        elif seqr_class_name == "LocusListGene":
            return BaseGeneListItem.objects.get(
                gene_list=find_matching_xbrowse_model(seqr_model.locus_list),
                description=seqr_model.description or '',
                gene_id=seqr_model.gene_id)
        elif seqr_class_name == "GeneNote":
            return BaseGeneNote.objects.get(
                note=seqr_model.note,
                gene_id=seqr_model.gene_id,
            )
    except Exception as e:
        logging.error("ERROR: when looking up xbrowse model for seqr %s model: %s" % (seqr_model, e))
        #traceback.print_exc()

    return None


def convert_seqr_kwargs_to_xbrowse_kwargs(seqr_model, **kwargs):
    # rename fields
    seqr_class_name = type(seqr_model).__name__
    field_mapping = SEQR_TO_XBROWSE_FIELD_MAPPING[seqr_class_name]
    xbrowse_kwargs = {
        field_mapping.get(field, field): value for field, value in kwargs.items()
        if not field_mapping.get(field, field) == _DELETED_FIELD
    }

    if seqr_class_name == "Individual" and "family" in xbrowse_kwargs:
        xbrowse_kwargs["project"] = getattr(seqr_model, "family").project

    if seqr_class_name == "LocusList" and 'name' in xbrowse_kwargs:
        xbrowse_kwargs['slug'] = xbrowse_kwargs['name'].replace(' ', '-').lower()

    # handle foreign keys
    for key, value in xbrowse_kwargs.items():
        if _is_seqr_model(value):
            if key in FLATTENED_MODEL_FIELDS.get(seqr_class_name, {}):
                nested_model_kwargs = {k: getattr(value, k, None) for k in FLATTENED_MODEL_FIELDS[seqr_class_name][key]}
                xbrowse_kwargs.update(convert_seqr_kwargs_to_xbrowse_kwargs(value, **nested_model_kwargs))
                del xbrowse_kwargs[key]
            else:
                if key == 'project_tag':
                    value.project = seqr_model.saved_variant.project
                new_value = find_matching_xbrowse_model(value)
                if new_value is not None:
                    xbrowse_kwargs[key] = new_value
                else:
                    logging.info("ERROR: unable to find equivalent seqr model for %s: %s" % (key, value))
                    del xbrowse_kwargs[key]

    # Explicitly add timestamps
    xbrowse_model_class = SEQR_TO_XBROWSE_CLASS_MAPPING.get(seqr_class_name)
    for timestamp_key in ['date_saved', 'last_updated']:
        if xbrowse_model_class and hasattr(xbrowse_model_class, timestamp_key) and timestamp_key not in xbrowse_kwargs:
            xbrowse_kwargs[timestamp_key] = timezone.now()

    return xbrowse_kwargs


def update_seqr_model(seqr_model, **kwargs):
    logging.info("update_seqr_model(%s, %s)" % (seqr_model, kwargs))
    xbrowse_model = find_matching_xbrowse_model(seqr_model)
    _update_model(seqr_model, **kwargs)

    if not xbrowse_model:
        return

    xbrowse_kwargs = convert_seqr_kwargs_to_xbrowse_kwargs(seqr_model, **kwargs)

    _update_model(xbrowse_model, **xbrowse_kwargs)


def _create_xbrowse_model(seqr_model, **kwargs):
    try:
        seqr_model_class = seqr_model.__class__
        seqr_model_class_name = seqr_model_class.__name__
        xbrowse_kwargs = convert_seqr_kwargs_to_xbrowse_kwargs(seqr_model, **kwargs)
        xbrowse_model_class = SEQR_TO_XBROWSE_CLASS_MAPPING[seqr_model_class_name]
        xbrowse_model_class_name = xbrowse_model_class.__name__
        logging.info("_create_xbrowse_model(%s, %s)" % (xbrowse_model_class_name, xbrowse_kwargs))
        xbrowse_model = xbrowse_model_class.objects.create(**xbrowse_kwargs)

        seqr_model_foreign_key_name = "seqr_"+_to_snake_case(seqr_model_class_name)
        if hasattr(xbrowse_model, seqr_model_foreign_key_name):
            setattr(xbrowse_model, seqr_model_foreign_key_name, seqr_model)
            xbrowse_model.save()
        return xbrowse_model

    except Exception as e:
        logging.error("ERROR: error when creating xbrowse model %s: %s" % (seqr_model, e))
        traceback.print_exc()
        return None


def create_seqr_model(seqr_model_class, **kwargs):
    logging.info("create_seqr_model(%s, %s)" % (seqr_model_class.__name__, kwargs))
    seqr_model = seqr_model_class.objects.create(**kwargs)
    _create_xbrowse_model(seqr_model, **kwargs)

    return seqr_model


def get_or_create_seqr_model(seqr_model_class, **kwargs):
    logging.info("get_or_create_seqr_model(%s, %s)" % (seqr_model_class, kwargs))
    seqr_model, created = seqr_model_class.objects.get_or_create(**kwargs)

    xbrowse_model = find_matching_xbrowse_model(seqr_model)
    if created or xbrowse_model is None:
        if xbrowse_model is not None:
            logging.error("ERROR: created seqr model: %s while xbrowse model already exists: %s" % (seqr_model, xbrowse_model))
        elif seqr_model_class.__name__ not in SEQR_TO_XBROWSE_CLASS_MAPPING:
            logging.error("ERROR: create operation not implemented for seqr model: %s" % (seqr_model_class.__name__))
        else:
            _create_xbrowse_model(seqr_model, **kwargs)

    return seqr_model, created


def delete_seqr_model(seqr_model):
    logging.info("delete_seqr_model(%s)" % seqr_model)
    xbrowse_model = find_matching_xbrowse_model(seqr_model)
    seqr_model.delete()

    if xbrowse_model:
        try:
            xbrowse_model.delete()
        except Exception as e:
            logging.error("ERROR: error when deleting seqr model %s: %s" % (seqr_model, e))
            traceback.print_exc()
