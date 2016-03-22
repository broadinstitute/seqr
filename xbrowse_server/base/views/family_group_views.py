import json

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

from xbrowse.utils import get_gene_id_from_str
from xbrowse_server.base import forms as base_forms
from xbrowse_server import server_utils
from xbrowse_server import json_displays
from xbrowse_server.base.forms import AddFamilyGroupForm
from xbrowse_server.base.models import Project, FamilyGroup, ANALYSIS_STATUS_CHOICES
from xbrowse_server.decorators import log_request
from xbrowse_server.analysis import family_group as family_group_analysis
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.mall import get_reference
from xbrowse_server import mall


@login_required
@log_request('family_groups')
def family_groups(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    _family_groups = project.get_family_groups()

    return render(request, 'family_group/family_groups.html', {
        'project': project,
        'family_groups': _family_groups,
    })

@login_required
@log_request('add_family_group')
def add_family_group(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    families_json = json_displays.family_list(project.get_families())

    return render(request, 'family_group/add_family_group.html', {
        'project': project,
        'families_json': json.dumps(families_json),
    })


@login_required
@log_request('add_family_group_submit')
@csrf_exempt
def add_family_group_submit(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    error = None

    form = AddFamilyGroupForm(project, request.POST)
    if form.is_valid():
        # todo: move to sample_anagement
        family_group = FamilyGroup.objects.create(
            project=project,
            slug=form.cleaned_data['family_group_slug'],
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description'],
        )
        for family in form.cleaned_data['families']:
            family_group.families.add(family)
    else:
        error = server_utils.form_error_string(form)

    if error:
        return server_utils.JSONResponse({'is_error': True, 'error': error})
    else:
        return server_utils.JSONResponse({'is_error': False, 'new_url': reverse('family_group_home', args=(project.project_id, family_group.slug))})


@login_required
@log_request('family_group_home')
def family_group_home(request, project_id, family_group_slug):

    project = get_object_or_404(Project, project_id=project_id)
    family_group = get_object_or_404(FamilyGroup, project=project, slug=family_group_slug)
    if not project.can_view(request.user):
        raise PermissionDenied

    return render(request, 'family_group/family_group_home.html', {
        'project': project,
        'family_group': family_group,
        'families_json': json.dumps(json_displays.family_list(family_group.get_families())),
        'analysis_statuses':  json.dumps(dict(ANALYSIS_STATUS_CHOICES)),
    })


@login_required
@log_request('family_group_edit')
def family_group_edit(request, project_id, family_group_slug):

    project = get_object_or_404(Project, project_id=project_id)
    family_group = get_object_or_404(FamilyGroup, project=project, slug=family_group_slug)
    if not project.can_admin(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        form = base_forms.EditFamilyGroupForm(project, request.POST)
        if form.is_valid():
            family_group.name = form.cleaned_data['name']
            family_group.description = form.cleaned_data['description']
            family_group.slug = form.cleaned_data['slug']
            family_group.save()
            return redirect('family_group_home', project.project_id, family_group.slug)

    else:
        form = base_forms.EditFamilyGroupForm(project, initial={
            'name': family_group.name,
            'description': family_group.description,
        })

    return render(request, 'family_group/family_group_edit.html', {
        'project': project,
        'family_group': family_group,
        'form': form,
    })


@login_required()
def delete(request, project_id, family_group_slug):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    family_group = get_object_or_404(FamilyGroup, project=project, slug=family_group_slug)
    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            family_group.delete()
            return redirect('family_groups', project_id)

    return render(request, 'family_group/delete.html', {
        'project': project,
        'family_group': family_group,
    })



@login_required
@log_request('combine_mendelian_families')
def combine_mendelian_families(request, project_id, family_group_slug):

    project = get_object_or_404(Project, project_id=project_id)
    family_group = get_object_or_404(FamilyGroup, project=project, slug=family_group_slug)
    if not project.can_view(request.user):
        raise PermissionDenied

    return render(request, 'family_group/combine_mendelian_families.html', {
        'project': project,
        'family_group': family_group,
        'family_group_json': json.dumps(family_group.toJSON()),
    })


@login_required
@log_request('family_group_gene')
def family_group_gene(request, project_id, family_group_slug, gene_id):

    project = get_object_or_404(Project, project_id=project_id)
    family_group = get_object_or_404(FamilyGroup, project=project, slug=family_group_slug)
    if not project.can_view(request.user):
        raise PermissionDenied

    gene_id = get_gene_id_from_str(gene_id, get_reference())
    gene = get_reference().get_gene(gene_id)

    varfilter = get_default_variant_filter('all_coding', mall.get_annotator().reference_population_slugs)
    variants_by_family = family_group_analysis.get_variants_in_gene(family_group, gene_id, variant_filter=varfilter)

    return render(request, 'family_group/family_group_gene.html', {
        'project': project,
        'family_group': family_group,
        'family_group_json': json.dumps(family_group.toJSON()),
        'gene_json': json.dumps(gene),
        'gene': gene,
        'variants_by_family_json': json.dumps(variants_by_family),
    })


