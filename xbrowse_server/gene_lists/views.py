import csv
import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from xbrowse_server.base.model_utils import update_xbrowse_model
from xbrowse_server.gene_lists.forms import GeneListForm

from xbrowse_server.gene_lists.models import GeneList, GeneListItem
from django.core.exceptions import PermissionDenied


@login_required
def home(request):
    user_lists = GeneList.objects.filter(owner=request.user)
    public_lists = GeneList.objects.filter(is_public=True)

    return render(request, 'gene_lists/home.html', {
        'user_lists': user_lists,
        'public_lists': public_lists,
    })


@login_required
def add(request):
    if request.method == 'POST':
        form = GeneListForm(request.POST)
        if form.is_valid():
            unique_slug = form.cleaned_data['slug']
            while GeneList.objects.filter(slug=unique_slug):
                unique_slug += "_"

            new_list = GeneList.objects.create(
                slug=unique_slug,
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                is_public=form.cleaned_data['is_public'],
                owner=request.user,
                last_updated=datetime.datetime.now(),
            )
            for gene_id in form.cleaned_data['gene_ids']:
                GeneListItem.objects.create(gene_list=new_list, gene_id=gene_id)
            return redirect('gene_list', slug=new_list.slug)
    else:
        form = GeneListForm()

    return render(request, 'gene_lists/add.html', {
        'form': form,
    })



@login_required
def gene_list(request, slug):
    _gene_list = get_object_or_404(GeneList, slug=slug)

    authorized = False
    if _gene_list.is_public:
        authorized = True
    if _gene_list.owner == request.user:
        authorized = True
    if not authorized:
        raise PermissionDenied

    return render(request, 'gene_lists/gene_list.html', {
        'gene_list': _gene_list,
        'genes': _gene_list.get_genes(),
    })


@login_required
def edit(request, slug):
    gene_list = get_object_or_404(GeneList, slug=slug)

    authorized = False
    if gene_list.owner == request.user:
        authorized = True
    if not authorized:
        raise PermissionDenied

    if request.method == 'POST':
        form = GeneListForm(request.POST)
        if form.is_valid():
            update_xbrowse_model(gene_list,
                slug=form.cleaned_data['slug'],
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                is_public=form.cleaned_data['is_public'],
                last_updated = datetime.datetime.now())

            GeneListItem.objects.filter(gene_list=gene_list).delete()
            for gene_id in form.cleaned_data['gene_ids']:
                GeneListItem.objects.create(gene_list=gene_list, gene_id=gene_id)
            return redirect('gene_list', slug=gene_list.slug)
    else:
        form = GeneListForm(initial={
            'name': gene_list.name,
            'description': gene_list.description,
            'is_public': gene_list.is_public,
            'genes': '\n'.join([g['symbol'] for g in gene_list.get_genes()]),
        })

    return render(request, 'gene_lists/edit.html', {
        'form': form,
        'gene_list': gene_list,
    })


@login_required
def delete(request, slug):
    _gene_list = get_object_or_404(GeneList, slug=slug)

    authorized = False
    if _gene_list.owner == request.user:
        authorized = True
    if not authorized:
        raise PermissionDenied

    if request.method == 'POST':
        _gene_list.delete()
        return redirect('gene_lists_home')

    return render(request, 'gene_lists/delete.html', {
        'gene_list': _gene_list,
    })


def download_response(_gene_list):

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    filename = '{}.tsv'.format(_gene_list.slug)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

    writer = csv.writer(response, dialect='excel', delimiter='\t')
    for gene in _gene_list.get_genes():
        writer.writerow([
            gene['gene_id'],
            gene['symbol'],
        ])
    return response



@login_required
def download(request, slug):
    _gene_list = get_object_or_404(GeneList, slug=slug)

    authorized = False
    if _gene_list.is_public:
        authorized = True
    if _gene_list.owner == request.user:
        authorized = True
    if not authorized:
        raise PermissionDenied

    return download_response(_gene_list)
