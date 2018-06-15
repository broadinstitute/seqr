import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from seqr.models import GeneNote
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_gene_note

from xbrowse_server.mall import get_reference

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def gene_info(request, gene_id):
    # TODO create new reference data handler for seqr
    reference = get_reference()

    gene = reference.get_gene(gene_id)
    gene['expression'] = reference.get_tissue_expression_display_values(gene_id)
    gene['notes'] = [get_json_for_gene_note(note, request.user) for note in GeneNote.objects.filter(gene_id=gene_id)]

    return create_json_response({gene_id: gene})
