import logging
import json
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import SavedVariant, VariantTagType, VariantTag, VariantNote, VariantFunctionalData,\
    LocusListInterval, LocusListGene, Family, CAN_VIEW, CAN_EDIT, GeneNote
from seqr.model_utils import create_seqr_model, delete_seqr_model
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants, get_json_for_variant_tag, \
    get_json_for_variant_functional_data, get_json_for_variant_note, get_json_for_saved_variant, \
    get_json_for_gene_notes_by_gene_id, get_project_locus_list_models
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions
from seqr.views.utils.variant_utils import update_project_saved_variant_json
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def saved_variant_data(request, project_guid, variant_guid=None):
    project = get_project_and_check_permissions(project_guid, request.user)
    family_guids = request.GET['families'].split(',') if request.GET.get('families') else None

    if family_guids:
        variant_query = SavedVariant.objects.filter(family__guid__in=family_guids)
    else:
        variant_query = SavedVariant.objects.filter(family__project=project)
    if variant_guid:
        variant_query = variant_query.filter(guid=variant_guid)
        if variant_query.count() < 1:
            return create_json_response({}, status=404, reason='Variant {} not found'.format(variant_guid))

    saved_variants = get_json_for_saved_variants(variant_query, add_tags=True, add_details=True)
    variants = {variant['variantGuid']: variant for variant in saved_variants if variant['notes'] or variant['tags']}
    genes = _saved_variant_genes(variants.values())
    _add_locus_lists([project], variants.values(), genes)

    return create_json_response({
        'savedVariantsByGuid': variants,
        'genesById': genes,
    })


def _create_single_saved_variant(variant_json, family):
    xpos = variant_json['xpos']
    ref = variant_json['ref']
    alt = variant_json['alt']
    saved_variant = SavedVariant.objects.create(
        xpos=xpos,
        xpos_start=xpos,
        xpos_end=xpos + len(ref) - 1,
        ref=ref,
        alt=alt,
        family=family,
        saved_variant_json=variant_json
    )
    return saved_variant

# TODO create helper function to save multiple compound hets _create_multi_saved_variants(request_json):

@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_saved_variant_handler(request):
    variant_json = json.loads(request.body)
    non_variant_key = ['searchHash', 'tags', 'functionalData', 'notes', 'note', 'submitToClinvar', 'saveAsGeneNote']
    non_variant_json = {k: variant_json.pop(k, None) for k in non_variant_key}

    family_guid = variant_json.pop('familyGuid')
    family = Family.objects.get(guid=family_guid)
    check_permissions(family.project, request.user, CAN_VIEW)

    saved_variants = []

    # are compound hets
    if 'familyGuids' not in variant_json.keys():
        for key in variant_json.keys():
            if key not in non_variant_key:
                compound_het = variant_json[key]
                if 'variantGuid' not in compound_het.keys():  # not a saved_variant
                    saved_variant = _create_single_saved_variant(compound_het, family)
                    saved_variants.append(saved_variant)
    # is single variant
    else:
        saved_variant = _create_single_saved_variant(variant_json, family)
        saved_variants = [saved_variant]

    if non_variant_json.get('note'):
        _create_variant_note(saved_variants, non_variant_json, request.user)
    elif non_variant_json.get('tags'):
        _create_new_tags(saved_variants, non_variant_json, request.user)
    variant_json.update(get_json_for_saved_variant(saved_variant, add_tags=True))
    return create_json_response({
        'savedVariantsByGuid': {saved_variant.guid: variant_json},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_variant_note_handler(request, variant_guids):
    request_json = json.loads(request.body)
    save_as_gene_note = request_json.get('saveAsGeneNote')

    family_guid = request_json.pop('familyGuid')
    family = Family.objects.get(guid=family_guid)
    check_permissions(family.project, request.user, CAN_VIEW)

    saved_variants = []

    # save unsaved variants in compound hets
    if 'familyGuids' not in request_json.keys():  # are compound hets
        gene_note = {}
        non_variant_key = ['searchHash', 'tags', 'functionalData', 'notes', 'note', 'submitToClinvar', 'saveAsGeneNote']
        for key in request_json.keys():
            if key not in non_variant_key:
                compound_het = request_json[key]
                if 'variantGuid' not in compound_het.keys():  # not a saved_variant
                    saved_variant = _create_single_saved_variant(compound_het, family)
                    saved_variants.append(saved_variant)

    # update saved_variants
    variant_guids = [] if variant_guids == 'no_saved_variant' else variant_guids.split(',')
    for variant_guid in variant_guids:
        saved_variant = SavedVariant.objects.get(guid=variant_guid)
        check_permissions(saved_variant.family.project, request.user, CAN_VIEW)

        if save_as_gene_note:
            main_transcript_id = saved_variant.selected_main_transcript_id or saved_variant.saved_variant_json['mainTranscriptId']
            gene_id = next(
                (gene_id for gene_id, transcripts in saved_variant.saved_variant_json['transcripts'].items()
                 if any(t['transcriptId'] == main_transcript_id for t in transcripts)), None) if main_transcript_id else None
            create_seqr_model(
                GeneNote,
                note=request_json.get('note'),
                gene_id=gene_id,
                created_by=request.user,
            )

        gene_note = {gene_id: {
            'notes': get_json_for_gene_notes_by_gene_id([gene_id], request.user).get(gene_id, [])}} if save_as_gene_note else {}

        saved_variants.append(saved_variant)

    _create_variant_note(saved_variants, request_json, request.user)

    variant_note = {}
    for saved_variant in saved_variants:
        variant_note[saved_variant.guid] = get_json_for_saved_variant(saved_variant, add_tags=True)
    return create_json_response({
        'savedVariantsByGuid': variant_note,
        'genesById': gene_note,
    })


def _create_variant_note(saved_variants, note_json, user):
    create_seqr_model(
        VariantNote,
        note=note_json.get('note'),
        saved_variants=saved_variants,
        submit_to_clinvar=note_json.get('submitToClinvar') or False,
        search_hash=note_json.get('searchHash'),
        created_by=user,
    )


def _get_note_from_variant_guids(user, variant_guids, note_guid):
    saved_variants = SavedVariant.objects.filter(guid__in=variant_guids)
    check_permissions(saved_variants[0].family.project, user, CAN_VIEW)
    note = VariantNote.objects.get(guid=note_guid)
    projects = {saved_variant.family.project for saved_variant in note.saved_variants.all()}
    for project in projects:
        check_permissions(project, user, CAN_VIEW)
    return note


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_note_handler(request, variant_guids, note_guid):
    variant_guids = variant_guids.split(',')
    note = _get_note_from_variant_guids(request.user, variant_guids, note_guid)
    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, allow_unknown_keys=True)
    saved_variants = SavedVariant.objects.filter(guid__in=variant_guids)
    update = {}
    for variant_guid in variant_guids:
        update[variant_guid] = {
            'notes': [get_json_for_variant_note(note) for note in saved_variants[0].variantnote_set.all()],
        }
    return create_json_response({'savedVariantsByGuid': update})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_variant_note_handler(request, variant_guids, note_guid):
    variant_guids = variant_guids.split(',')
    note = _get_note_from_variant_guids(request.user, variant_guids, note_guid)
    delete_seqr_model(note)
    logging.info("variant_guids(%s)" % variant_guids)
    saved_variants = SavedVariant.objects.filter(guid__in=variant_guids)

    update = {}
    for variant_guid in variant_guids:
        update[variant_guid] = {
            'notes': [get_json_for_variant_note(note) for note in saved_variants[0].variantnote_set.all()]
        }
    return create_json_response({'savedVariantsByGuid': update})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_tags_handler(request, variant_guids):
    request_json = json.loads(request.body)

    family_guid = request_json.pop('familyGuid')
    family = Family.objects.get(guid=family_guid)
    check_permissions(family.project, request.user, CAN_VIEW)

    updated_tags = request_json.get('tags', [])
    updated_functional_data = request_json.get('functionalData', [])

    saved_variants = []
    unsaved_compound_hets = request_json.get('compoundHetsToSave') or []
    all_variant_guids = variant_guids.split(',')

    # get saved_variants
    for variant_guid in all_variant_guids:
        saved_variant = SavedVariant.objects.get(guid=variant_guid)
        saved_variants.append(saved_variant)

    # save compound hets that are not saved_variants
    for compound_het in unsaved_compound_hets:
        saved_variant = _create_single_saved_variant(compound_het, family)
        saved_variants.append(saved_variant)
        all_variant_guids.append(saved_variant.guid)

    # Update tags

    existing_tag_guids = [tag['tagGuid'] for tag in updated_tags if tag.get('tagGuid')]

    for tag in saved_variants[0].varianttag_set.exclude(guid__in=existing_tag_guids):
        delete_seqr_model(tag)

    _create_new_tags(saved_variants, request_json, request.user)

    # Update functional data

    existing_functional_guids = [tag['tagGuid'] for tag in updated_functional_data if tag.get('tagGuid')]

    for tag in saved_variants[0].variantfunctionaldata_set.exclude(guid__in=existing_functional_guids):
        delete_seqr_model(tag)

    for tag in updated_functional_data:
        if tag.get('tagGuid'):
            tag_model = VariantFunctionalData.objects.filter(
                guid=tag.get('tagGuid'),
                functional_data_tag=tag.get('name'),
                saved_variants__in=saved_variants
            ).prefetch_related('saved_variants').first()
            update_model_from_json(tag_model, tag, allow_unknown_keys=True)
        else:
            create_seqr_model(
                VariantFunctionalData,
                saved_variants=saved_variants,
                functional_data_tag=tag.get('name'),
                metadata=tag.get('metadata'),
                search_hash=request_json.get('searchHash'),
                created_by=request.user,
            )
    update = {}
    for variant_guid in all_variant_guids:
        update[variant_guid] = {
            'tags': [get_json_for_variant_tag(tag) for tag in saved_variants[0].varianttag_set.all()],
            'functionalData': [get_json_for_variant_functional_data(functional_data) for functional_data in saved_variants[0].variantfunctionaldata_set.all()]
        }

    return create_json_response({'savedVariantsByGuid': update})


def _create_new_tags(saved_variants, tags_json, user):
    tags = tags_json.get('tags', [])
    new_tags = [tag for tag in tags if not tag.get('tagGuid')]

    for tag in new_tags:
        variant_tag_type = VariantTagType.objects.get(
            Q(name=tag['name']),
            Q(project=saved_variants[0].family.project) | Q(project__isnull=True)
        )
        create_seqr_model(
            VariantTag,
            variant_tag_type=variant_tag_type,
            saved_variants=saved_variants,
            search_hash=tags_json.get('searchHash'),
            created_by=user,
        )


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_saved_variant_json(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    updated_saved_variant_guids = update_project_saved_variant_json(project)

    return create_json_response({variant_guid: None for variant_guid in updated_saved_variant_guids})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_main_transcript(request, variant_guid, transcript_id):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.family.project, request.user, CAN_EDIT)

    saved_variant.selected_main_transcript_id = transcript_id
    saved_variant.save()

    return create_json_response({'savedVariantsByGuid': {variant_guid: {'selectedMainTranscriptId': transcript_id}}})


def _saved_variant_genes(variants):
    gene_ids = set()
    for variant in variants:
        if isinstance(variant, list):
            for compound_het in variant:
                gene_ids.update(compound_het['transcripts'].keys())
        else:
            gene_ids.update(variant['transcripts'].keys())
    genes = get_genes(gene_ids, add_dbnsfp=True, add_omim=True, add_constraints=True, add_primate_ai=True)
    for gene in genes.values():
        if gene:
            gene['locusListGuids'] = []
    return genes


def _add_locus_lists(projects, variants, genes):
    locus_lists = set()
    for project in projects:
        locus_lists.update(get_project_locus_list_models(project))
    for variant in variants:
        if isinstance(variant, list):
            for compound_het in variant:
                compound_het['locusListGuids'] = []
        else:
            variant['locusListGuids'] = []

    locus_list_intervals_by_chrom = defaultdict(list)
    for interval in LocusListInterval.objects.filter(locus_list__in=locus_lists):
        locus_list_intervals_by_chrom[interval.chrom].append(interval)
    if locus_list_intervals_by_chrom:
        for variant in variants:
            for interval in locus_list_intervals_by_chrom[variant['chrom']]:
                pos = variant['pos'] if variant['genomeVersion'] == interval.genome_version else variant['liftedOverPos']
                if pos and interval.start <= int(pos) <= interval.end:
                    variant['locusListGuids'].append(interval.locus_list.guid)

    for locus_list_gene in LocusListGene.objects.filter(locus_list__in=locus_lists, gene_id__in=genes.keys()).prefetch_related('locus_list'):
        genes[locus_list_gene.gene_id]['locusListGuids'].append(locus_list_gene.locus_list.guid)

    return [locus_list.guid for locus_list in locus_lists]