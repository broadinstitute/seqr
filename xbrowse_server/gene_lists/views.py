from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from xbrowse_server.gene_lists.models import GeneList

@login_required
def gene_list(request, slug):

    gene_list = get_object_or_404(GeneList, slug=slug)
    projects = gene_list.get_projects(request.user)

    return render(request, 'gene_lists/gene_list.html', {
        'gene_list': gene_list,
        'genes': gene_list.get_genes(),
        'projects': projects,
    })
