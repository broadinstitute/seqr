import json
import logging

from seqr.models import GeneNote
from seqr.utils.gene_utils import get_gene, get_genes_with_detail
from seqr.views.utils.json_to_orm_utils import update_model_from_json, create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_gene_notes_by_gene_id
from seqr.views.utils.permissions_utils import check_user_created_object_permissions, login_and_policies_required


logger = logging.getLogger(__name__)


@login_and_policies_required
def genes_info(request):
    gene_ids = request.GET.get('geneIds', '').split(',')
    return create_json_response({'genesById': get_genes_with_detail(gene_ids, request.user)})


@login_and_policies_required
def gene_info(request, gene_id):
    gene = get_gene(gene_id, request.user)

    return create_json_response({'genesById': {gene_id: gene}})


@login_and_policies_required
def create_gene_note_handler(request, gene_id):
    request_json = json.loads(request.body)
    create_model_from_json(GeneNote, {'note': request_json.get('note'), 'gene_id': gene_id}, request.user)

    return create_json_response({'genesById': {gene_id: {
        'notes': _get_gene_notes(gene_id, request.user)
    }}})


@login_and_policies_required
def update_gene_note_handler(request, gene_id, note_guid):
    note = GeneNote.objects.get(guid=note_guid)
    check_user_created_object_permissions(note, request.user)

    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, user=request.user, allow_unknown_keys=True)

    return create_json_response({'genesById': {gene_id: {
        'notes': _get_gene_notes(gene_id, request.user)
    }}})


@login_and_policies_required
def delete_gene_note_handler(request, gene_id, note_guid):
    note = GeneNote.objects.get(guid=note_guid)
    note.delete_model(request.user)
    return create_json_response({'genesById': {gene_id: {
        'notes': _get_gene_notes(gene_id, request.user)
    }}})


def _get_gene_notes(gene_id, user):
    return get_json_for_gene_notes_by_gene_id([gene_id], user).get(gene_id, [])
