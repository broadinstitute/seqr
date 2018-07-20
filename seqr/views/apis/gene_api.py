import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import GeneNote
from seqr.model_utils import create_seqr_model, delete_seqr_model
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.gene_utils import get_gene
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_gene_note


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def gene_info(request, gene_id):
    gene = get_gene(gene_id)
    gene['notes'] = _get_gene_notes(gene_id, request.user)

    return create_json_response({gene_id: gene})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_gene_note_handler(request, gene_id):
    request_json = json.loads(request.body)
    create_seqr_model(
        GeneNote,
        note=request_json.get('note'),
        gene_id=gene_id,
        created_by=request.user,
    )

    return create_json_response({gene_id: {
        'notes': _get_gene_notes(gene_id, request.user)
    }})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_gene_note_handler(request, gene_id, note_guid):
    note = GeneNote.objects.get(guid=note_guid)
    if not _can_edit_note(note, request.user):
        raise PermissionDenied("User does not have permission to edit this note")

    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, allow_unknown_keys=True)

    return create_json_response({gene_id: {
        'notes': _get_gene_notes(gene_id, request.user)
    }})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_gene_note_handler(request, gene_id, note_guid):
    note = GeneNote.objects.get(guid=note_guid)
    if not _can_edit_note(note, request.user):
        raise PermissionDenied("User does not have permission to delete this note")

    delete_seqr_model(note)
    return create_json_response({gene_id: {
        'notes': _get_gene_notes(gene_id, request.user)
    }})


def _get_gene_notes(gene_id, user):
    return [get_json_for_gene_note(note, user) for note in GeneNote.objects.filter(gene_id=gene_id)]


def _can_edit_note(note, user):
    return user.is_staff or user == note.created_by