import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings

from xbrowse_server.decorators import log_request
from xbrowse.utils import get_gene_id_from_str
from xbrowse_server.mall import get_reference
from xbrowse_server.api.utils import add_notes_to_genes


@login_required
@log_request('gene_search')
def gene_search(request):
    return render(request, 'gene_search.html', {
        'new_page_url': '/gene_info',
    })


@login_required
@log_request('gene_info')
def gene_info(request, gene_str):

    real_gene_id = get_gene_id_from_str(gene_str, get_reference())
    gene = get_reference().get_gene(real_gene_id)
    gene['expression'] = get_reference().get_tissue_expression_display_values(real_gene_id)
    add_notes_to_genes([gene], request.user)
    gene_json = json.dumps(gene)

    return render(request, 'gene_info.html', {
        'gene_json': gene_json,
        'gene_symbol': gene['symbol'],
        'new_page_url': '/gene_info/{}'.format(gene_str),
    })

