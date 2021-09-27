from seqr.models import GeneNote
from seqr.utils.gene_utils import get_gene, get_genes_with_detail
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.note_utils import create_note_handler, update_note_handler, delete_note_handler
from seqr.views.utils.orm_to_json_utils import get_json_for_gene_notes_by_gene_id
from seqr.views.utils.permissions_utils import login_and_policies_required


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
    return create_note_handler(
        request, GeneNote, parent_fields={'gene_id': gene_id},
        get_response_json=_get_gene_notes_response_func(gene_id, request.user),
    )


@login_and_policies_required
def update_gene_note_handler(request, gene_id, note_guid):
    return update_note_handler(
        request, GeneNote, gene_id, note_guid, parent_field='gene_id',
        get_response_json=_get_gene_notes_response_func(gene_id, request.user),
    )


@login_and_policies_required
def delete_gene_note_handler(request, gene_id, note_guid):
    return delete_note_handler(
        request, GeneNote, gene_id, note_guid, parent_field='gene_id',
        get_response_json=_get_gene_notes_response_func(gene_id, request.user),
    )


def _get_gene_notes_response_func(gene_id, user):
    return lambda *args: {'genesById': {gene_id: {
        'notes': get_json_for_gene_notes_by_gene_id([gene_id], user).get(gene_id, [])
    }}}
