import logging
import json
from django.db.models import Q

from seqr.models import SavedVariant, VariantTagType, VariantTag, VariantNote, VariantFunctionalData,\
    Family, GeneNote, Project
from seqr.utils.search.utils import backend_specific_call
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json, \
    create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants_with_tags, get_json_for_variant_note, \
    get_json_for_saved_variants_child_entities, get_json_for_gene_notes_by_gene_id, STRUCTURED_METADATA_TAG_TYPES
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions, \
    login_and_policies_required
from seqr.views.utils.variant_utils import update_project_saved_variant_json, reset_cached_search_results, \
    get_variants_response, parse_saved_variant_json


logger = logging.getLogger(__name__)

INCLUDE_LOCUS_LISTS_PARAM = 'includeLocusLists'

@login_and_policies_required
def saved_variant_data(request, project_guid, variant_guids=None):
    project = get_project_and_check_permissions(project_guid, request.user)
    family_guids = request.GET['families'].split(',') if request.GET.get('families') else None
    variant_guids = variant_guids.split(',') if variant_guids else None

    variant_query = SavedVariant.objects.filter(family__project=project)
    if variant_guids:
        variant_query = variant_query.filter(guid__in=variant_guids)
        if variant_query.count() < 1:
            return create_json_response({}, status=404, reason='Variant {} not found'.format(', '.join(variant_guids)))
    elif family_guids:
        variant_query = variant_query.filter(family__guid__in=family_guids)
    else:
        get_note_only = bool(request.GET.get('includeNoteVariants'))
        variant_query = variant_query.filter(varianttag__isnull=get_note_only).distinct()

    add_locus_list_detail = request.GET.get(INCLUDE_LOCUS_LISTS_PARAM) == 'true'
    response = get_variants_response(request, variant_query, add_locus_list_detail=add_locus_list_detail)
    if 'individualsByGuid' in response and not family_guids:
        if 'projectsByGuid' not in response:
            response['projectsByGuid'] = {project_guid: {}}
        response['projectsByGuid'][project_guid]['familiesLoaded'] = True

    return create_json_response(response)


@login_and_policies_required
def create_saved_variant_handler(request):
    variant_json = json.loads(request.body)
    family_guid = variant_json['familyGuid']

    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    variants_json = variant_json['variant']
    if not isinstance(variant_json['variant'], list):
        variants_json = [variants_json]

    saved_variant_guids = []
    for single_variant_json in variants_json:
        try:
            create_json, update_json = parse_saved_variant_json(single_variant_json, family.id)
        except ValueError as e:
            return create_json_response({'error': str(e)}, status=400)
        saved_variant, _ = get_or_create_model_from_json(
            SavedVariant, create_json=create_json, update_json=update_json,
            user=request.user, update_on_create_only=True)
        saved_variant_guids.append(saved_variant.guid)
    saved_variants = SavedVariant.objects.filter(guid__in=saved_variant_guids)

    response = {}
    if variant_json.get('note'):
        _, response = _create_variant_note(saved_variants, variant_json, request.user)
    elif variant_json.get('tags'):
        _update_tags(saved_variants, variant_json, request.user)

    response.update(get_json_for_saved_variants_with_tags(saved_variants, add_details=True))
    return create_json_response(response)


@login_and_policies_required
def create_variant_note_handler(request, variant_guids):
    request_json = json.loads(request.body)

    family_guid = request_json.pop('familyGuid')
    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    all_variant_guids = variant_guids.split(',')
    saved_variants = SavedVariant.objects.filter(guid__in=all_variant_guids)
    if len(saved_variants) != len(all_variant_guids):
        error = 'Unable to find the following variant(s): {}'.format(
            ', '.join([guid for guid in all_variant_guids if guid not in {sv.guid for sv in saved_variants}]))
        return create_json_response({'error': error}, status=400, reason=error)

    if not request_json.get('note'):
        return create_json_response({'error': 'Note is required'}, status=400)

    # update saved_variants
    note, response = _create_variant_note(saved_variants, request_json, request.user)
    note_json = get_json_for_variant_note(note)
    note_json['variantGuids'] = all_variant_guids
    response.update({
        'savedVariantsByGuid': {
            saved_variant.guid: {'noteGuids': [n.guid for n in saved_variant.variantnote_set.all()]}
            for saved_variant in saved_variants},
        'variantNotesByGuid': {note.guid: note_json},
    })

    return create_json_response(response)


def _create_variant_note(saved_variants, note_json, user):
    note = create_model_from_json(VariantNote, {
        'note': note_json.get('note'),
        'report': note_json.get('report') or False,
        'search_hash': note_json.get('searchHash'),
    }, user)
    note.saved_variants.set(saved_variants)

    response = {}
    if note_json.get('saveAsGeneNote'):
        main_transcript_id = saved_variants[0].selected_main_transcript_id or saved_variants[0].saved_variant_json.get('mainTranscriptId')
        if main_transcript_id:
            gene_id = next(
                gene_id for gene_id, transcripts in saved_variants[0].saved_variant_json['transcripts'].items()
                if any(t['transcriptId'] == main_transcript_id for t in transcripts))
        else:
            gene_id = next(gene_id for gene_id in sorted(saved_variants[0].saved_variant_json['transcripts']))
        create_model_from_json(GeneNote, {'note': note_json.get('note'), 'gene_id': gene_id}, user)
        response['genesById'] = {gene_id: {
            'notes': get_json_for_gene_notes_by_gene_id([gene_id], user)[gene_id],
        }}

    return note, response


@login_and_policies_required
def update_variant_note_handler(request, variant_guids, note_guid):
    note = VariantNote.objects.get(guid=note_guid)
    projects = {saved_variant.family.project for saved_variant in note.saved_variants.all()}
    for project in projects:
        check_project_permissions(project, request.user)
    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, user=request.user, allow_unknown_keys=True)

    note_json = get_json_for_variant_note(note)
    note_json['variantGuids'] = variant_guids.split(',')

    return create_json_response({
        'variantNotesByGuid': {note.guid: note_json},
    })


@login_and_policies_required
def delete_variant_note_handler(request, variant_guids, note_guid):
    variant_guids = variant_guids.split(',')
    note = VariantNote.objects.get(guid=note_guid)
    projects = {saved_variant.family.project for saved_variant in note.saved_variants.all()}
    for project in projects:
        check_project_permissions(project, request.user)
    note.delete_model(request.user, user_can_delete=True)

    saved_variants_by_guid = {}
    for saved_variant in SavedVariant.objects.filter(guid__in=variant_guids):
        notes = saved_variant.variantnote_set.all()
        saved_variants_by_guid[saved_variant.guid] = {'noteGuids': [n.guid for n in notes]}
        if not notes:
            if saved_variant.varianttag_set.count() == 0 and saved_variant.matchmakersubmissiongenes_set.count() == 0:
                saved_variant.delete_model(request.user, user_can_delete=True)
                saved_variants_by_guid[saved_variant.guid] = None

    return create_json_response({
        'savedVariantsByGuid': saved_variants_by_guid,
        'variantNotesByGuid': {note_guid: None},
    })


def _get_tag_type_create_data(tag, saved_variants=None):
    variant_tag_type = VariantTagType.objects.get(
        Q(name=tag['name']),
        Q(project=saved_variants[0].family.project) | Q(project__isnull=True)
    )
    return {'variant_tag_type': variant_tag_type}


@login_and_policies_required
def update_variant_tags_handler(request, variant_guids):
    return _update_variant_tag_models(
        request, variant_guids, tag_key='tags', response_guid_key='tagGuids', model_cls=VariantTag,
        get_tag_create_data=_get_tag_type_create_data, delete_variants_if_empty=True, protected_tag_types=STRUCTURED_METADATA_TAG_TYPES)

@login_and_policies_required
def update_variant_acmg_classification_handler(request, variant_guid):
    return _update_variant_acmg_classification(request, variant_guid)

def _update_variant_acmg_classification(request, variant_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_project_permissions(saved_variant.family.project, request.user)

    request_json = json.loads(request.body)
    variant = request_json.get('variant')
    update_model_from_json(saved_variant, {'acmg_classification': variant['acmgClassification']}, request.user)

    return create_json_response({
        'savedVariantsByGuid': {
            variant_guid: {
                'acmgClassification': variant['acmgClassification'],
            }
        },
    })

@login_and_policies_required
def update_variant_functional_data_handler(request, variant_guids):
    return _update_variant_tag_models(
        request, variant_guids, tag_key='functionalData', model_cls=VariantFunctionalData,
        get_tag_create_data=lambda tag, **kwargs: {'functional_data_tag': tag.get('name')})


def _update_variant_tag_models(request, variant_guids, tag_key, model_cls, get_tag_create_data, response_guid_key=None, delete_variants_if_empty=False, protected_tag_types=None):
    request_json = json.loads(request.body)

    family_guid = request_json.pop('familyGuid')
    project = Project.objects.get(family__guid=family_guid)
    check_project_permissions(project, request.user)

    all_variant_guids = set(variant_guids.split(','))
    saved_variants = SavedVariant.objects.filter(guid__in=all_variant_guids)
    if len(saved_variants) != len(all_variant_guids):
        error = 'Unable to find the following variant(s): {}'.format(
            ', '.join([guid for guid in all_variant_guids if guid not in {sv.guid for sv in saved_variants}]))
        return create_json_response({'error': error}, status=400, reason=error)

    tag_type = tag_key.lower().rstrip('s')
    updated_data = request_json.get(tag_key, [])
    deleted_guids = _delete_removed_tags(saved_variants, all_variant_guids, updated_data, request.user, tag_type, protected_tag_types)

    _update_tags(saved_variants, request_json, request.user, tag_key, model_cls, get_tag_create_data)

    saved_variant_id_map = {sv.id: sv.guid for sv in saved_variants}
    tags, variant_tag_map = get_json_for_saved_variants_child_entities(model_cls, saved_variant_id_map)
    updates = {tag['tagGuid']: tag for tag in tags}
    updates.update({guid: None for guid in deleted_guids})

    if not response_guid_key:
        response_guid_key = '{}Guids'.format(tag_key)
    saved_variants_by_guid = {}
    for saved_variant in saved_variants:
        tag_guids = variant_tag_map[saved_variant.guid]
        saved_variants_by_guid[saved_variant.guid] = {response_guid_key: tag_guids}
        if delete_variants_if_empty and not tag_guids:
            if saved_variant.variantnote_set.count() == 0 and saved_variant.matchmakersubmissiongenes_set.count() == 0:
                saved_variant.delete_model(request.user, user_can_delete=True)
                saved_variants_by_guid[saved_variant.guid] = None

    return create_json_response({
        'savedVariantsByGuid': saved_variants_by_guid,
        'variant{}{}ByGuid'.format(tag_key[0].upper(), tag_key[1:]): updates,
    })


def _get_tag_set(saved_variant, tag_type):
    return getattr(saved_variant, 'variant{}_set'.format(tag_type))


def _delete_removed_tags(saved_variants, all_variant_guids, tag_updates, user, tag_type, protected_tag_types):
    existing_tag_guids = [tag['tagGuid'] for tag in tag_updates if tag.get('tagGuid')]
    deleted_tag_guids = []
    tag_set = _get_tag_set(saved_variants[0], tag_type)
    remove_tags = tag_set.exclude(guid__in=existing_tag_guids)
    if protected_tag_types:
        remove_tags = remove_tags.exclude(variant_tag_type__name__in=protected_tag_types)
    for tag in remove_tags:
        tag_variant_guids = {sv.guid for sv in tag.saved_variants.all()}
        if tag_variant_guids == all_variant_guids:
            deleted_tag_guids.append(tag.guid)
            tag.delete_model(user, user_can_delete=True)
    return deleted_tag_guids


def _update_tags(saved_variants, tags_json, user, tag_key='tags', model_cls=VariantTag, get_tag_create_data=_get_tag_type_create_data):
    tags = tags_json.get(tag_key, [])
    for tag in tags:
        if tag.get('tagGuid'):
            model = model_cls.objects.get(guid=tag.get('tagGuid'))
            update_model_from_json(model, tag, user=user, allow_unknown_keys=True)
        else:
            create_data = get_tag_create_data(tag, saved_variants=saved_variants)
            create_data.update({
                'metadata': tag.get('metadata'),
                'search_hash': tags_json.get('searchHash'),
            })
            model = create_model_from_json(model_cls, create_data, user)
            model.saved_variants.set(saved_variants)


@login_and_policies_required
def update_saved_variant_json(request, project_guid):
    backend_specific_call(lambda: True, _hail_backend_error)()
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    reset_cached_search_results(project)
    try:
        updated_saved_variant_guids = update_project_saved_variant_json(project.id, project.genome_version, user=request.user)
    except Exception as e:
        logger.error('Unable to reset saved variant json for {}: {}'.format(project_guid, e))
        updated_saved_variant_guids = []

    return create_json_response({variant_guid: None for variant_guid in updated_saved_variant_guids or []})


def _hail_backend_error(*args, **kwargs):
    raise ValueError('Endpoint is disabled for the hail backend')


@login_and_policies_required
def update_variant_main_transcript(request, variant_guid, transcript_id):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_project_permissions(saved_variant.family.project, request.user, can_edit=True)

    update_model_from_json(saved_variant, {'selected_main_transcript_id': transcript_id}, request.user)

    return create_json_response({'savedVariantsByGuid': {variant_guid: {'selectedMainTranscriptId': transcript_id}}})
