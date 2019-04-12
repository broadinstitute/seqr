import json

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

from xbrowse_server.base import forms as base_forms
from xbrowse_server import server_utils
from xbrowse_server import json_displays
from xbrowse_server.base.forms import AddFamilyGroupForm
from xbrowse_server.base.models import Project, FamilyGroup, ANALYSIS_STATUS_CHOICES
from xbrowse_server.base.model_utils import update_xbrowse_model, get_or_create_xbrowse_model, delete_xbrowse_model, \
    find_matching_seqr_model
from xbrowse_server.decorators import log_request


def redirect_family_group_guid(request, project_id, family_group_guid, path):
    family_group = get_object_or_404(FamilyGroup, seqr_analysis_group__guid=family_group_guid)
    return redirect('/project/{project_id}/family-group/{family_group_slug}{path}'.format(
        project_id=project_id, family_group_slug=family_group.slug, path='/{}'.format(path) if path else ''
    ))


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
        'new_page_url': '/project/{}/project_page'.format(project.seqr_project.guid) if project.seqr_project else None,
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
        'new_page_url': '/project/{}/project_page'.format(project.seqr_project.guid) if project.seqr_project else None,
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
        family_group, created = get_or_create_xbrowse_model(
            FamilyGroup,
            project=project,
            slug=form.cleaned_data['family_group_slug'],
        )
        update_xbrowse_model(family_group, name=form.cleaned_data['name'], description=form.cleaned_data['description'])

        seqr_analysis_group = find_matching_seqr_model(family_group)
        for family in form.cleaned_data['families']:
            family_group.families.add(family)
            seqr_analysis_group.families.add(find_matching_seqr_model(family))
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
    if not project.can_view(request.user):
        raise PermissionDenied

    family_group = get_object_or_404(FamilyGroup, project=project, slug=family_group_slug)

    return render(request, 'family_group/family_group_home.html', {
        'project': project,
        'family_group': family_group,
        'families_json': json.dumps(json_displays.family_list(family_group.get_families())),
        'analysis_statuses':  json.dumps(dict(ANALYSIS_STATUS_CHOICES)),
        'new_page_url': '/project/{}/analysis_group/{}'.format(project.seqr_project.guid, family_group.seqr_analysis_group.guid) if project.seqr_project and family_group.seqr_analysis_group else None,
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
            update_xbrowse_model(
                family_group,
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                slug=form.cleaned_data['slug']
            )
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
        'new_page_url': '/project/{}/analysis_group/{}'.format(project.seqr_project.guid, family_group.seqr_analysis_group.guid) if project.seqr_project and family_group.seqr_analysis_group else None,
    })


@login_required()
def delete(request, project_id, family_group_slug):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    family_group = get_object_or_404(FamilyGroup, project=project, slug=family_group_slug)
    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            delete_xbrowse_model(family_group)
            return redirect('family_groups', project_id)

    return render(request, 'family_group/delete.html', {
        'project': project,
        'family_group': family_group,
        'new_page_url': '/project/{}/analysis_group/{}'.format(project.seqr_project.guid, family_group.seqr_analysis_group.guid) if project.seqr_project and family_group.seqr_analysis_group else None,
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
        'new_page_url': '/variant_search/analysis_group/{0}'.format(family_group.seqr_analysis_group.guid)
        if family_group.seqr_analysis_group and family_group.seqr_analysis_group.project.has_new_search else None,
    })
