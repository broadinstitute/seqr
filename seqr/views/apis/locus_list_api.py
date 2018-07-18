import json
import logging

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from guardian.shortcuts import get_group_perms, assign_perm, remove_perm, get_objects_for_group


from seqr.models import LocusList, LocusListGene, LocusListInterval, CAN_VIEW, CAN_EDIT
from seqr.model_utils import create_seqr_model, delete_seqr_model
from seqr.utils.xpos_utils import get_xpos
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.gene_utils import get_genes, get_gene_symbols_to_gene_ids
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_locus_lists, get_json_for_locus_list, get_json_for_locus_list_intervals
from seqr.views.utils.permissions_utils import get_project_and_check_permissions

logger = logging.getLogger(__name__)


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

    new_genes, invalid_gene_symbols, existing_gene_ids = _parse_requested_genes(request_json)
    if not new_genes:
        return create_json_response({'invalidLocusListItems': invalid_gene_symbols}, status=400, reason="Genes are required")

    locus_list = create_seqr_model(
        LocusList,
        name=name,
        description=request_json.get('description') or '',
        is_public=request_json.get('isPublic') or False,
        created_by=request.user,
    )

    for gene_id in new_genes.keys():
        create_seqr_model(
            LocusListGene,
            locus_list=locus_list,
            gene_id=gene_id,
            created_by=request.user,
        )

    new_intervals, invalid_intervals, existing_interval_ids = _parse_requested_intervals(request_json)

    for interval in new_intervals:
        LocusListInterval.objects.create(
            locus_list=locus_list,
            genome_version=interval.get('genomeVersion'),
            chrom=interval['chrom'],
            start=interval['start'],
            end=interval['end'],
        )

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: get_json_for_locus_list(locus_list, request.user)},
        'genesById': new_genes,
        'invalidLocusListItems': invalid_gene_symbols + invalid_intervals,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_locus_list_handler(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)
    if not locus_list.created_by == request.user:
        raise PermissionDenied('User does not have permission to edit locus list {}'.format(locus_list.name))

    request_json = json.loads(request.body)

    # Update list metadata
    update_model_from_json(locus_list, request_json, allow_unknown_keys=True)

    # Update genes
    new_genes, invalid_gene_symbols, existing_gene_ids = _parse_requested_genes(request_json)
    for locus_list_gene in locus_list.locuslistgene_set.exclude(gene_id__in=existing_gene_ids):
        delete_seqr_model(locus_list_gene)

    for gene_id in new_genes.keys():
        create_seqr_model(
            LocusListGene,
            locus_list=locus_list,
            gene_id=gene_id,
            created_by=request.user,
        )

    # Update intervals
    new_intervals, invalid_intervals, existing_intervals = _parse_requested_intervals(request_json)

    locus_list.locuslistinterval_set.exclude(guid__in=existing_intervals.keys()).delete()
    for interval in new_intervals:
        LocusListInterval.objects.create(
            locus_list=locus_list,
            genome_version=interval.get('genomeVersion'),
            chrom=interval['chrom'],
            start=interval['start'],
            end=interval['end'],
        )
    for interval in existing_intervals.values():
        interval_model = LocusListInterval.objects.get(guid=interval['locusListIntervalGuid'])
        interval_model.genome_version = interval.get('genomeVersion')
        interval_model.chrom = interval['chrom']
        interval_model.start = interval['start']
        interval_model.end = interval['end']
        interval_model.save()

    locus_list_json = get_json_for_locus_list(locus_list, request.user)
    locus_list_json['geneIds'] = new_genes.keys() + existing_gene_ids
    locus_list_json['intervals'] = get_json_for_locus_list_intervals(locus_list.locuslistinterval_set.all())

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: locus_list_json},
        'genesById': new_genes,
        'invalidLocusListItems': invalid_gene_symbols + invalid_intervals,
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

    return create_json_response({
        'locusListGuids': [locus_list['locusListGuid'] for locus_list in get_sorted_project_locus_lists(project, request.user)],
    })


def get_project_locus_list_models(project):
    return get_objects_for_group(project.can_view_group, CAN_VIEW, LocusList)


def get_sorted_project_locus_lists(project, user):
    result = get_json_for_locus_lists(get_project_locus_list_models(project), user)
    return sorted(result, key=lambda locus_list: locus_list['name'])


def _parse_requested_genes(request_json):
    requested_genes = request_json.get('genes') or []
    existing_gene_ids = [gene.get('geneId') for gene in requested_genes if gene.get('geneId')]
    gene_symbols_to_ids = get_gene_symbols_to_gene_ids([gene.get('symbol') for gene in requested_genes if not gene.get('geneId')])
    invalid_gene_symbols = [symbol for symbol, gene_id in gene_symbols_to_ids.items() if not gene_id]
    new_genes = get_genes([gene_id for gene_id in gene_symbols_to_ids.values() if gene_id])
    return new_genes, invalid_gene_symbols, existing_gene_ids


def _parse_requested_intervals(request_json):
    requested_intervals = request_json.get('intervals') or []
    existing_intervals = {}
    invalid_intervals = []
    new_intervals = []
    for interval in requested_intervals:
        if interval.get('locusListIntervalGuid'):
            existing_intervals[interval.get('locusListIntervalGuid')] = interval
        else:
            try:
                interval['start'] = int(interval['start'])
                interval['end'] = int(interval['end'])
                if interval['start'] > interval['end']:
                    raise ValueError
                get_xpos(interval['chrom'], int(interval['start']))
                new_intervals.append(interval)
            except (KeyError, ValueError):
                invalid_intervals.append('chr{chrom}:{start}-{end}'.format(
                    chrom=interval.get('chrom', '?'), start=interval.get('start', '?'), end=interval.get('end', '?')
                ))

    return new_intervals, invalid_intervals, existing_intervals
