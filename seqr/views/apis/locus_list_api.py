import json
import logging

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from guardian.shortcuts import get_group_perms, assign_perm, get_objects_for_group


from seqr.models import LocusList, LocusListGene, CAN_VIEW, CAN_EDIT
from seqr.model_utils import create_seqr_model, delete_seqr_model
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.gene_utils import get_genes, get_gene_symbols_to_gene_ids
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_locus_lists, get_json_for_locus_list
from seqr.views.utils.permissions_utils import get_project_and_check_permissions


logger = logging.getLogger(__name__)

# TODO gene intervals


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

    if request.GET.get('projectGuid'):
        project = get_project_and_check_permissions(request.GET.get('projectGuid'), request.user)
        if not get_group_perms(project.can_view_group, locus_list).filter(name=CAN_VIEW):
            raise PermissionDenied('Project {} does not have access to locus list {}'.format(project.name, locus_list.name))
    elif not (locus_list.is_public or locus_list.created_by == request.user):
        raise PermissionDenied('User does not have access to locus list {}'.format(locus_list.name))

    locus_list_json = get_json_for_locus_list(locus_list, request.user)
    return create_json_response({
        'locusListsByGuid': {locus_list_guid: locus_list_json},
        'genesById': get_genes(locus_list_json['geneIds'])
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_locus_list_handler(request):
    request_json = json.loads(request.body)

    name = request_json.get('name')
    if not name:
        return create_json_response({}, status=400, reason="'Name' is required")

    requested_genes = request_json.get('genes') or []
    gene_symbols_to_ids = get_gene_symbols_to_gene_ids([gene.get('symbol') for gene in requested_genes])
    invalid_gene_symbols = [symbol for symbol, gene_id in gene_symbols_to_ids.items() if not gene_id]
    genes = get_genes([gene_id for gene_id in gene_symbols_to_ids.values() if gene_id])
    if not genes:
        return create_json_response({'invalidGeneSymbols': invalid_gene_symbols}, status=400, reason="Genes are required")

    locus_list = create_seqr_model(
        LocusList,
        name=name,
        description=request_json.get('description') or '',
        is_public=request_json.get('isPublic') or False,
        created_by=request.user,
    )

    for gene_id in genes.keys():
        create_seqr_model(
            LocusListGene,
            locus_list=locus_list,
            gene_id=gene_id,
            created_by=request.user,
        )

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: get_json_for_locus_list(locus_list, request.user)},
        'genesById': genes,
        'invalidGeneSymbols': invalid_gene_symbols,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_locus_list_handler(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)
    if not locus_list.created_by == request.user:
        raise PermissionDenied('User does not have permission to edit locus list {}'.format(locus_list.name))

    request_json = json.loads(request.body)
    update_model_from_json(locus_list, request_json, allow_unknown_keys=True)

    requested_genes = request_json.get('genes') or []
    existing_gene_ids = [gene.get('geneId') for gene in requested_genes if gene.get('geneId')]
    gene_symbols_to_ids = get_gene_symbols_to_gene_ids([gene.get('symbol') for gene in requested_genes if not gene.get('geneId')])
    invalid_gene_symbols = [symbol for symbol, gene_id in gene_symbols_to_ids.items() if not gene_id]
    new_gene_ids = [gene_id for gene_id in gene_symbols_to_ids.values() if gene_id]

    for locus_list_gene in locus_list.locuslistgene_set.exclude(gene_id__in=existing_gene_ids):
        delete_seqr_model(locus_list_gene)

    for gene_id in new_gene_ids:
        create_seqr_model(
            LocusListGene,
            locus_list=locus_list,
            gene_id=gene_id,
            created_by=request.user,
        )

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: get_json_for_locus_list(locus_list, request.user)},
        'genesById': get_genes(new_gene_ids),
        'invalidGeneSymbols': invalid_gene_symbols,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_locus_list_handler(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)
    if not locus_list.created_by == request.user:
        raise PermissionDenied('User does not have permission to delete locus list {}'.format(locus_list.name))

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

    return create_json_response({
        'locusLists': get_sorted_project_locus_lists(project, request.user),
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project_locus_lists(request, project_guid):
    pass


def get_sorted_project_locus_lists(project, user):
    result = get_json_for_locus_lists(get_objects_for_group(project.can_view_group, CAN_VIEW, LocusList), user)
    return sorted(result, key=lambda locus_list: locus_list['createdDate'])