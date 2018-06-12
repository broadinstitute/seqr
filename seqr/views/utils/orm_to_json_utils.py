"""
Utility functions for converting Django ORM object to JSON
"""

import json
import logging
import os
from django.db.models import Model
from django.db.models.fields.files import ImageFieldFile

from seqr.models import CAN_EDIT, Project, Family, Individual, Sample, Dataset, SavedVariant, VariantTag, \
    VariantFunctionalData, VariantNote
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.utils.json_utils import _to_camel_case
from family_info_utils import retrieve_family_analysed_by
logger = logging.getLogger(__name__)


def _record_to_dict(record, fields, nested_fields=None):
    if isinstance(record, Model):
        model = record
        record = {field[1]: getattr(model, field[0]) for field in fields}
        for nested_field in (nested_fields or []):
            field_value = model
            for field in nested_field:
                field_value = getattr(field_value, field)
            record['_'.join(nested_field)] = field_value
    return record


def _get_record_fields(model_class, model_type, user=None):
    fields = [(field, '{}_{}'.format(model_type, field)) for field in model_class._meta.json_fields]
    if user and user.is_staff:
        internal_fields = getattr(model_class._meta, 'internal_json_fields', [])
        fields += [(field, '{}_{}'.format(model_type, field)) for field in internal_fields]
    return fields


def _get_json_for_record(record, fields):
    return {_to_camel_case(field[0]): record.get(field[1]) for field in fields}


def _get_json_for_user(user):
    """Returns JSON representation of the given User object

    Args:
        user (object): Django user model

    Returns:
        dict: json object
    """

    if hasattr(user, '_wrapped'):
        user = user._wrapped   # Django request.user actually stores the Django User objects in a ._wrapped attribute

    json_obj = {
        key: getattr(user, key)
        for key in ['id', 'username', 'email', 'first_name', 'last_name', 'last_login', 'is_staff', 'is_active', 'date_joined']
    }

    return json_obj


def _get_json_for_project(project, user, add_project_category_guids_field=True):
    """Returns JSON representation of the given Project.

    Args:
        project (object): dictionary or django model for the project
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    fields = _get_record_fields(Project, 'project')
    project_dict = _record_to_dict(project, fields)
    result = _get_json_for_record(project_dict, fields)
    result.update({
        'projectGuid': result.pop('guid'),
        'projectCategoryGuids': [c.guid for c in project.projectcategory_set.all()] if add_project_category_guids_field else [],
        'canEdit': user.is_staff or user.has_perm(CAN_EDIT, project),
    })
    return result


def _get_json_for_families(families, user=None, add_individual_guids_field=False, add_analysed_by_field=True):
    """Returns a JSON representation of the given Family.

    Args:
        families (array): array of dictionaries or django models representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
    Returns:
        array: json objects
    """

    def _get_pedigree_image_url(pedigree_image):
        if isinstance(pedigree_image, ImageFieldFile):
            try:
                pedigree_image = pedigree_image.url
            except Exception:
                pedigree_image = None
        return os.path.join("/media/", pedigree_image) if pedigree_image else None

    fields = _get_record_fields(Family, 'family', user)
    results = []
    for family in families:
        family_dict = _record_to_dict(family, fields, nested_fields=[('project', 'guid')])
        result = _get_json_for_record(family_dict, fields)
        if add_analysed_by_field:
            family_pk = result.pop('id')
            result['analysedBy'] = retrieve_family_analysed_by(family_pk)
        result.update({
            'projectGuid': family_dict['project_guid'],
            'familyGuid': result.pop('guid'),
        })
        pedigree_image = _get_pedigree_image_url(result.pop('pedigreeImage'))
        if pedigree_image:
            result['pedigreeImage'] = pedigree_image
        if add_individual_guids_field:
            result['individualGuids'] = [i.guid for i in family.individual_set.all()]
        results.append(result)

    return results


def _get_json_for_family(family, user=None, add_individual_guids_field=False, add_analysed_by_field=True):
    """Returns a JSON representation of the given Family.

    Args:
        family (object): dictionary or django model representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
    Returns:
        dict: json object
    """

    return _get_json_for_families([family], user, add_individual_guids_field, add_analysed_by_field)[0]


def _get_json_for_individuals(individuals, user=None):
    """Returns a JSON representation for the given list of Individuals.

    Args:
        individuals (array): array of dictionaries or django models for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        array: array of json objects
    """

    def _get_case_review_status_modified_by(modified_by):
        return modified_by.email or modified_by.username if hasattr(modified_by, 'email') else modified_by

    def _load_phenotips_data(phenotips_data):
        phenotips_json = None
        if phenotips_data:
            try:
                phenotips_json = json.loads(phenotips_data)
            except Exception as e:
                logger.error("Couldn't parse phenotips: {}".format(e))
        return phenotips_json

    fields = _get_record_fields(Individual, 'individual', user)

    results = []
    for individual in individuals:
        individual_dict = _record_to_dict(
            individual, fields, nested_fields=[('family', 'project', 'guid'), ('family', 'guid')]
        )

        result = _get_json_for_record(individual_dict, fields)
        result.update({
            'projectGuid': individual_dict.get('family_project_guid') or individual_dict['project_guid'],
            'familyGuid': individual_dict['family_guid'],
            'individualGuid': result.pop('guid'),
            'caseReviewStatusLastModifiedBy': _get_case_review_status_modified_by(result.get('caseReviewStatusLastModifiedBy')),
            'phenotipsData': _load_phenotips_data(result['phenotipsData'])
        })
        results.append(result)
    return results


def _get_json_for_individual(individual, user=None):
    """Returns a JSON representation of the given Individual.

    Args:
        individual (object): dictionary or django model for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    return _get_json_for_individuals([individual], user)[0]


def _get_json_for_sample(sample):
    """Returns a JSON representation of the given Sample.

    Args:
        sample (object): dictionary or django model for the Sample.
    Returns:
        dict: json object
    """

    fields = _get_record_fields(Sample, 'sample')
    sample_dict = _record_to_dict(
        sample, fields, nested_fields=[('individual', 'family', 'project', 'guid'), ('individual', 'guid')]
    )

    result = _get_json_for_record(sample_dict, fields)
    result.update({
        'projectGuid': sample_dict.get('individual_family_project_guid') or sample_dict['project_guid'],
        'individualGuid': sample_dict['individual_guid'],
        'sampleGuid': result.pop('guid'),
    })
    return result


def _get_json_for_dataset(dataset, add_sample_type_field=True):
    """Returns a JSON representation of the given Dataset.

    Args:
        dataset (object): dictionary or django model for the Dataset.
    Returns:
        dict: json object
    """

    fields = _get_record_fields(Dataset, 'dataset')
    dataset_dict = _record_to_dict(dataset, fields, nested_fields=[('project', 'guid')])

    result = _get_json_for_record(dataset_dict, fields)
    if add_sample_type_field:
        result['sampleType'] = dataset_dict['sample_sample_type']
    result.update({
        'projectGuid': dataset_dict['project_guid'],
        'datasetGuid': result.pop('guid'),
    })
    return result


def get_json_for_saved_variant(saved_variant, add_tags=False):
    """Returns a JSON representation of the given variant.

    Args:
        saved_variant (object): dictionary or django model for the SavedVariant.
    Returns:
        dict: json object
    """

    fields = _get_record_fields(SavedVariant, 'variant')
    saved_variant_dict = _record_to_dict(saved_variant, fields, nested_fields=[('family', 'guid')])

    result = _get_json_for_record(saved_variant_dict, fields)

    chrom, pos = get_chrom_pos(result['xpos'])
    lifted_over_xpos = result.pop('liftedOverXposStart')
    lifted_over_chrom, lifted_over_pos = get_chrom_pos(result.pop('liftedOverXposStart')) if lifted_over_xpos else ('', '')

    result.update({
        'variantId': result.pop('guid'),
        'familyGuid': saved_variant_dict['family_guid'],
        'chrom': chrom,
        'pos': pos,
        'liftedOverChrom': lifted_over_chrom,
        'liftedOverPos': lifted_over_pos,
    })
    if add_tags:
        result.update({
            'tags': [get_json_for_variant_tag(tag) for tag in saved_variant.varianttag_set.all()],
            'functionalData': [get_json_for_variant_functional_data(tag) for tag in saved_variant.variantfunctionaldata_set.all()],
            'notes': [get_json_for_variant_note(tag) for tag in saved_variant.variantnote_set.all()],
        })
    return result


def get_json_for_variant_tag(tag):
    """Returns a JSON representation of the given variant tag.

    Args:
        tag (object): dictionary or django model for the VarianTag.
    Returns:
        dict: json object
    """

    fields = _get_record_fields(VariantTag, 'tag')
    tag_dict = _record_to_dict(tag, fields, nested_fields=[
        ('variant_tag_type', 'name'),  ('variant_tag_type', 'category'),  ('variant_tag_type', 'color')
    ])

    result = _get_json_for_record(tag_dict, fields)
    created_by = result.pop('createdBy')
    result.update({
        'tagGuid': result.pop('guid'),
        'name': tag_dict['variant_tag_type_name'],
        'category': tag_dict['variant_tag_type_category'],
        'color': tag_dict['variant_tag_type_color'],
        'createdBy': (created_by.get_full_name() or created_by.email) if created_by else None,
    })
    return result


def get_json_for_variant_functional_data(tag):
    """Returns a JSON representation of the given variant tag.

    Args:
        tag (object): dictionary or django model for the VariantFunctionalData.
    Returns:
        dict: json object
    """

    fields = _get_record_fields(VariantFunctionalData, 'tag')
    tag_dict = _record_to_dict(tag, fields)
    result = _get_json_for_record(tag_dict, fields)

    display_data = json.loads(tag.get_functional_data_tag_display())
    created_by = result.pop('createdBy')
    result.update({
        'tagGuid': result.pop('guid'),
        'name': result.pop('functionalDataTag'),
        'metadataTitle': display_data.get('metadata_title'),
        'color': display_data['color'],
        'createdBy': (created_by.get_full_name() or created_by.email) if created_by else None,
    })
    return result


def get_json_for_variant_note(note):
    """Returns a JSON representation of the given variant note.

    Args:
        note (object): dictionary or django model for the VariantNote.
    Returns:
        dict: json object
    """

    fields = _get_record_fields(VariantNote, 'note')
    note_dict = _record_to_dict(note, fields)
    result = _get_json_for_record(note_dict, fields)

    created_by = result.pop('createdBy')
    result.update({
        'noteGuid': result.pop('guid'),
        'createdBy': (created_by.get_full_name() or created_by.email) if created_by else None,
    })
    return result
