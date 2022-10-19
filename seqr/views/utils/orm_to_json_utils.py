"""
Utility functions for converting Django ORM object to JSON
"""

import json
from collections import defaultdict
from django.db.models import prefetch_related_objects, Prefetch, Count
from django.db.models.fields.files import ImageFieldFile
from django.db.models.functions import Lower
from django.contrib.auth.models import User
from guardian.shortcuts import get_users_with_perms, get_groups_with_perms

from reference_data.models import HumanPhenotypeOntology
from seqr.models import GeneNote, VariantNote, VariantTag, VariantFunctionalData, SavedVariant, CAN_VIEW, CAN_EDIT, \
    get_audit_field_names
from seqr.views.utils.json_utils import _to_camel_case
from seqr.views.utils.permissions_utils import has_project_permissions, has_case_review_permissions, \
    project_has_anvil, get_workspace_collaborator_perms, user_is_analyst, user_is_data_manager, user_is_pm, \
    is_internal_anvil_project, get_project_guids_user_can_view, get_anvil_analyst_user_emails
from seqr.views.utils.terra_api_utils import is_anvil_authenticated, anvil_enabled
from settings import ANALYST_USER_GROUP, SERVICE_ACCOUNT_FOR_ANVIL


def _get_model_json_fields(model_class, user, is_analyst, additional_model_fields):
    fields = set(model_class._meta.json_fields)
    internal_fields = getattr(model_class._meta, 'internal_json_fields', [])
    if internal_fields:
        if is_analyst is None:
            is_analyst = user and user_is_analyst(user)
        if is_analyst:
            fields.update(internal_fields)
    if additional_model_fields:
        fields.update(additional_model_fields)
    audit_fields = [field for field in getattr(model_class._meta, 'audit_fields', set()) if field in fields]
    for audit_field in audit_fields:
        fields.update(get_audit_field_names(audit_field))

    return fields


def _get_json_for_models(models, nested_fields=None, user=None, is_analyst=None, process_result=None, guid_key=None, additional_model_fields=None):
    """Returns an array JSON representations of the given models.

    Args:
        models (array): Array of django models
        user (object): Django User object for determining whether to include restricted/internal-only fields
        nested_fields (array): Optional array of fields to get from the model that are nested on related objects
        process_result (lambda): Optional function to post-process a given model json
        guid_key (string): Optional key to use for the model's guid
    Returns:
        array: json objects
    """

    if not models:
        return []

    model_class = type(models[0])
    fields = _get_model_json_fields(model_class, user, is_analyst, additional_model_fields)
    user_fields = [field for field in fields if field.endswith('last_modified_by') or field == 'created_by']

    for field in user_fields:
        prefetch_related_objects(models, field)
    for nested_field in nested_fields or []:
        if not nested_field.get('value'):
            prefetch_related_objects(models, '__'.join(nested_field['fields'][:-1]))

    results = []
    for model in models:
        result = {_to_camel_case(field): getattr(model, field) for field in fields}
        for nested_field in (nested_fields or []):
            field_value = nested_field.get('value')
            if not field_value:
                field_value = model
                for field in nested_field['fields']:
                    field_value = getattr(field_value, field) if field_value else None

            result[nested_field.get('key', _to_camel_case('_'.join(nested_field['fields'])))] = field_value

        if result.get('guid'):
            guid_key = guid_key or '{}{}Guid'.format(model_class.__name__[0].lower(), model_class.__name__[1:])
            result[guid_key] = result.pop('guid')
        for field in user_fields:
            result_field = _to_camel_case(field)
            if result.get(result_field):
                result[result_field] = result[result_field].get_full_name() or result[result_field].email
        if process_result:
            process_result(result, model)
        results.append(result)

    return results


def _get_json_for_model(model, get_json_for_models=_get_json_for_models, **kwargs):
    """Helper function to return a JSON representations of the given model.

    Args:
        model (object): Django models
        get_json_for_models (lambda): Function used to determine the json for an array of the given model
    Returns:
        object: json object
    """
    return get_json_for_models([model], **kwargs)[0]


def _get_empty_json_for_model(model_class):
    return {_to_camel_case(field): None for field in model_class._meta.json_fields}


MODEL_USER_FIELDS = [
    'username', 'email', 'first_name', 'last_name', 'last_login', 'date_joined', 'id', 'is_superuser', 'is_active',
]
COMPUTED_USER_FIELDS = {
    'display_name': lambda user: user.get_full_name(),
    'is_data_manager': user_is_data_manager,
}


def get_json_for_user(user, fields):
    invalid_fields = [field for field in fields if field not in MODEL_USER_FIELDS and field not in COMPUTED_USER_FIELDS]
    if invalid_fields:
        raise ValueError(f'Invalid user fields: {", ".join(invalid_fields)}')

    return {
        _to_camel_case(field): COMPUTED_USER_FIELDS[field](user) if field in COMPUTED_USER_FIELDS else getattr(user, field)
        for field in fields
    }


def get_json_for_current_user(user):
    user_json = get_json_for_user(user, fields=MODEL_USER_FIELDS + list(COMPUTED_USER_FIELDS.keys()))
    user_json.update({
        'isAnvil': is_anvil_authenticated(user),
        'isAnalyst': user_is_analyst(user),
        'isPm': user_is_pm(user),
    })
    return user_json


def get_json_for_projects(projects, user=None, is_analyst=None, add_project_category_guids_field=True, add_permissions=False):
    """Returns JSON representation of the given Projects.

    Args:
        projects (object array): Django models for the projects
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    def _process_result(result, project):
        result.update({
            'projectCategoryGuids': list(
                project.projectcategory_set.values_list('guid', flat=True)
            ) if add_project_category_guids_field else [],
            'isMmeEnabled': result['isMmeEnabled'] and not result['isDemo'],
            'userIsCreator': project.created_by == user,
            'isAnalystProject': is_internal_anvil_project(project),
        })
        if add_permissions:
            result['canEdit'] = has_project_permissions(project, user, can_edit=True)

    prefetch_related_objects(projects, 'created_by')
    if add_project_category_guids_field:
        prefetch_related_objects(projects, 'projectcategory_set')

    return _get_json_for_models(projects, user=user, is_analyst=is_analyst, process_result=_process_result)


def _get_json_for_project(project, user, **kwargs):
    """Returns JSON representation of the given Project.

    Args:
        project (object): Django model for the project
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    return _get_json_for_model(project, get_json_for_models=get_json_for_projects, user=user, add_permissions=True, **kwargs)


def _get_case_review_fields(model, has_case_review_perm, user, get_project):
    if has_case_review_perm is None:
        has_case_review_perm = user and has_case_review_permissions(get_project(model), user)
    if not has_case_review_perm:
        return []
    return [field.name for field in type(model)._meta.fields if field.name.startswith('case_review')]


def _get_json_for_families(families, user=None, add_individual_guids_field=False, project_guid=None, is_analyst=None, has_case_review_perm=None):
    """Returns a JSON representation of the given Family.

    Args:
        families (array): array of django models representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
        project_guid (boolean): An optional field to use as the projectGuid instead of querying the DB
    Returns:
        array: json objects
    """
    if not families:
        return []

    def _get_pedigree_image_url(pedigree_image):
        if isinstance(pedigree_image, ImageFieldFile):
            try:
                pedigree_image = pedigree_image.url
            except Exception:
                pedigree_image = None
        return pedigree_image

    def _process_result(result, family):
        result['analysedBy'] = _get_json_for_models(family.familyanalysedby_set.all(), user=user, is_analyst=is_analyst)
        pedigree_image = _get_pedigree_image_url(result.pop('pedigreeImage'))
        result['pedigreeImage'] = pedigree_image
        if add_individual_guids_field:
            result['individualGuids'] = [i.guid for i in family.individual_set.all()]
        if not result['displayName']:
            result['displayName'] = result['familyId']
        if result['assignedAnalyst']:
            result['assignedAnalyst'] = {
                'fullName': result['assignedAnalyst'].get_full_name(),
                'email': result['assignedAnalyst'].email,
            }
        else:
            result['assignedAnalyst'] = None

    prefetch_related_objects(families, 'assigned_analyst')
    prefetch_related_objects(families, 'familyanalysedby_set__created_by')
    if add_individual_guids_field:
        prefetch_related_objects(families, 'individual_set')

    kwargs = {'additional_model_fields': _get_case_review_fields(
        families[0], has_case_review_perm, user, lambda family: family.project)
    }
    kwargs.update({'nested_fields': [{'fields': ('project', 'guid'), 'value': project_guid}]})

    return _get_json_for_models(families, user=user, is_analyst=is_analyst, process_result=_process_result, **kwargs)


def _get_json_for_family(family, user=None, **kwargs):
    """Returns a JSON representation of the given Family.

    Args:
        family (object): Django model representing the family.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        add_individual_guids_field (bool): whether to add an 'individualGuids' field. NOTE: this will require a database query.
    Returns:
        dict: json object
    """

    return _get_json_for_model(family, get_json_for_models=_get_json_for_families, user=user, **kwargs)


def get_json_for_family_notes(notes, **kwargs):
    return _get_json_for_models(notes, guid_key='noteGuid', nested_fields=[{'fields': ('family', 'guid')}], **kwargs)


def get_json_for_family_note(note):
    return _get_json_for_model(note, get_json_for_models=get_json_for_family_notes)

def _process_individual_result(add_sample_guids_field):
    def _process_result(result, individual):
        mother = result.pop('mother', None)
        father = result.pop('father', None)

        result.update({
            'maternalGuid': mother.guid if mother else None,
            'paternalGuid': father.guid if father else None,
            'maternalId': mother.individual_id if mother else None,
            'paternalId': father.individual_id if father else None,
            'displayName': result['displayName'] or result['individualId'],
        })

        if add_sample_guids_field:
            result['sampleGuids'] = [s.guid for s in individual.sample_set.all()]
            result['igvSampleGuids'] = [s.guid for s in individual.igvsample_set.all()]
    return _process_result

def _get_json_for_individuals(individuals, user=None, project_guid=None, family_guid=None, add_sample_guids_field=False,
                              family_fields=None, add_hpo_details=False, is_analyst=None, has_case_review_perm=None):
    """Returns a JSON representation for the given list of Individuals.

    Args:
        individuals (array): array of django models for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
        project_guid (string): An optional field to use as the projectGuid instead of querying the DB
        family_guid (boolean): An optional field to use as the familyGuid instead of querying the DB
        add_sample_guids_field (boolean): A flag to indicate weather sample ids should be added
    Returns:
        array: array of json objects
    """

    if not individuals:
        return []

    kwargs = {
        'additional_model_fields': _get_case_review_fields(
            individuals[0], has_case_review_perm, user, lambda indiv: indiv.family.project)
    }
    nested_fields = [
        {'fields': ('family', 'guid'), 'value': family_guid},
        {'fields': ('family', 'project', 'guid'), 'key': 'projectGuid', 'value': project_guid},
    ]
    if family_fields:
        for field in family_fields:
            nested_fields.append({'fields': ('family', field), 'key': _to_camel_case(field)})
    kwargs.update({'nested_fields': nested_fields})

    if add_hpo_details:
        kwargs['additional_model_fields'] += [
            'features', 'absent_features', 'nonstandard_features', 'absent_nonstandard_features']

    prefetch_related_objects(individuals, 'mother')
    prefetch_related_objects(individuals, 'father')
    if add_sample_guids_field:
        prefetch_related_objects(individuals, 'sample_set')
        prefetch_related_objects(individuals, 'igvsample_set')

    parsed_individuals = _get_json_for_models(individuals, user=user, is_analyst=is_analyst, process_result=_process_individual_result(add_sample_guids_field), **kwargs)
    if add_hpo_details:
        _add_individual_hpo_details(parsed_individuals)

    return parsed_individuals


def _add_individual_hpo_details(parsed_individuals):
    all_hpo_ids = set()
    for i in parsed_individuals:
        all_hpo_ids.update([feature['id'] for feature in i.get('features') or []])
        all_hpo_ids.update([feature['id'] for feature in i.get('absentFeatures') or []])
    hpo_terms_by_id = {hpo.hpo_id: hpo for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_hpo_ids)}
    for i in parsed_individuals:
        for feature in i.get('features') or []:
            hpo = hpo_terms_by_id.get(feature['id'])
            if hpo:
                feature.update({'category': hpo.category_id, 'label': hpo.name})
        for feature in i.get('absentFeatures') or []:
            hpo = hpo_terms_by_id.get(feature['id'])
            if hpo:
                feature.update({'category': hpo.category_id, 'label': hpo.name})


def _get_json_for_individual(individual, user=None, **kwargs):
    """Returns a JSON representation of the given Individual.

    Args:
        individual (object): Django model for the individual.
        user (object): Django User object for determining whether to include restricted/internal-only fields
    Returns:
        dict: json object
    """
    return _get_json_for_model(individual, get_json_for_models=_get_json_for_individuals, user=user, **kwargs)


def get_json_for_samples(samples, project_guid=None, family_guid=None, individual_guid=None, skip_nested=False, **kwargs):
    """Returns a JSON representation of the given list of Samples.

    Args:
        samples (array): array of django models for the Samples.
    Returns:
        array: array of json objects
    """

    if project_guid or not skip_nested:
        additional_kwargs = {'nested_fields': [
            {'fields': ('individual', 'guid'), 'value': individual_guid},
            {'fields': ('individual', 'family', 'guid'), 'key': 'familyGuid', 'value': family_guid},
            {'fields': ('individual', 'family', 'project', 'guid'), 'key': 'projectGuid', 'value': project_guid},
        ]}
    else:
        additional_kwargs = {'additional_model_fields': ['individual_id']}

    return _get_json_for_models(samples, guid_key='sampleGuid', **additional_kwargs, **kwargs)


def get_json_for_sample(sample, **kwargs):
    """Returns a JSON representation of the given Sample.

    Args:
        sample (object): Django model for the Sample.
    Returns:
        dict: json object
    """

    return _get_json_for_model(sample, get_json_for_models=get_json_for_samples, **kwargs)


def get_json_for_analysis_groups(analysis_groups, project_guid=None, skip_nested=False, **kwargs):
    """Returns a JSON representation of the given list of AnalysisGroups.

    Args:
        analysis_groups (array): array of django models for the AnalysisGroups.
        project_guid (string): An optional field to use as the projectGuid instead of querying the DB
    Returns:
        array: array of json objects
    """

    def _process_result(result, group):
        result.update({
            'familyGuids': [f.guid for f in group.families.all()]
        })

    prefetch_related_objects(analysis_groups, 'families')

    if project_guid or not skip_nested:
        additional_kwargs = {'nested_fields': [{'fields': ('project', 'guid'), 'value': project_guid}]}
    else:
        additional_kwargs = {'additional_model_fields': ['project_id']}

    return _get_json_for_models(analysis_groups, process_result=_process_result, **additional_kwargs, **kwargs)


def get_json_for_analysis_group(analysis_group, **kwargs):
    """Returns a JSON representation of the given AnalysisGroup.

    Args:
        analysis_group (object): Django model for the AnalysisGroup.
        project_guid (string): An optional field to use as the projectGuid instead of querying the DB
    Returns:
        dict: json object
    """
    return _get_json_for_model(analysis_group, get_json_for_models=get_json_for_analysis_groups, **kwargs)


def get_json_for_saved_variants(saved_variants, add_details=False):
    """Returns a JSON representation of the given variant.
    Args:
        saved_variants (object): Django model for the SavedVariant.
    Returns:
        dict: json object
    """
    def _process_result(variant_json, saved_variant):
        if add_details:
            variant_json.update({k: v for k, v in saved_variant.saved_variant_json.items() if k not in variant_json})
        variant_json['familyGuids'] = [saved_variant.family.guid]
        return variant_json

    prefetch_related_objects(saved_variants, 'family')

    return _get_json_for_models(saved_variants, guid_key='variantGuid', process_result=_process_result)


def get_json_for_saved_variant(saved_variant, **kwargs):
    """Returns a JSON representation of the given variant.

    Args:
        saved_variant (object): Django model for the SavedVariant.
    Returns:
        dict: json object
    """

    return _get_json_for_model(saved_variant, get_json_for_models=get_json_for_saved_variants, **kwargs)


def get_json_for_saved_variants_with_tags(saved_variants, **kwargs):
    variants_by_guid = {
        variant['variantGuid']: dict(tagGuids=[], functionalDataGuids=[], noteGuids=[], **variant)
        for variant in get_json_for_saved_variants(saved_variants, **kwargs)
    }

    saved_variant_id_map = {var.id: var.guid for var in saved_variants}

    variant_tag_id_map = defaultdict(list)
    for tag_mapping in VariantTag.saved_variants.through.objects.filter(savedvariant_id__in=saved_variant_id_map.keys()):
        variant_tag_id_map[tag_mapping.varianttag_id].append(tag_mapping.savedvariant_id)
    tag_models = VariantTag.objects.filter(id__in=variant_tag_id_map.keys())
    tag_id_map = {tag.guid: tag.id for tag in tag_models}

    tags = get_json_for_variant_tags(tag_models, add_variant_guids=False)
    for tag in tags:
        tag_guid = tag['tagGuid']
        tag['variantGuids'] = []
        variant_ids = variant_tag_id_map[tag_id_map[tag_guid]]
        for variant_id in variant_ids:
            variant_guid = saved_variant_id_map[variant_id]
            variants_by_guid[variant_guid]['tagGuids'].append(tag['tagGuid'])
            tag['variantGuids'].append(variant_guid)

    variant_functional_id_map = defaultdict(list)
    for functional_mapping in VariantFunctionalData.saved_variants.through.objects.filter(
            savedvariant_id__in=saved_variant_id_map.keys()):
        variant_functional_id_map[functional_mapping.variantfunctionaldata_id].append(functional_mapping.savedvariant_id)
    functional_models = VariantFunctionalData.objects.filter(id__in=variant_functional_id_map.keys())
    functional_id_map = {tag.guid: tag.id for tag in functional_models}

    functional_data = get_json_for_variant_functional_data_tags(functional_models, add_variant_guids=False)
    for tag in functional_data:
        tag_guid = tag['tagGuid']
        tag['variantGuids'] = []
        variant_ids = variant_functional_id_map[functional_id_map[tag_guid]]
        for variant_id in variant_ids:
            variant_guid = saved_variant_id_map[variant_id]
            variants_by_guid[variant_guid]['functionalDataGuids'].append(tag['tagGuid'])
            tag['variantGuids'].append(variant_guid)

    variant_note_id_map = defaultdict(list)
    for note_mapping in VariantNote.saved_variants.through.objects.filter(savedvariant_id__in=saved_variant_id_map.keys()):
        variant_note_id_map[note_mapping.variantnote_id].append(note_mapping.savedvariant_id)
    note_models = VariantNote.objects.filter(id__in=variant_note_id_map.keys())
    note_id_map = {note.guid: note.id for note in note_models}

    notes = get_json_for_variant_notes(note_models, add_variant_guids=False)
    for note in notes:
        note_guid = note['noteGuid']
        note['variantGuids'] = []
        variant_ids = variant_note_id_map[note_id_map[note_guid]]
        for variant_id in variant_ids:
            variant_guid = saved_variant_id_map[variant_id]
            variants_by_guid[variant_guid]['noteGuids'].append(note['noteGuid'])
            note['variantGuids'].append(variant_guid)

    response = {
        'variantTagsByGuid': {tag['tagGuid']: tag for tag in tags},
        'variantNotesByGuid': {note['noteGuid']: note for note in notes},
        'variantFunctionalDataByGuid': {tag['tagGuid']: tag for tag in functional_data},
        'savedVariantsByGuid': variants_by_guid,
    }

    return response


def get_json_for_discovery_tags(variants, user):
    from seqr.views.utils.variant_utils import get_variant_key
    response = {}
    discovery_tags = defaultdict(list)

    tag_models = VariantTag.objects.filter(
        variant_tag_type__category='CMG Discovery Tags',
        saved_variants__variant_id__in={variant['variantId'] for variant in variants},
        saved_variants__family__project__guid__in=get_project_guids_user_can_view(user),
    )
    if tag_models:
        discovery_tag_json = get_json_for_variant_tags(tag_models, add_variant_guids=False)

        tag_id_map = {tag.guid: tag.id for tag in tag_models}
        variant_tag_id_map = defaultdict(list)
        variant_ids = set()
        for tag_mapping in VariantTag.saved_variants.through.objects.filter(
                varianttag_id__in=tag_id_map.values()):
            variant_tag_id_map[tag_mapping.varianttag_id].append(tag_mapping.savedvariant_id)
            variant_ids.add(tag_mapping.savedvariant_id)
        saved_variants_by_id = {var.id: var for var in SavedVariant.objects.filter(id__in=variant_ids).only(
            'guid', 'ref', 'alt', 'xpos', 'family_id').prefetch_related('family', 'family__project')
        }

        existing_families = set()
        for variant in variants:
            existing_families.update(variant['familyGuids'])

        families = set()
        for tag in discovery_tag_json:
            for variant_id in variant_tag_id_map[tag_id_map[tag['tagGuid']]]:
                variant = saved_variants_by_id[variant_id]
                if variant.family.guid not in existing_families:
                    families.add(variant.family)
                tag_json = {'savedVariant': {
                    'variantGuid': variant.guid,
                    'familyGuid': variant.family.guid,
                    'projectGuid': variant.family.project.guid,
                }}
                tag_json.update(tag)
                variant_key = get_variant_key(
                    genomeVersion=variant.family.project.genome_version,
                    xpos=variant.xpos, ref=variant.ref, alt=variant.alt,
                )
                discovery_tags[variant_key].append(tag_json)

        response['familiesByGuid'] = {f['familyGuid']: f for f in _get_json_for_families(list(families))}
    return discovery_tags, response


def get_json_for_variant_tags(tags, add_variant_guids=True):
    """Returns a JSON representation of the given variant tags.

    Args:
        tag (object): Django models for the VariantTag.
    Returns:
        dict: json objects
    """
    def _process_result(tag_json, tag):
        if add_variant_guids:
            tag_json['variantGuids'] = [variant.guid for variant in tag.saved_variants.all()]

    if add_variant_guids:
        prefetch_related_objects(tags, Prefetch('saved_variants', queryset=SavedVariant.objects.only('guid')))

    nested_fields = [{'fields': ('variant_tag_type', field), 'key': field} for field in ['name', 'category', 'color']]
    return _get_json_for_models(tags, nested_fields=nested_fields, guid_key='tagGuid', process_result=_process_result)


def get_json_for_variant_functional_data_tags(tags, add_variant_guids=True):
    """Returns a JSON representation of the given variant tags.

    Args:
        tags (object): Django models for the VariantFunctionalData.
    Returns:
        dict: json objects
    """

    def _process_result(tag_json, tag):
        display_data = json.loads(tag.get_functional_data_tag_display())
        tag_json.update({
            'name': tag_json.pop('functionalDataTag'),
            'metadataTitle': display_data.get('metadata_title', 'Notes'),
            'color': display_data['color'],
        })
        if add_variant_guids:
            tag_json['variantGuids'] = [variant.guid for variant in tag.saved_variants.all()]

    if add_variant_guids:
        prefetch_related_objects(tags, Prefetch('saved_variants', queryset=SavedVariant.objects.only('guid')))

    return _get_json_for_models(tags, guid_key='tagGuid', process_result=_process_result)


def get_json_for_variant_notes(notes, add_variant_guids=True):
    """Returns a JSON representation of the given variant notes.

    Args:
        notes (object): Django model for the VariantNote.
    Returns:
        dict: json objects
    """
    def _process_result(note_json, note):
        if add_variant_guids:
            note_json['variantGuids'] = [variant.guid for variant in note.saved_variants.all()]

    if add_variant_guids:
        prefetch_related_objects(notes, Prefetch('saved_variants', queryset=SavedVariant.objects.only('guid')))

    return _get_json_for_models(notes, guid_key='noteGuid', process_result=_process_result)


def get_json_for_variant_note(note, **kwargs):
    """Returns a JSON representation of the given variant note.

    Args:
        note (object): Django model for the VariantNote.
    Returns:
        dict: json object
    """

    return _get_json_for_model(note, get_json_for_models=get_json_for_variant_notes, **kwargs)


def get_json_for_gene_notes(notes, user):
    """Returns a JSON representation of the given gene note.

    Args:
        note (object): Django model for the GeneNote.
    Returns:
        dict: json object
    """

    return _get_json_for_models(notes, user=user, guid_key='noteGuid')


def get_json_for_gene_notes_by_gene_id(gene_ids, user):
    """Returns a JSON representation of the gene notes for the given gene ids.

    Args:
        note (object): Django model for the GeneNote.
    Returns:
        dict: json object
    """
    notes_by_gene_id = defaultdict(list)
    for note in get_json_for_gene_notes(GeneNote.objects.filter(gene_id__in=gene_ids), user):
        notes_by_gene_id[note['geneId']].append(note)
    return notes_by_gene_id


def get_json_for_locus_lists(locus_lists, user, include_genes=False, include_pagenes=False, include_project_count=False,
                             is_analyst=False, include_metadata=True):
    """Returns a JSON representation of the given LocusLists.

    Args:
        locus_lists (array): array of LocusList django models.
    Returns:
        array: json objects
    """

    def _process_result(result, locus_list):
        gene_set = locus_list.locuslistgene_set
        interval_set = locus_list.locuslistinterval_set
        if include_genes:
            intervals = _get_json_for_models(interval_set.all())
            genome_versions = {interval['genomeVersion'] for interval in intervals}

            if include_pagenes:
                result.update({
                    'items': [{
                        'geneId': gene.gene_id,
                        'pagene': _get_json_for_model(gene.palocuslistgene, user=user, is_analyst=is_analyst)
                        if hasattr(gene, 'palocuslistgene') else None
                    } for gene in gene_set.all()] + intervals,
                })
            else:
                result.update({
                    'items': [{'geneId': gene.gene_id} for gene in gene_set.all()] + intervals,
                })
            result.update({
                'intervalGenomeVersion': genome_versions.pop() if len(genome_versions) == 1 else None,
            })

        if include_project_count:
            result['numProjects'] = locus_list.num_projects

        if include_metadata:
            result.update({
                'numEntries': gene_set.count() + interval_set.count()
                if include_genes else locus_list.locuslistgene__count + locus_list.locuslistinterval__count,
                'canEdit': user == locus_list.created_by,
            })

        if hasattr(locus_list, 'palocuslist'):
            pa_locus_list_json = _get_json_for_model(locus_list.palocuslist, user=user, is_analyst=is_analyst)
            result.update({
                'paLocusList': pa_locus_list_json,
            })

    if include_metadata:
        prefetch_related_objects(locus_lists, 'created_by')

    if include_genes:
        prefetch_related_objects(locus_lists, 'locuslistgene_set')
        prefetch_related_objects(locus_lists, 'locuslistinterval_set')
    elif include_metadata:
        locus_lists = locus_lists.annotate(Count('locuslistgene')).annotate(Count('locuslistinterval'))

    prefetch_related_objects(locus_lists, 'palocuslist')

    if include_pagenes:
        prefetch_related_objects(locus_lists, 'locuslistgene_set__palocuslistgene')

    return _get_json_for_models(locus_lists, user=user, is_analyst=is_analyst, process_result=_process_result)


def get_json_for_locus_list(locus_list, user):
    """Returns a JSON representation of the given LocusList.

    Args:
        locus_list (object): LocusList django model.
    Returns:
        dict: json object
    """
    return _get_json_for_model(locus_list, get_json_for_models=get_json_for_locus_lists, user=user, include_genes=True,
                               include_pagenes=True)


PROJECT_ACCESS_GROUP_NAMES = ['_owners', '_can_view', '_can_edit']


def get_json_for_project_collaborator_groups(project):
    if anvil_enabled():
        return None
    group_json = [
        _get_collaborator_json(
            group, fields=['name'], include_permissions=True, can_edit=CAN_EDIT in perms,
            get_json_func=lambda g, fields: {field: getattr(g, field) for field in fields},
        )
        for group, perms in get_groups_with_perms(project, attach_perms=True).items()
        if not any(substring in group.name for substring in PROJECT_ACCESS_GROUP_NAMES)
    ]
    return sorted(group_json, key=lambda group: (not group['hasEditPermissions'], group['name'].lower()))


def get_json_for_project_collaborator_list(user, project):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborator_list = list(
        get_project_collaborators_by_username(
            user, project, fields=['username', 'email', 'display_name'], include_permissions=True,
        ).values())

    return sorted(collaborator_list, key=lambda collaborator: (
        not collaborator['hasEditPermissions'], (collaborator['displayName'] or collaborator['email']).lower()))


def get_project_collaborators_by_username(user, project, fields, include_permissions=False, expand_user_groups=False):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborators = {}
    if not anvil_enabled():
        if expand_user_groups:
            collaborator_perms = get_users_with_perms(project, attach_perms=True)
        else:
            collaborator_perms = {collab: [CAN_VIEW] for collab in project.can_view_group.user_set.all()}
            for collab in project.can_edit_group.user_set.all():
                collaborator_perms[collab].append(CAN_EDIT)

        for collaborator, perms in collaborator_perms.items():
            collaborators[collaborator.username] = _get_collaborator_json(
                collaborator, fields, include_permissions, can_edit=CAN_EDIT in perms)

    elif project_has_anvil(project):
        permission_levels = get_workspace_collaborator_perms(user, project.workspace_namespace, project.workspace_name)
        analyst_email = f'{ANALYST_USER_GROUP}@firecloud.org'.lower()
        if expand_user_groups and analyst_email in permission_levels:
            analyst_permission = permission_levels.pop(analyst_email)
            permission_levels.update({email.lower(): analyst_permission for email in get_anvil_analyst_user_emails(user)})

        users_by_email = {u.email_lower: u for u in User.objects.annotate(email_lower=Lower('email')).filter(email_lower__in=permission_levels.keys())}
        for email, permission in permission_levels.items():
            if email == SERVICE_ACCOUNT_FOR_ANVIL:
                continue
            collaborator = users_by_email.get(email)
            collaborator_json = _get_collaborator_json(
                collaborator or email, fields, include_permissions, can_edit=permission == CAN_EDIT,
                get_json_func=get_json_for_user if collaborator else _get_anvil_user_json)
            collaborators[collaborator_json['username']] = collaborator_json

    return collaborators


def _get_anvil_user_json(collaborator, fields):
    user = {_to_camel_case(field): '' for field in fields}
    user.update({field: collaborator for field in ['username', 'email']})
    return user


def _get_collaborator_json(collaborator, fields, include_permissions, can_edit, get_json_func=get_json_for_user):
    collaborator_json = get_json_func(collaborator, fields)
    return _set_collaborator_permissions(collaborator_json, include_permissions, can_edit)


def _set_collaborator_permissions(collaborator_json, include_permissions, can_edit):
    if include_permissions:
        collaborator_json.update({
            'hasViewPermissions': True,
            'hasEditPermissions': can_edit,
        })
    return collaborator_json


def get_json_for_saved_searches(searches, user):
    is_analyst = user_is_analyst(user)
    def _process_result(result, search):
        # Do not apply HGMD filters in shared searches for non-analyst users
        if not search.created_by and not is_analyst and result['search'].get('pathogenicity', {}).get('hgmd'):
            result['search']['pathogenicity'] = {
                k: v for k, v in result['search']['pathogenicity'].items() if k != 'hgmd'
            }
    prefetch_related_objects(searches, 'created_by')
    return _get_json_for_models(searches, guid_key='savedSearchGuid', process_result=_process_result)


def get_json_for_saved_search(search, user):
    return _get_json_for_model(search, user=user, get_json_for_models=get_json_for_saved_searches)


def get_json_for_matchmaker_submissions(models, individual_guid=None, additional_model_fields=None, all_parent_guids=False):
    nested_fields = [{'fields': ('individual', 'guid'), 'value': individual_guid}]
    if all_parent_guids:
        nested_fields += [
            {'fields': ('individual', 'individual_id'), 'key': 'individualId'},
            {'fields': ('individual', 'family', 'guid'), 'key': 'familyGuid'},
            {'fields': ('individual', 'family', 'project', 'guid'), 'key': 'projectGuid'},
        ]
    return _get_json_for_models(
        models, nested_fields=nested_fields, guid_key='submissionGuid', additional_model_fields=additional_model_fields
    )


def get_json_for_matchmaker_submission(submission):
    return _get_json_for_model(
        submission, get_json_for_models=get_json_for_matchmaker_submissions, individual_guid=submission.individual.guid,
        additional_model_fields=['contact_name', 'contact_href', 'submission_id'])


def get_json_for_rna_seq_outliers(models, **kwargs):
    def _process_result(data, model):
        data['isSignificant'] = data['pAdjust'] < model.SIGNIFICANCE_THRESHOLD

    return _get_json_for_models(models, process_result=_process_result, **kwargs)
