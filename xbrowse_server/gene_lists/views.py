import csv
import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from xbrowse_server.base.model_utils import update_xbrowse_model, create_xbrowse_model, delete_xbrowse_model
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
        'new_page_url': '/gene_lists',
    })


@login_required
def add(request):
    if request.method == 'POST':
        form = GeneListForm(request.POST)
        if form.is_valid():
            unique_slug = form.cleaned_data['slug']
            while GeneList.objects.filter(slug=unique_slug):
                unique_slug += "_"

            new_list = create_xbrowse_model(GeneList,
                slug=unique_slug,
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                is_public=form.cleaned_data['is_public'],
                owner=request.user,
                last_updated=datetime.datetime.now(),
            )
            for gene_id in form.cleaned_data['gene_ids']:
                create_xbrowse_model(GeneListItem, gene_list=new_list, gene_id=gene_id)
            return redirect('gene_list', slug=new_list.slug)
    else:
        form = GeneListForm()

    return render(request, 'gene_lists/add.html', {
        'form': form,
        'new_page_url': '/gene_lists',
    })



@login_required
def gene_list(request, slug):
    if request.GET.get('guid'):
        lookup_kwargs = {'seqr_locus_list__guid': slug}
    else:
        lookup_kwargs = {'slug': slug}

    _gene_list = get_object_or_404(GeneList, **lookup_kwargs)

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
        'new_page_url': '/gene_lists/{}'.format(_gene_list.seqr_locus_list.guid) if _gene_list.seqr_locus_list else None,
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

            for gene_list_item in GeneListItem.objects.filter(gene_list=gene_list):
                delete_xbrowse_model(gene_list_item)

            for gene_id in form.cleaned_data['gene_ids']:
                create_xbrowse_model(GeneListItem, gene_list=gene_list, gene_id=gene_id)
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
        'new_page_url': '/gene_lists/{}'.format(gene_list.seqr_locus_list.guid) if gene_list.seqr_locus_list else None,
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
        delete_xbrowse_model(_gene_list)
        return redirect('gene_lists_home')

    return render(request, 'gene_lists/delete.html', {
        'gene_list': _gene_list,
        'new_page_url': '/gene_lists/{}'.format(_gene_list.seqr_locus_list.guid) if _gene_list.seqr_locus_list else None,
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
