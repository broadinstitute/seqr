import json
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count


from reference_data.models import GENOME_VERSION_GRCh37
from seqr.models import LocusList, LocusListGene, LocusListInterval
from seqr.utils.gene_utils import get_genes, parse_locus_list_items
from seqr.utils.logging_utils import log_model_update
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json, \
    create_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_locus_lists, get_json_for_locus_list
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_multi_project_permissions, \
    check_user_created_object_permissions
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)

INVALID_ITEMS_ERROR = 'This list contains invalid genes/ intervals. Update them, or select the "Ignore invalid genes and intervals" checkbox to ignore.'


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def locus_lists(request):
    if request.user.is_staff:
        locus_list_models = LocusList.objects.all()
    else:
        locus_list_models = LocusList.objects.filter(Q(is_public=True) | Q(created_by=request.user))
    locus_list_models = locus_list_models.annotate(num_projects=Count('projects'))

    locus_lists_json = get_json_for_locus_lists(locus_list_models, request.user, include_project_count=True)

    return create_json_response({
        'locusListsByGuid': {locus_list['locusListGuid']: locus_list for locus_list in locus_lists_json}
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def locus_list_info(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)

    if not locus_list.is_public:
        check_multi_project_permissions(locus_list, request.user)

    locus_list_json = get_json_for_locus_list(locus_list, request.user)
    gene_ids = [item['geneId'] for item in locus_list_json['items'] if item.get('geneId')]
    return create_json_response({
        'locusListsByGuid': {locus_list_guid: locus_list_json},
        'genesById': get_genes(gene_ids, add_dbnsfp=True, add_omim=True, add_constraints=True)
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def create_locus_list_handler(request):
    request_json = json.loads(request.body)

    if not request_json.get('name'):
        return create_json_response({}, status=400, reason='"Name" is required')

    genes_by_id, intervals, invalid_items = parse_locus_list_items(request_json)
    if invalid_items and not request_json.get('ignoreInvalidItems'):
        return create_json_response({'invalidLocusListItems': invalid_items}, status=400, reason=INVALID_ITEMS_ERROR)

    locus_list = create_model_from_json(LocusList, {
        'name': request_json['name'],
        'description': request_json.get('description') or '',
        'is_public': request_json.get('isPublic') or False,
    }, request.user)
    _update_locus_list_items(locus_list, genes_by_id, intervals, request_json, request.user)

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: get_json_for_locus_list(locus_list, request.user)},
        'genesById': genes_by_id,
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_locus_list_handler(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)
    check_user_created_object_permissions(locus_list, request.user)

    request_json = json.loads(request.body)

    genes_by_id, intervals, invalid_items = parse_locus_list_items(request_json)
    if invalid_items and not request_json.get('ignoreInvalidItems'):
        return create_json_response({'invalidLocusListItems': invalid_items}, status=400, reason=INVALID_ITEMS_ERROR)

    update_model_from_json(locus_list, request_json, user=request.user, allow_unknown_keys=True)
    if genes_by_id is not None:
        _update_locus_list_items(locus_list, genes_by_id, intervals, request_json, request.user)

    return create_json_response({
        'locusListsByGuid': {locus_list.guid: get_json_for_locus_list(locus_list, request.user)},
        'genesById': genes_by_id or {},
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def delete_locus_list_handler(request, locus_list_guid):
    locus_list = LocusList.objects.get(guid=locus_list_guid)
    locus_list.delete_model(request.user)
    return create_json_response({'locusListsByGuid': {locus_list_guid: None}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def add_project_locus_lists(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    request_json = json.loads(request.body)
    locus_lists = LocusList.objects.filter(guid__in=request_json['locusListGuids'])
    for locus_list in locus_lists:
        locus_list.projects.add(project)
        locus_list.save()
    log_model_update(logger, project, user=request.user, update_type='update', update_fields=['locus_lists'])

    return create_json_response({
        'locusListGuids': [locus_list['locusListGuid'] for locus_list in _get_sorted_project_locus_lists(project, request.user)],
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def delete_project_locus_lists(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    request_json = json.loads(request.body)
    locus_lists = LocusList.objects.filter(guid__in=request_json['locusListGuids'])
    for locus_list in locus_lists:
        locus_list.projects.remove(project)
        locus_list.save()
    log_model_update(logger, project, user=request.user, update_type='update', update_fields=['locus_lists'])


    return create_json_response({
        'locusListGuids': [locus_list['locusListGuid'] for locus_list in _get_sorted_project_locus_lists(project, request.user)],
    })


def _update_locus_list_items(locus_list, genes_by_id, intervals, request_json, user):
    # Update genes
    LocusList.bulk_delete(user, queryset=locus_list.locuslistgene_set.exclude(gene_id__in=genes_by_id.keys()))

    for gene_id in genes_by_id.keys():
        get_or_create_model_from_json(
            LocusListGene, {'locus_list': locus_list, 'gene_id': gene_id}, update_json=None, user=user)

    # Update intervals
    genome_version = request_json.get('intervalGenomeVersion') or GENOME_VERSION_GRCh37
    interval_guids = set()
    for interval in intervals:
        interval_model, _ = get_or_create_model_from_json(LocusListInterval, {
            'locus_list': locus_list,
            'chrom': interval['chrom'],
            'start': interval['start'],
            'end': interval['end'],
            'genome_version': genome_version,
        }, update_json=None, user=user)

        interval_guids.add(interval_model.guid)

    LocusList.bulk_delete(user, queryset=locus_list.locuslistinterval_set.exclude(guid__in=interval_guids))


def _get_sorted_project_locus_lists(project, user):
    result = get_json_for_locus_lists(LocusList.objects.filter(projects__id=project.id), user)
    return sorted(result, key=lambda locus_list: locus_list['name'])
