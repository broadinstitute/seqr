import json
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from guardian.shortcuts import assign_perm, remove_perm, get_objects_for_group


from reference_data.models import GENOME_VERSION_GRCh37
from seqr.models import LocusList, LocusListGene, LocusListInterval, IS_OWNER, CAN_VIEW, CAN_EDIT
from seqr.model_utils import get_or_create_seqr_model, create_seqr_model, delete_seqr_model, \
    add_xbrowse_project_gene_lists, remove_xbrowse_project_gene_lists
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.utils.gene_utils import get_genes, parse_locus_list_items
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_locus_lists, get_json_for_locus_list
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_object_permissions, check_public_object_permissions

logger = logging.getLogger(__name__)

INVALID_ITEMS_ERROR = 'This list contains invalid genes/ intervals. Update them, or select the "Ignore invalid genes and intervals" checkbox to ignore.'


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def locus_lists(request):
    locus_lists = LocusList.objects.filter(Q(is_public=True) | Q(created_by=request.user))
    locus_lists_json = get_json_for_locus_lists(locus_lists, request.user)

    return create_json_response({
        'locusListsByGuid': {locus_list['locusListGuid']: locus_list for locus_list in locus_lists_json}
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def locus_list_info(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)

    check_public_object_permissions(locus_list, request.user)

    locus_list_json = get_json_for_locus_list(locus_list, request.user)
    gene_ids = [item['geneId'] for item in locus_list_json['items'] if item.get('geneId')]
    return create_json_response({
        'locusListsByGuid': {locus_list_guid: locus_list_json},
        'genesById': get_genes(gene_ids, add_dbnsfp=True, add_omim=True, add_constraints=True)
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_locus_list_handler(request):
    request_json = json.loads(request.body)

    if not request_json.get('name'):
        return create_json_response({}, status=400, reason='"Name" is required')

    genes_by_id, intervals, invalid_items = parse_locus_list_items(request_json)
    if invalid_items and not request_json.get('ignoreInvalidItems'):
        return create_json_response({'invalidLocusListItems': invalid_items}, status=400, reason=INVALID_ITEMS_ERROR)

    locus_list = create_seqr_model(
        LocusList,
        name=request_json['name'],
        description=request_json.get('description') or '',
        is_public=request_json.get('isPublic') or False,
        created_by=request.user,
    )
    _update_locus_list_items(locus_list, genes_by_id, intervals, request_json, request.user)
    add_locus_list_user_permissions(locus_list)

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: get_json_for_locus_list(locus_list, request.user)},
        'genesById': genes_by_id,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_locus_list_handler(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)
    check_object_permissions(locus_list, request.user, permission_level=CAN_EDIT)

    request_json = json.loads(request.body)

    genes_by_id, intervals, invalid_items = parse_locus_list_items(request_json)
    if invalid_items and not request_json.get('ignoreInvalidItems'):
        return create_json_response({'invalidLocusListItems': invalid_items}, status=400, reason=INVALID_ITEMS_ERROR)

    update_model_from_json(locus_list, request_json, allow_unknown_keys=True)
    if genes_by_id is not None:
        _update_locus_list_items(locus_list, genes_by_id, intervals, request_json, request.user)

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: get_json_for_locus_list(locus_list, request.user)},
        'genesById': genes_by_id or {},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_locus_list_handler(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)
    check_object_permissions(locus_list, request.user, permission_level=CAN_EDIT)

    delete_seqr_model(locus_list)
    return create_json_response({'locusListsByGuid': {locus_list_guid: None}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def add_project_locus_lists(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)
    request_json = json.loads(request.body)
    locus_lists = LocusList.objects.filter(guid__in=request_json['locusListGuids'])
    for locus_list in locus_lists:
        assign_perm(user_or_group=project.can_view_group, perm=CAN_VIEW, obj=locus_list)
    add_xbrowse_project_gene_lists(project, locus_lists)

    return create_json_response({
        'locusListGuids': [locus_list['locusListGuid'] for locus_list in get_sorted_project_locus_lists(project, request.user)],
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project_locus_lists(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, CAN_EDIT)
    request_json = json.loads(request.body)
    locus_lists = LocusList.objects.filter(guid__in=request_json['locusListGuids'])
    for locus_list in locus_lists:
        remove_perm(user_or_group=project.can_view_group, perm=CAN_VIEW, obj=locus_list)
    remove_xbrowse_project_gene_lists(project, locus_lists)

    return create_json_response({
        'locusListGuids': [locus_list['locusListGuid'] for locus_list in get_sorted_project_locus_lists(project, request.user)],
    })


def get_project_locus_list_models(project):
    return get_objects_for_group(project.can_view_group, CAN_VIEW, LocusList)


def get_sorted_project_locus_lists(project, user):
    result = get_json_for_locus_lists(get_project_locus_list_models(project), user)
    return sorted(result, key=lambda locus_list: locus_list['name'])


def add_locus_list_user_permissions(locus_list):
    assign_perm(user_or_group=locus_list.created_by, perm=IS_OWNER, obj=locus_list)
    assign_perm(user_or_group=locus_list.created_by, perm=CAN_EDIT, obj=locus_list)
    assign_perm(user_or_group=locus_list.created_by, perm=CAN_VIEW, obj=locus_list)


def _update_locus_list_items(locus_list, genes_by_id, intervals, request_json, user):
    # Update genes
    for locus_list_gene in locus_list.locuslistgene_set.exclude(gene_id__in=genes_by_id.keys()):
        delete_seqr_model(locus_list_gene)

    for gene_id in genes_by_id.keys():
        get_or_create_seqr_model(
            LocusListGene,
            locus_list=locus_list,
            gene_id=gene_id,
            created_by=user,
        )

    # Update intervals
    genome_version = request_json.get('intervalGenomeVersion') or GENOME_VERSION_GRCh37
    interval_guids = set()
    for interval in intervals:
        interval_model, _ = LocusListInterval.objects.get_or_create(
            locus_list=locus_list,
            chrom=interval['chrom'],
            start=interval['start'],
            end=interval['end'],
            genome_version=genome_version,
        )
        interval_guids.add(interval_model.guid)
    locus_list.locuslistinterval_set.exclude(guid__in=interval_guids).delete()
