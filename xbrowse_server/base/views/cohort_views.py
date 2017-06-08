import json
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from xbrowse_server.base.models import Project, Cohort
from xbrowse_server.decorators import log_request
from xbrowse_server.base import forms as base_forms
from xbrowse_server import server_utils, json_displays
from xbrowse_server.server_utils import JSONResponse
from django.core.exceptions import PermissionDenied


@login_required
@log_request('family_groups')
def cohorts(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    _cohorts = project.get_cohorts()

    return render(request, 'cohort/cohorts.html', {
        'project': project,
        'cohorts': _cohorts,
    })



@login_required
@log_request('cohort_home')
def cohort_home(request, project_id, cohort_id):

    project = get_object_or_404(Project, project_id=project_id)
    cohort = get_object_or_404(Cohort, project=project, cohort_id=cohort_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    return render(request, 'cohort/cohort_home.html', {
        'project': project,
        'cohort': cohort,
        'user_can_edit': cohort.can_edit(request.user),
    })



@login_required
@csrf_exempt
def add(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        form = base_forms.AddCohortForm(project, request.POST)
        if form.is_valid():
            cohort = Cohort.objects.create(
                project=project,
                cohort_id=form.cleaned_data['cohort_id'],
                display_name=form.cleaned_data['name'],
                short_description=form.cleaned_data['description'],
            )
            for indiv in form.cleaned_data['individuals']:
                cohort.individuals.add(indiv)
            cohort.save()

            # TODO figure out a way to launch variant loading in the background
            #xbrowse_controls.load_variants_for_cohort_list(project, [cohort])

            return JSONResponse({'is_error': False, 'next_page': reverse('cohort_home', args=(project.project_id, cohort.cohort_id))})
        else:
            return JSONResponse({'is_error': True, 'error': server_utils.form_error_string(form)})

    individuals_json = json_displays.individual_list(project.get_individuals())

    return render(request, 'cohort/add.html', {
        'project': project,
        'individuals_json': json.dumps(individuals_json),
    })

@login_required
@csrf_exempt
def edit(request, project_id, cohort_id):

    project = get_object_or_404(Project, project_id=project_id)
    cohort = get_object_or_404(Cohort, project=project, cohort_id=cohort_id)
    if not project.can_admin(request.user):
        raise PermissionDenied


    if request.method == 'POST':
        form = base_forms.EditCohortForm(project, request.POST)
        if form.is_valid():
            cohort.display_name = form.cleaned_data['name']
            cohort.short_description = form.cleaned_data['description']
            cohort.save()
            return redirect('cohort_home', project.project_id, cohort.cohort_id)

    else:
        form = base_forms.EditCohortForm(project, initial={
            'name': cohort.display_name,
            'description': cohort.short_description,
        })

    return render(request, 'cohort/edit.html', {
        'project': project,
        'cohort': cohort,
        'form': form,
    })



@login_required
@csrf_exempt
def delete(request, project_id, cohort_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    cohort = get_object_or_404(Cohort, project=project, cohort_id=cohort_id)
    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            cohort.delete()
            return redirect('cohorts', project_id)

    return render(request, 'cohort/delete.html', {
        'project': project,
        'cohort': cohort,
    })

