"""
Utility functions for converting Django ORM object to JSON
"""

from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import prefetch_related_objects, Count, Value, F, Q, CharField, Case, When
from django.db.models.functions import Concat, Coalesce, NullIf, Lower, Trim, JSONObject
from django.contrib.auth.models import User
from guardian.shortcuts import get_users_with_perms, get_groups_with_perms

from panelapp.models import PaLocusList
from reference_data.models import HumanPhenotypeOntology
from seqr.models import GeneNote, VariantNote, VariantTag, VariantFunctionalData, SavedVariant, Family, CAN_VIEW, CAN_EDIT, \
    get_audit_field_names, RnaSeqOutlier, RnaSeqSpliceOutlier
from seqr.views.utils.json_utils import _to_camel_case
from seqr.views.utils.permissions_utils import has_project_permissions, \
    project_has_anvil, get_workspace_collaborator_perms, user_is_analyst, user_is_data_manager, user_is_pm, \
    is_internal_anvil_project, get_project_guids_user_can_view, get_anvil_analyst_user_emails
from seqr.views.utils.terra_api_utils import is_anvil_authenticated, anvil_enabled
from settings import ANALYST_USER_GROUP, SERVICE_ACCOUNT_FOR_ANVIL, MEDIA_URL


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
                    field_value = getattr(field_value, field, None) if field_value else None

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


def _full_name_expr(field):
    return Trim(Concat(f'{field}__first_name', Value(' '), f'{field}__last_name'))


def _user_expr(field):
    return Coalesce(NullIf(_full_name_expr(field), Value('')), f'{field}__email', output_field=CharField())


def get_json_for_queryset(models, nested_fields=None, user=None, is_analyst=None, additional_values=None, guid_key=None, additional_model_fields=None):
    model_class = models.model
    fields = _get_model_json_fields(model_class, user, is_analyst, additional_model_fields)

    field_key_map = {_to_camel_case(field): field for field in fields}
    if 'guid' in field_key_map:
        guid_key = guid_key or '{}{}Guid'.format(model_class.__name__[0].lower(), model_class.__name__[1:])
        field_key_map[guid_key] = field_key_map.pop('guid')

    no_modify_fields = [field for key, field in field_key_map.items() if key == field]
    value_fields = {key: F(field) for key, field in field_key_map.items() if key != field}
    value_fields.update({
        key: _user_expr(field) for key, field in field_key_map.items()
        if field.endswith('last_modified_by') or field == 'created_by'
    })
    value_fields.update(additional_values or {})

    for nested_field in (nested_fields or []):
        key = nested_field.get('key', _to_camel_case('_'.join(nested_field['fields'])))
        value_fields[key] = Value(nested_field['value']) if nested_field.get('value') else F('__'.join(nested_field['fields']))

    return models.values(*no_modify_fields, **value_fields)


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
            'isMmeEnabled': result['isMmeEnabled'] and not result['isDemo'],
            'userIsCreator': project.created_by == user,
            'isAnalystProject': is_internal_anvil_project(project),
        })
        if add_permissions:
            result['canEdit'] = has_project_permissions(project, user, can_edit=True)
        if add_project_category_guids_field:
            result['projectCategoryGuids'] = list(project.projectcategory_set.values_list('guid', flat=True))

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


def _get_case_review_fields(model_cls, has_case_review_perm):
    if not has_case_review_perm:
        return []
    return [field.name for field in model_cls._meta.fields if field.name.startswith('case_review')]


FAMILY_DISPLAY_NAME_EXPR = Coalesce(NullIf('display_name', Value('')), 'family_id')


def _get_json_for_families(families, user=None, add_individual_guids_field=False, project_guid=None, is_analyst=None,
                           has_case_review_perm=False, additional_values=None):

    family_additional_values = {
        'analysedBy': ArrayAgg(JSONObject(
            createdBy=_user_expr('familyanalysedby__created_by'),
            dataType='familyanalysedby__data_type',
            lastModifiedDate='familyanalysedby__last_modified_date',
        ), filter=Q(familyanalysedby__isnull=False)),
        'assignedAnalyst': Case(
            When(assigned_analyst__isnull=False, then=JSONObject(
                fullName=_full_name_expr('assigned_analyst'), email=F('assigned_analyst__email'),
            )), default=Value(None),
        ),
        'displayName': FAMILY_DISPLAY_NAME_EXPR,
        'pedigreeImage': NullIf(Concat(Value(MEDIA_URL), 'pedigree_image', output_field=CharField()), Value(MEDIA_URL)),
    }
    if additional_values:
        family_additional_values.update(additional_values)
    if add_individual_guids_field:
        family_additional_values['individualGuids'] = ArrayAgg('individual__guid', filter=Q(individual__isnull=False), distinct=True)

    additional_model_fields = _get_case_review_fields(families.model, has_case_review_perm)
    nested_fields = [{'fields': ('project', 'guid'), 'value': project_guid}]

    return get_json_for_queryset(families, user=user, is_analyst=is_analyst, additional_values=family_additional_values,
                                 additional_model_fields=additional_model_fields, nested_fields=nested_fields)


FAMILY_NOTE_KWARGS = dict(guid_key='noteGuid', nested_fields=[{'fields': ('family', 'guid')}])


def get_json_for_family_notes(notes, **kwargs):
    return get_json_for_queryset(notes, **FAMILY_NOTE_KWARGS, **kwargs)


def get_json_for_family_note(note):
    return _get_json_for_model(note, **FAMILY_NOTE_KWARGS)


INDIVIDUAL_DISPLAY_NAME_EXPR = Coalesce(NullIf('display_name', Value('')), 'individual_id', output_field=CharField())


def _get_json_for_individuals(individuals, user=None, project_guid=None, family_guid=None, add_sample_guids_field=False,
                              family_fields=None, add_hpo_details=False, is_analyst=None, has_case_review_perm=False):
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

    additional_model_fields = _get_case_review_fields(individuals.model, has_case_review_perm)
    nested_fields = [
        {'fields': ('family', 'guid'), 'value': family_guid},
        {'fields': ('family', 'project', 'guid'), 'key': 'projectGuid', 'value': project_guid},
    ]
    if family_fields:
        for field in family_fields:
            nested_fields.append({'fields': ('family', field), 'key': _to_camel_case(field)})

    if add_hpo_details:
        additional_model_fields += [
            'features', 'absent_features', 'nonstandard_features', 'absent_nonstandard_features']

    additional_values = {
        'maternalGuid': F('mother__guid'),
        'paternalGuid': F('father__guid'),
        'maternalId': F('mother__individual_id'),
        'paternalId': F('father__individual_id'),
        'displayName': INDIVIDUAL_DISPLAY_NAME_EXPR,
    }
    if add_sample_guids_field:
        additional_values.update({
            f'{field}Guids': ArrayAgg(f'{field.lower()}__guid', filter=Q(**{f'{field.lower()}__isnull': False}))
            for field in ['sample', 'igvSample']
        })

    parsed_individuals = get_json_for_queryset(
        individuals, user=user, is_analyst=is_analyst, additional_values=additional_values,
        additional_model_fields=additional_model_fields, nested_fields=nested_fields,
    )

    if add_hpo_details:
        add_individual_hpo_details(parsed_individuals)

    return parsed_individuals


def add_individual_hpo_details(parsed_individuals):
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


def get_json_for_saved_variants(saved_variants, add_details=False, additional_model_fields=None, additional_values=None):
    sv_additional_values = {
        'familyGuids': ArrayAgg('family__guid', distinct=True),
    }
    if additional_values:
        sv_additional_values.update(additional_values)

    additional_fields = []
    additional_fields += additional_model_fields or []
    if add_details:
        additional_fields.append('saved_variant_json')

    results = get_json_for_queryset(
        saved_variants, guid_key='variantGuid', additional_values=sv_additional_values,
        additional_model_fields=additional_fields,
    )

    if add_details:
        for result in results:
            result.update({k: v for k, v in result.pop('savedVariantJson').items() if k not in result})

    return results


def _format_functional_tags(tags):
    for tag in tags:
        name = tag.pop('functionalDataTag')
        display_data = VariantFunctionalData.FUNCTIONAL_DATA_TAG_LOOKUP[name]
        tag.update({
            'name': name,
            'metadataTitle': display_data.get('metadata_title', 'Notes'),
            'color': display_data['color'],
        })
    return tags


def get_json_for_saved_variants_child_entities(tag_cls, saved_variant_id_map, tag_filter=None):
    variant_tag_id_map = defaultdict(list)
    for savedvariant_id, tag_id in tag_cls.saved_variants.through.objects.filter(
            savedvariant_id__in=saved_variant_id_map.keys()).values_list(
        'savedvariant_id', f'{tag_cls.__name__.lower()}_id',
    ):
        variant_tag_id_map[tag_id].append(savedvariant_id)
    tag_models = tag_cls.objects.filter(id__in=variant_tag_id_map.keys())
    if tag_filter:
        tag_models = tag_models.filter(**tag_filter)

    guid_key = 'tagGuid'
    nested_fields = None
    if tag_cls == VariantTag:
        nested_fields = [
            {'fields': ('variant_tag_type', field), 'key': field} for field in ['name', 'category', 'color']]
    elif tag_cls == VariantNote:
        guid_key = 'noteGuid'

    tags = get_json_for_queryset(
        tag_models, guid_key=guid_key, nested_fields=nested_fields, additional_model_fields=['id'])
    if tag_cls == VariantFunctionalData:
        _format_functional_tags(tags)

    variant_tag_map = defaultdict(list)
    for tag in tags:
        tag['variantGuids'] = []
        variant_ids = variant_tag_id_map[tag.pop('id')]
        for variant_id in variant_ids:
            variant_guid = saved_variant_id_map[variant_id]
            variant_tag_map[variant_guid].append(tag[guid_key])
            tag['variantGuids'].append(variant_guid)

    return tags, variant_tag_map


def get_json_for_saved_variants_with_tags(saved_variants, **kwargs):
    variants_by_guid = {
        variant['variantGuid']: dict(tagGuids=[], functionalDataGuids=[], noteGuids=[], **variant)
        for variant in get_json_for_saved_variants(saved_variants, additional_model_fields=['id'], **kwargs)
    }

    saved_variant_id_map = {}
    for guid, variant in variants_by_guid.items():
        saved_variant_id_map[variant.pop('id')] = guid

    tags, variant_tag_map = get_json_for_saved_variants_child_entities(VariantTag, saved_variant_id_map)
    for variant_guid, tag_guids in variant_tag_map.items():
        variants_by_guid[variant_guid]['tagGuids'] = tag_guids

    functional_data, variant_tag_map = get_json_for_saved_variants_child_entities(
        VariantFunctionalData, saved_variant_id_map)
    for variant_guid, tag_guids in variant_tag_map.items():
        variants_by_guid[variant_guid]['functionalDataGuids'] = tag_guids

    notes, variant_tag_map = get_json_for_saved_variants_child_entities(VariantNote, saved_variant_id_map)
    for variant_guid, tag_guids in variant_tag_map.items():
        variants_by_guid[variant_guid]['noteGuids'] = tag_guids

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

    saved_variants = SavedVariant.objects.filter(
        variant_id__in={variant['variantId'] for variant in variants},
        family__project__guid__in=get_project_guids_user_can_view(user),
    ).only('id', 'guid', 'ref', 'alt', 'xpos', 'family_id').prefetch_related('family', 'family__project')
    saved_variants_by_guid = {sv.guid: sv for sv in saved_variants}
    saved_variant_id_map = {sv.id: guid for guid, sv in saved_variants_by_guid.items()}

    discovery_tag_json, _ = get_json_for_saved_variants_child_entities(
        VariantTag, saved_variant_id_map, tag_filter={'variant_tag_type__category': 'CMG Discovery Tags'})
    if discovery_tag_json:
        existing_families = set()
        for variant in variants:
            existing_families.update(variant['familyGuids'])

        family_ids = set()
        for tag in discovery_tag_json:
            for variant_guid in tag.pop('variantGuids'):
                variant = saved_variants_by_guid[variant_guid]
                if variant.family.guid not in existing_families:
                    family_ids.add(variant.family_id)
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

        response['familiesByGuid'] = {
            f['familyGuid']: f for f in _get_json_for_families(Family.objects.filter(id__in=family_ids))
        }
    return discovery_tags, response


def get_json_for_variant_note(note):
    """Returns a JSON representation of the given variant note.

    Args:
        note (object): Django model for the VariantNote.
    Returns:
        dict: json object
    """
    return _get_json_for_model(note, guid_key='noteGuid')


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


def _add_pa_locus_lists(locus_lists_json, user):
    ll_guids = [ll['locusListGuid'] for ll in locus_lists_json]
    pa_json = get_json_for_queryset(
        PaLocusList.objects.filter(seqr_locus_list__guid__in=ll_guids), user=user,
        nested_fields=[{'fields': ('seqr_locus_list', 'guid'), 'key': 'locusListGuid'}]
    )
    pa_json_by_locus_list = {pa.pop('locusListGuid'): pa for pa in pa_json}
    for ll in locus_lists_json:
        pa_locus_list_json = pa_json_by_locus_list.get(ll['locusListGuid'])
        if pa_locus_list_json:
            ll['paLocusList'] = pa_locus_list_json


def get_json_for_locus_lists(locus_lists, user, include_metadata=True, additional_values=None):
    ll_additional_values = {}
    if additional_values:
        ll_additional_values.update(additional_values)
    if include_metadata:
        ll_additional_values.update({
            'numEntries': Count('locuslistgene') + Count('locuslistinterval'),
            'canEdit': Case(When(created_by=user, then=Value(True)), default=Value(False)),
        })

    results = get_json_for_queryset(locus_lists, user=user, additional_values=ll_additional_values)
    _add_pa_locus_lists(results, user)
    return results


def get_json_for_locus_list(locus_list, user):
    """Returns a JSON representation of the given LocusList.

    Args:
        locus_list (object): LocusList django model.
    Returns:
        dict: json object
    """
    result = _get_json_for_model(locus_list, user=user)

    intervals = _get_json_for_models(locus_list.locuslistinterval_set.all())
    genome_versions = {interval['genomeVersion'] for interval in intervals}
    result.update({
        'items': [{
            'geneId': gene.gene_id,
            'pagene': _get_json_for_model(gene.palocuslistgene, user=user)
            if hasattr(gene, 'palocuslistgene') else None
        } for gene in locus_list.locuslistgene_set.all()] + intervals,
        'intervalGenomeVersion': genome_versions.pop() if len(genome_versions) == 1 else None,
        'canEdit': user == locus_list.created_by,
    })
    result['numEntries'] = len(result['items'])
    _add_pa_locus_lists([result], user)

    return result


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
            username = collaborator.username if collaborator else collaborator_json['username']
            collaborators[username] = collaborator_json

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
    additional_model_fields = []
    results = get_json_for_queryset(searches, guid_key='savedSearchGuid', additional_model_fields=additional_model_fields)
    if not user_is_analyst(user):
        for result in results:
            # Do not apply HGMD filters in shared searches for non-analyst users
            if not result['createdById'] and result['search'].get('pathogenicity', {}).get('hgmd'):
                result['search']['pathogenicity'] = {
                    k: v for k, v in result['search']['pathogenicity'].items() if k != 'hgmd'
                }
    return results


def get_json_for_saved_search(search, user):
    return _get_json_for_model(search, user=user, guid_key='savedSearchGuid')


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


EXPRESSION_OUTLIERS = 'outliers'
SPLICE_OUTLIERS = 'spliceOutliers'


def get_json_for_rna_seq_outliers(filters, significant_only=True, individual_guid=None):
    filters = {'sample__is_active': True, **filters}

    data_by_individual_gene = defaultdict(lambda: {EXPRESSION_OUTLIERS: {}, SPLICE_OUTLIERS: defaultdict(list)})

    for model, outlier_type in [(RnaSeqOutlier, EXPRESSION_OUTLIERS), (RnaSeqSpliceOutlier, SPLICE_OUTLIERS)]:
        significant_filter = {f'{model.SIGNIFICANCE_FIELD}__lt': model.SIGNIFICANCE_THRESHOLD}
        if hasattr(model, 'MAX_SIGNIFICANT_OUTLIER_NUM'):
            significant_filter['rank__lt'] = model.MAX_SIGNIFICANT_OUTLIER_NUM

        outliers = get_json_for_queryset(
            model.objects.filter(**filters, **(significant_filter if significant_only else {})),
            nested_fields=[
                {'fields': ('sample', 'tissue_type'), 'key': 'tissueType'},
                {'fields': ('sample', 'individual', 'guid'), 'key': 'individualGuid', 'value': individual_guid},
            ],
            additional_values={'isSignificant': Value(True)} if significant_only else {
                'isSignificant': Case(When(then=Value(True), **significant_filter), default=Value(False))},
        )

        for data in outliers:
            if outlier_type == EXPRESSION_OUTLIERS:
                data_by_individual_gene[data.pop('individualGuid')][outlier_type][data['geneId']] = data
            else:
                data_by_individual_gene[data.pop('individualGuid')][outlier_type][data['geneId']].append(data)

    return data_by_individual_gene
