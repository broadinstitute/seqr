import json
import itertools

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib import messages

from xbrowse_server.analysis.project import get_knockouts_in_gene
from xbrowse_server.base.forms import FAMFileForm, AddPhenotypeForm, AddFamilyGroupForm
from xbrowse_server.base.models import Project, Individual, Family, FamilyGroup, ProjectCollaborator, ProjectPhenotype
from xbrowse_server import sample_management, json_displays
from xbrowse_server import server_utils
from xbrowse_server.base.utils import get_collaborators_for_user
from xbrowse_server.gene_lists.forms import GeneListForm
from xbrowse_server.gene_lists.models import GeneList, GeneListItem
from xbrowse_server.base.models import ProjectGeneList
from xbrowse_server.decorators import log_request
from xbrowse_server.base.lookups import get_saved_variants_for_project
from xbrowse_server.api.utils import add_extra_info_to_variants_family, add_extra_info_to_variants_project
from xbrowse_server.base import forms as base_forms
from xbrowse_server import user_controls
from xbrowse_server.analysis import project as project_analysis
from xbrowse.utils.basic_utils import get_alt_allele_count, get_gene_id_from_str
from xbrowse.core.variant_filters import get_default_variant_filter


@login_required
def project_home(request, project_id): 

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    if project.can_admin(request.user):
        auth_level = 'admin'
    elif project.can_edit(request.user):
        auth_level = 'editor'
    elif project.is_public:
        auth_level = 'public'
    elif project.can_view(request.user):
        auth_level = 'viewer'

    else:
        raise Exception("Authx - how did we get here?!?")

    return render(request, 'project.html', {
        'project': project,
        'auth_level': auth_level,
        'can_edit': project.can_edit(request.user), 
        })


@login_required
def manage_project(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    return render(request, 'project/manage_project.html', {
        'project': project,
    })

@login_required
def project_settings(request, project_id):
    """
    Manager can edit project settings
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse('Unauthorized')

    return render(request, 'project/project_settings.html', {
        'project': project,
        'is_manager': project.can_admin(request.user),
    })

@login_required
def project_collaborators(request, project_id):
    """
    Manager can edit project settings
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse('Unauthorized')

    return render(request, 'project/collaborators.html', {
        'project': project,
        'is_manager': project.can_admin(request.user),
    })

@login_required
def edit_project_refpops(request, project_id):
    """
    Manager can edit project settings
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse('Unauthorized')

    return render(request, 'project/edit_project_refpops.html', {
        'project': project,
        'is_manager': project.can_admin(request.user),
    })


@login_required
def add_gene_list(request, project_id):
    """
    Manager can edit project settings
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('Unauthorized')

    error = None

    if request.method == 'POST':

        form = GeneListForm(request.POST)

        if request.POST.get('select_public_list') == 'yes':
            public_list = GeneList.objects.get(pk=int(request.POST.get('public_list')))
            if not public_list.is_public:
                error = "Not actually public, good try"
            else:
                ProjectGeneList.objects.create(project=project, gene_list=public_list)
                return redirect('project_settings', project_id=project_id)

        else:
            if form.is_valid():
                new_list = GeneList.objects.create(
                    slug=form.cleaned_data['slug'],
                    name=form.cleaned_data['name'],
                    description=form.cleaned_data['description'],
                    is_public=form.cleaned_data['is_public'],
                )
                for gene_id in form.cleaned_data['gene_ids']:
                    GeneListItem.objects.create(gene_list=new_list, gene_id=gene_id)
                ProjectGeneList.objects.create(project=project, gene_list=new_list)
                return redirect('project_settings', project_id=project_id)
            else:
                error = server_utils.form_error_string(form)

    else:
        form = GeneListForm()

    public_lists = GeneList.objects.filter(is_public=True)

    return render(request, 'project/add_gene_list.html', {
        'project': project,
        'form': form,
        'public_lists': public_lists,
        'error': error,
    })


@login_required
def remove_gene_list(request, project_id):
    """
    Manager can edit project settings
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('Unauthorized')

    return render(request, 'project/remove_gene_list.html', {
        'project': project,
    })


@login_required
def project_individuals(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    _individuals = json_displays.individual_list(project.get_individuals())

    return render(request, 'individual/individuals.html', {
        'project': project,
        'individuals_json': json.dumps(_individuals),
    })


@login_required
def edit_individuals(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    individuals = project.individual_set.all()
    individuals_json = [indiv.to_dict() for indiv in individuals]

    return render(request, 'edit_individuals.html', {
        'individuals_json': json.dumps(individuals_json),
        'project': project,
    })


@login_required
@csrf_exempt
def update_project_from_fam(request, project_id):

    error = None

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    form = FAMFileForm(request.POST, request.FILES)

    if form.is_valid():
        sample_management.update_project_from_individuals(project, form.cleaned_data['individuals'])
        return redirect('edit_individuals', project.project_id)
    else:
        error = "File error"

    if error:
        ret = {'is_error': True, 'error': error}
    else:
        ret = {'is_error': False}

    return server_utils.JSONResponse(ret)


@login_required
@csrf_exempt
def delete_individuals(request, project_id):

    error = None

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    indiv_id_list = request.POST.get('to_delete').split('|')
    to_delete = []
    for indiv_id in indiv_id_list:
        i = Individual.objects.get(project=project, indiv_id=indiv_id)
        to_delete.append(i)

    for individual in to_delete:
        individual.delete()

    if error:
        return server_utils.JSONResponse({'is_error': True, 'error': error})
    else:
        return redirect('edit_individuals', project.project_id)


@login_required
@csrf_exempt
def add_phenotype(request, project_id):

    error = None

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    form = AddPhenotypeForm(project, request.POST)
    if form.is_valid():
        phenotype = ProjectPhenotype(
            project=project,
            slug=form.cleaned_data['slug'],
            name=form.cleaned_data['name'],
            category=form.cleaned_data['category'],
            datatype=form.cleaned_data['datatype'],
        )
        phenotype.save()
        return redirect('edit_individuals', project.project_id)
    else:
        error = server_utils.form_error_string(form)

    if error:
        return server_utils.JSONResponse({'is_error': True, 'error': error})
    else:
        return redirect('edit_individuals', project.project_id)


# todo: move this to an api_utils area
def save_individual_from_json_dict(project, indiv_dict):
    individual = Individual.objects.get_or_create(indiv_id=indiv_dict['indiv_id'], project=project)[0]
    individual.gender = indiv_dict.get('gender')
    individual.affected = indiv_dict.get('affected')
    individual.nickname = indiv_dict.get('nickname', '')
    individual.paternal_id = indiv_dict.get('paternal_id', '')
    individual.maternal_id = indiv_dict.get('maternal_id', '')
    individual.save()
    sample_management.set_family_id_for_individual(individual, indiv_dict.get('family_id', ''))
    sample_management.set_individual_phenotypes_from_dict(individual, indiv_dict.get('phenotypes', {}))


@csrf_exempt
@login_required
def save_one_individual(request, project_id):

    error = None
    project = Project.objects.get(project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    indiv_json = json.loads(request.POST.get('individual_json'))
    save_individual_from_json_dict(project, indiv_json)

    if not error:
        ret = {
            'is_error': False,
        }
        return server_utils.JSONResponse(ret)
    else:
        ret = {
            'is_error': True,
            'error': error
        }
        return server_utils.JSONResponse(ret)


@csrf_exempt
@login_required
def save_all_individuals(request, project_id):

    error = None

    # todo: validation
    project = Project.objects.get(project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    individuals_json = json.loads(request.POST.get('individuals_json'))
    for indiv_obj in individuals_json:
        save_individual_from_json_dict(project, indiv_obj)

    if not error:
        ret = {
            'is_error': False,
        }
        return server_utils.JSONResponse(ret)
    else:
        ret = {
            'is_error': True,
            'error': error
        }
        return server_utils.JSONResponse(ret)


@login_required
@csrf_exempt
def add_individuals(request, project_id):

    error = None

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

    indiv_id_list = json.loads(request.POST.get('indiv_id_list'), '[]')
    for indiv_id in indiv_id_list:
        if Individual.objects.filter(project=project, indiv_id=indiv_id).exists():
            error = "Indiv ID %s already exists" % indiv_id

    if not error:
        for indiv_id in indiv_id_list:
            Individual.objects.create(project=project, indiv_id=indiv_id)

    if True:
        return server_utils.JSONResponse({'is_error': True, 'error': error})
    else:
        return server_utils.JSONResponse({'is_error': False})


@login_required
@log_request('saved_variants')
def saved_variants(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    variants = get_saved_variants_for_project(project)
    variants = sorted(variants, key=lambda v: v.extras['family_id'])
    grouped_variants = itertools.groupby(variants, key=lambda v: v.extras['family_id'])
    for family_id, family_variants in grouped_variants:
        family = Family.objects.get(project=project, family_id=family_id)
        family_variants = list(family_variants)

        # TODO: in addition to the notes in family_saved_variants, need to have an add_extra_info_to_variants_project
        add_extra_info_to_variants_family(settings.REFERENCE, family, family_variants)

    return render(request, 'project/saved_variants.html', {
        'project': project,
        'variants_json': json.dumps([v.toJSON() for v in variants]),
        'families_json': json.dumps({family.family_id: family.get_json_obj() for family in project.get_families()})
    })


@login_required
@csrf_exempt
def add_family_group(request, project_id):

    error = None

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse('unauthorized')

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
        return redirect('family_group_home', project.project_id, family_group.slug )


@login_required()
def add_collaborator(request, project_id):
    """
    Form for a manager to add a new collaborator
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    if request.method == 'POST':
        form = base_forms.AddCollaboratorForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get('collaborator'):
                collaborator = form.cleaned_data['collaborator']
                project.set_as_collaborator(collaborator)
                messages.add_message(
                    request,
                    messages.INFO,
                    '{} has been added!'.format(collaborator.profile)
                )
                return redirect('project_collaborators', project_id)
            else:
                request.session['collaborator_email'] = form.cleaned_data['collaborator_email']
            return redirect('add_collaborator_confirm', project_id)
    else:
        form = base_forms.AddCollaboratorForm()

    return render(request, 'project/add_collaborator.html', {
        'project': project,
        'form': form,
        'other_users': get_collaborators_for_user(request.user)[:50],
    })


@login_required()
def add_collaborator_confirm(request, project_id):
    """
    Form for a manager to add a new collaborator
    """
    collaborator_email = request.session['collaborator_email']
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    if request.method == 'POST':
        request.session.pop('collaborator_email')
        if User.objects.filter(email=collaborator_email).exists():
            collaborator = User.objects.get(email=collaborator_email)
            messages.add_message(
                request,
                messages.INFO,
                '{} has been added to this project, but he or she actually already had an xBrowse account. This project will be visible on their My Data page.'.format(collaborator.profile)
            )
        else:
            collaborator = user_controls.add_new_collaborator(collaborator_email, request.user)
            messages.add_message(
                request,
                messages.INFO,
                '{} has been added! He or she has been emailed to set up an xBrowse password.'.format(collaborator.email)
            )
        project.set_as_collaborator(collaborator)
        return redirect('project_collaborators', project_id)

    return render(request, 'project/add_collaborator_confirm.html', {
        'project': project,
        'collaborator_email': collaborator_email,
    })


@login_required()
def edit_collaborator(request, project_id, username):
    """
    Form to edit collaborator's permissions in a project
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    project_collaborator = get_object_or_404(ProjectCollaborator, project=project, user__username=username)

    if request.method == 'POST':
        form = base_forms.EditCollaboratorForm(request.POST)
        if form.is_valid():
            project_collaborator.collaborator_type = form.cleaned_data['collaborator_type']
            project_collaborator.save()
            return redirect('project_collaborators', project_id)

    else:
        form = base_forms.EditCollaboratorForm()

    return render(request, 'project/edit_collaborator.html', {
        'project_collaborator': project_collaborator,
        'project': project,
        'form': form,
    })


@login_required()
def delete_collaborator(request, project_id, username):
    """
    POST removes this collaborator from the project
    GET is a confirm message
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    project_collaborator = get_object_or_404(ProjectCollaborator, project=project, user__username=username)
    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            project_collaborator.delete()
            return redirect('project_settings', project_id)

    return render(request, 'project/delete_collaborator.html', {
        'project': project,
        'project_collaborator': project_collaborator,
    })


@login_required()
def gene_quicklook(request, project_id, gene_id):
    """
    Summary of a gene in a project
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        return HttpResponse("Unauthorized")
    gene_id = get_gene_id_from_str(gene_id, settings.REFERENCE)
    gene = settings.REFERENCE.get_gene(gene_id)

    variant_filter = get_default_variant_filter('all_coding', settings.ANNOTATOR.reference_population_slugs)
    num_indivs = len([i for i in project.get_individuals() if i.has_variant_data()])
    aac_threshold = (.2 * num_indivs) + 5
    rare_variants = []
    for variant in project_analysis.get_variants_in_gene(project, gene_id, variant_filter=variant_filter):
        aac = get_alt_allele_count(variant)
        max_af = max(variant.annotation['freqs'].values())
        if aac <= aac_threshold and max_af < .01:
            rare_variants.append(variant)

    add_extra_info_to_variants_project(settings.REFERENCE, project, rare_variants)

    knockouts = []
    knockout_ids, variation = get_knockouts_in_gene(project, gene_id)
    for kid in knockout_ids:
        variants = variation.get_relevant_variants_for_indiv_ids([kid])
        add_extra_info_to_variants_project(settings.REFERENCE, project, variants)
        knockouts.append({
            'indiv_id': kid,
            'variants': [v.toJSON() for v in variants],
        })

    return render(request, 'project/gene_quicklook.html', {
        'gene': gene,
        'gene_json': json.dumps(gene),
        'project': project,
        'rare_variants_json': json.dumps([v.toJSON() for v in rare_variants]),
        'individuals_json': json.dumps([i.get_json_obj() for i in project.get_individuals()]),
        'knockouts_json': json.dumps(knockouts),
    })


@login_required()
def edit_basic_info(request, project_id):
    """
    Form for a manager to add a new collaborator
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        return HttpResponse("Unauthorized")

    if request.method == 'POST':
        form = base_forms.EditBasicInfoForm(request.POST)
        if form.is_valid():
            project.project_name = form.cleaned_data['name']
            project.description = form.cleaned_data['description']
            project.save()
            return redirect('project_settings', project_id)
    else:
        form = base_forms.EditBasicInfoForm({'name': project.project_name, 'description': project.description})

    return render(request, 'project/edit_basic_info.html', {
        'project': project,
        'form': form,
    })