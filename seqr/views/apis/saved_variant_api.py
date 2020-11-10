import logging
import json
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from seqr.models import SavedVariant, VariantTagType, VariantTag, VariantNote, VariantFunctionalData,\
    LocusList, LocusListInterval, LocusListGene, Family, GeneNote
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json, \
    create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants_with_tags, get_json_for_variant_note, \
    get_json_for_variant_tags, get_json_for_variant_functional_data_tags, get_json_for_gene_notes_by_gene_id, \
    _get_json_for_models
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions
from seqr.views.utils.variant_utils import update_project_saved_variant_json, reset_cached_search_results, \
    get_variant_key, saved_variant_genes
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def saved_variant_data(request, project_guid, variant_guids=None):
    project = get_project_and_check_permissions(project_guid, request.user)
    family_guids = request.GET['families'].split(',') if request.GET.get('families') else None
    variant_guids = variant_guids.split(',') if variant_guids else None

    if family_guids:
        variant_query = SavedVariant.objects.filter(family__guid__in=family_guids)
    else:
        variant_query = SavedVariant.objects.filter(family__project=project)
    if variant_guids:
        variant_query = variant_query.filter(guid__in=variant_guids)
        if variant_query.count() < 1:
            return create_json_response({}, status=404, reason='Variant {} not found'.format(', '.join(variant_guids)))

    discovery_tags_query = None
    if request.user.is_staff:
        discovery_tags_query = Q()
        for variant in variant_query:
            discovery_tags_query |= Q(Q(variant_id=variant.variant_id) & ~Q(family_id=variant.family_id))

    response = get_json_for_saved_variants_with_tags(variant_query, add_details=True, discovery_tags_query=discovery_tags_query)

    variants = list(response['savedVariantsByGuid'].values())
    genes = saved_variant_genes(variants)
    response['locusListsByGuid'] = _add_locus_lists([project], genes)
    discovery_tags = response.pop('discoveryTags', None)
    if discovery_tags:
        _add_discovery_tags(variants, discovery_tags)
    response['genesById'] = genes

    return create_json_response(response)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def create_saved_variant_handler(request):
    variant_json = json.loads(request.body)
    family_guid = variant_json['familyGuid']

    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    if isinstance(variant_json['variant'], list):
        # are compound hets
        saved_variants = []
        for single_variant_json in variant_json['variant']:
            saved_variant, _ = get_or_create_model_from_json(
                SavedVariant, create_json=_get_parsed_variant_args(single_variant_json, family),
                update_json={'saved_variant_json': single_variant_json}, user=request.user)
            saved_variants.append(saved_variant)
    else:
        parsed_variant_json = _get_parsed_variant_args(variant_json['variant'], family)
        parsed_variant_json['saved_variant_json'] = variant_json['variant']
        saved_variant = create_model_from_json(SavedVariant, parsed_variant_json, request.user)
        saved_variants = [saved_variant]

    if variant_json.get('note'):
        _create_variant_note(saved_variants, variant_json, request.user)
    elif variant_json.get('tags'):
        _create_new_tags(saved_variants, variant_json, request.user)

    return create_json_response(get_json_for_saved_variants_with_tags(saved_variants, add_details=True))


def _get_parsed_variant_args(variant_json, family):
    if 'xpos' not in variant_json:
        variant_json['xpos'] = get_xpos(variant_json['chrom'], variant_json['pos'])
    xpos = variant_json['xpos']
    ref = variant_json.get('ref')
    alt = variant_json.get('alt')
    var_length = variant_json['end'] - variant_json['pos'] if 'end' in variant_json else len(ref) - 1
    return {
        'xpos': xpos,
        'xpos_start':  xpos,
        'xpos_end':  xpos + var_length,
        'ref':  ref,
        'alt':  alt,
        'family':  family,
        'variant_id': variant_json['variantId']
    }


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def create_variant_note_handler(request, variant_guids):
    request_json = json.loads(request.body)
    save_as_gene_note = request_json.get('saveAsGeneNote')

    family_guid = request_json.pop('familyGuid')
    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    all_variant_guids = variant_guids.split(',')
    saved_variants = SavedVariant.objects.filter(guid__in=all_variant_guids)
    if len(saved_variants) != len(all_variant_guids):
        error = 'Unable to find the following variant(s): {}'.format(
            ', '.join([guid for guid in all_variant_guids if guid not in {sv.guid for sv in saved_variants}]))
        return create_json_response({'error': error}, status=400, reason=error)

    # update saved_variants
    note = _create_variant_note(saved_variants, request_json, request.user)
    note_json = get_json_for_variant_note(note, add_variant_guids=False)
    note_json['variantGuids'] = all_variant_guids
    response = {
        'savedVariantsByGuid': {
            saved_variant.guid: {'noteGuids': [n.guid for n in saved_variant.variantnote_set.all()]}
            for saved_variant in saved_variants},
        'variantNotesByGuid': {note.guid: note_json},
    }

    if save_as_gene_note:
        main_transcript_id = saved_variants[0].selected_main_transcript_id or saved_variants[0].saved_variant_json['mainTranscriptId']
        gene_id = next(
            (gene_id for gene_id, transcripts in saved_variants[0].saved_variant_json['transcripts'].items()
             if any(t['transcriptId'] == main_transcript_id for t in transcripts)), None) if main_transcript_id else None
        create_model_from_json(GeneNote, {'note': request_json.get('note'), 'gene_id': gene_id}, request.user)
        response['genesById'] = {gene_id: {
            'notes': get_json_for_gene_notes_by_gene_id([gene_id], request.user)[gene_id],
        }}

    return create_json_response(response)


def _create_variant_note(saved_variants, note_json, user):
    note = create_model_from_json(VariantNote, {
        'note': note_json.get('note'),
        'submit_to_clinvar': note_json.get('submitToClinvar') or False,
        'search_hash': note_json.get('searchHash'),
    }, user)
    note.saved_variants.set(saved_variants)
    return note


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_variant_note_handler(request, variant_guids, note_guid):
    note = VariantNote.objects.get(guid=note_guid)
    projects = {saved_variant.family.project for saved_variant in note.saved_variants.all()}
    for project in projects:
        check_project_permissions(project, request.user)
    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, user=request.user, allow_unknown_keys=True)

    note_json = get_json_for_variant_note(note, add_variant_guids=False)
    note_json['variantGuids'] = variant_guids.split(',')

    return create_json_response({
        'variantNotesByGuid': {note.guid: note_json},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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
            if not saved_variant.varianttag_set.count() > 0:
                saved_variant.delete_model(request.user, user_can_delete=True)
                saved_variants_by_guid[saved_variant.guid] = None

    return create_json_response({
        'savedVariantsByGuid': saved_variants_by_guid,
        'variantNotesByGuid': {note_guid: None},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_variant_tags_handler(request, variant_guids):
    request_json = json.loads(request.body)

    family_guid = request_json.pop('familyGuid')
    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    all_variant_guids = set(variant_guids.split(','))
    saved_variants = SavedVariant.objects.filter(guid__in=all_variant_guids)
    if len(saved_variants) != len(all_variant_guids):
        error = 'Unable to find the following variant(s): {}'.format(
            ', '.join([guid for guid in all_variant_guids if guid not in {sv.guid for sv in saved_variants}]))
        return create_json_response({'error': error}, status=400, reason=error)

    deleted_tag_guids = _delete_removed_tags(saved_variants, all_variant_guids, request_json.get('tags', []), request.user)
    created_tags = _create_new_tags(saved_variants, request_json, request.user)
    tag_updates = {tag['tagGuid']: tag for tag in get_json_for_variant_tags(created_tags)}
    tag_updates.update({guid: None for guid in deleted_tag_guids})

    saved_variants_by_guid = {}
    for saved_variant in saved_variants:
        tags = saved_variant.varianttag_set.all()
        saved_variants_by_guid[saved_variant.guid] = {'tagGuids': [t.guid for t in tags]}
        if not tags:
            if not saved_variant.variantnote_set.count() > 0:
                saved_variant.delete_model(request.user, user_can_delete=True)
                saved_variants_by_guid[saved_variant.guid] = None

    return create_json_response({
        'savedVariantsByGuid': saved_variants_by_guid,
        'variantTagsByGuid': tag_updates,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_variant_functional_data_handler(request, variant_guids):
    request_json = json.loads(request.body)

    family_guid = request_json.pop('familyGuid')
    family = Family.objects.get(guid=family_guid)
    check_project_permissions(family.project, request.user)

    all_variant_guids = set(variant_guids.split(','))
    saved_variants = SavedVariant.objects.filter(guid__in=all_variant_guids)
    if len(saved_variants) != len(all_variant_guids):
        error = 'Unable to find the following variant(s): {}'.format(
            ', '.join([guid for guid in all_variant_guids if guid not in {sv.guid for sv in saved_variants}]))
        return create_json_response({'error': error}, status=400, reason=error)

    updated_functional_data = request_json.get('functionalData', [])
    deleted_functional_guids = _delete_removed_tags(
        saved_variants, all_variant_guids, updated_functional_data, request.user, tag_type='functionaldata')

    updated_functional_models = []
    for tag in updated_functional_data:
        if tag.get('tagGuid'):
            functional_data = VariantFunctionalData.objects.get(guid=tag.get('tagGuid'))
            update_model_from_json(functional_data, tag, user=request.user, allow_unknown_keys=True)
        else:
            functional_data = create_model_from_json(VariantFunctionalData, {
                'functional_data_tag': tag.get('name'),
                'metadata': tag.get('metadata'),
                'search_hash': request_json.get('searchHash'),
            }, request.user)
            functional_data.saved_variants.set(saved_variants)
        updated_functional_models.append(functional_data)

    functional_updates = {tag['tagGuid']: tag for tag in get_json_for_variant_functional_data_tags(updated_functional_models)}
    functional_updates.update({guid: None for guid in deleted_functional_guids})

    return create_json_response({
        'savedVariantsByGuid': {saved_variant.guid: {
            'functionalDataGuids': [t.guid for t in saved_variant.variantfunctionaldata_set.all()],
        } for saved_variant in saved_variants},
        'variantFunctionalDataByGuid': functional_updates,
    })


def _delete_removed_tags(saved_variants, all_variant_guids, tag_updates, user, tag_type='tag'):
    existing_tag_guids = [tag['tagGuid'] for tag in tag_updates if tag.get('tagGuid')]
    deleted_tag_guids = []
    tag_set = getattr(saved_variants[0], 'variant{}_set'.format(tag_type))
    for tag in tag_set.exclude(guid__in=existing_tag_guids):
        tag_variant_guids = {sv.guid for sv in tag.saved_variants.all()}
        if tag_variant_guids == all_variant_guids:
            deleted_tag_guids.append(tag.guid)
            tag.delete_model(user, user_can_delete=True)
    return deleted_tag_guids


def _create_new_tags(saved_variants, tags_json, user):
    tags = tags_json.get('tags', [])
    new_tags = [tag for tag in tags if not tag.get('tagGuid')]

    new_tag_models = []
    for tag in new_tags:
        variant_tag_type = VariantTagType.objects.get(
            Q(name=tag['name']),
            Q(project=saved_variants[0].family.project) | Q(project__isnull=True)
        )
        tag_model = create_model_from_json(VariantTag, {
            'variant_tag_type': variant_tag_type,
            'search_hash': tags_json.get('searchHash'),
        }, user)
        tag_model.saved_variants.set(saved_variants)
        new_tag_models.append(tag_model)
    return new_tag_models


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_saved_variant_json(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    reset_cached_search_results(project)
    try:
        updated_saved_variant_guids = update_project_saved_variant_json(project, user=request.user)
    except Exception as e:
        logger.error('Unable to reset saved variant json for {}: {}'.format(project_guid, e))
        updated_saved_variant_guids = []

    return create_json_response({variant_guid: None for variant_guid in updated_saved_variant_guids})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_variant_main_transcript(request, variant_guid, transcript_id):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_project_permissions(saved_variant.family.project, request.user, can_edit=True)

    update_model_from_json(saved_variant, {'selected_main_transcript_id': transcript_id}, request.user)

    return create_json_response({'savedVariantsByGuid': {variant_guid: {'selectedMainTranscriptId': transcript_id}}})


def _add_locus_lists(projects, genes, include_all_lists=False):
    locus_lists = LocusList.objects.filter(projects__in=projects)

    if include_all_lists:
        locus_lists_by_guid = {locus_list.guid: {'intervals': []} for locus_list in locus_lists}
    else:
        locus_lists_by_guid = defaultdict(lambda: {'intervals': []})
    intervals = LocusListInterval.objects.filter(locus_list__in=locus_lists)
    for interval in _get_json_for_models(intervals, nested_fields=[{'fields': ('locus_list', 'guid')}]):
        locus_lists_by_guid[interval['locusListGuid']]['intervals'].append(interval)

    for locus_list_gene in LocusListGene.objects.filter(locus_list__in=locus_lists, gene_id__in=genes.keys()).prefetch_related('locus_list'):
        genes[locus_list_gene.gene_id]['locusListGuids'].append(locus_list_gene.locus_list.guid)

    return locus_lists_by_guid


def _add_discovery_tags(variants, discovery_tags):
    for variant in variants:
        tags = discovery_tags.get(get_variant_key(**variant))
        if tags:
            if not variant.get('discoveryTags'):
                variant['discoveryTags'] = []
            variant['discoveryTags'] += tags
