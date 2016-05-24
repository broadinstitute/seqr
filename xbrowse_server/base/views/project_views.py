import json
import itertools
import csv
import datetime
import sys

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib import messages
from xbrowse_server.mall import get_project_datastore
from xbrowse_server.analysis.project import get_knockouts_in_gene
from xbrowse_server.base.forms import FAMFileForm, AddPhenotypeForm, AddFamilyGroupForm, AddTagForm
from xbrowse_server.base.models import Project, Individual, Family, FamilyGroup, ProjectCollaborator, ProjectPhenotype, \
    VariantNote, ProjectTag
from xbrowse_server import sample_management, json_displays
from xbrowse_server import server_utils
from xbrowse_server.base.utils import get_collaborators_for_user
from xbrowse_server.gene_lists.forms import GeneListForm
from xbrowse_server.gene_lists.models import GeneList, GeneListItem
from xbrowse_server.base.models import ProjectGeneList
from xbrowse_server.decorators import log_request
from xbrowse_server.base.lookups import get_all_saved_variants_for_project, get_variants_with_notes_for_project, \
    get_variants_by_tag, get_causal_variants_for_project
from xbrowse_server.api.utils import add_extra_info_to_variants_family, add_extra_info_to_variants_project
from xbrowse_server.base import forms as base_forms
from xbrowse_server import user_controls
from xbrowse_server.analysis import project as project_analysis
from xbrowse.utils.basic_utils import get_alt_allele_count, get_gene_id_from_str
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.mall import get_reference
from xbrowse_server import mall
from xbrowse_server.gene_lists.views import download_response as gene_list_download_response
from xbrowse_server.phenotips.reporting_utilities import get_phenotype_entry_metrics_for_project
#from xbrowse_server.phenotips.reporting_utilities import categorize_phenotype_counts
#from xbrowse_server.phenotips.reporting_utilities import aggregate_phenotype_counts_into_bins
from xbrowse_server.decorators import log_request
import logging

logger = logging.getLogger(__name__)


@login_required
@log_request('project_views')
def project_home(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    project.set_accessed()
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

    #phenotips_supported=False
    #if not (settings.PROJECTS_WITHOUT_PHENOTIPS is None or project_id in settings.PROJECTS_WITHOUT_PHENOTIPS):
    #  phenotips_supported=True
    
    phenotips_supported=True
    if settings.PROJECTS_WITHOUT_PHENOTIPS is not None and project_id in settings.PROJECTS_WITHOUT_PHENOTIPS:
          phenotips_supported=False

    #indiv_phenotype_counts=[]
    #binned_counts={}
    #categorized_phenotype_counts={}
    #if phenotips_supported:
    #  try:
    #    indiv_phenotype_counts= get_phenotype_entry_metrics_for_project(project_id)
    #    binned_counts=aggregate_phenotype_counts_into_bins(indiv_phenotype_counts)
    #    categorized_phenotype_counts=categorize_phenotype_counts(binned_counts)
    #  except Exception as e:
    #    print 'error looking for project information in PhenoTips:logging & moving,there might not be any data'
    #    logger.error('project_views:'+str(e))

    return render(request, 'project.html', {
        'phenotips_supported':phenotips_supported,
        'project': project,
        'auth_level': auth_level,
        'can_edit': project.can_edit(request.user),
        'is_manager': project.can_admin(request.user),
        'has_gene_search':
            get_project_datastore(project_id).project_collection_is_loaded(project_id)
    })


@login_required
def manage_project(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

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
        raise PermissionDenied

    return render(request, 'project/project_settings.html', {
        'project': project,
        'is_manager': project.can_admin(request.user),
    })


@login_required
def project_gene_list_settings(request, project_id):
    """
    Manager can edit project settings
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    return render(request, 'project/project_gene_list_settings.html', {
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
        raise PermissionDenied

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
        raise PermissionDenied

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
        raise PermissionDenied

    error = None

    if request.method == 'POST':
        for slug in request.POST.getlist('gene_list_slug'):
            try:
                genelist = GeneList.objects.get(slug=slug)
            except ObjectDoesNotExist:
                error = 'Invalid gene list'
                break
            if not genelist.is_public and genelist.owner != request.user:
                error = 'Unauthorized'
                break

            ProjectGeneList.objects.get_or_create(project=project, gene_list=genelist)

        if not error:
            return redirect('project_gene_list_settings', project_id=project_id)

    public_lists = GeneList.objects.filter(is_public=True)

    return render(request, 'project/add_gene_list.html', {
        'project': project,
        'my_lists': GeneList.objects.filter(owner=request.user),
        'public_lists': public_lists,
        'error': error,
    })


@login_required
def remove_gene_list(request, project_id, gene_list_slug):
    """
    Manager can edit project settings
    """
    project = get_object_or_404(Project, project_id=project_id)
    gene_list = get_object_or_404(GeneList, slug=gene_list_slug)
    if not project.can_admin(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        ProjectGeneList.objects.filter(project=project, gene_list=gene_list).delete()
        return redirect('project_gene_list_settings', project.project_id)

    return render(request, 'project/remove_gene_list.html', {
        'project': project,
        'gene_list': gene_list,
    })


@login_required
def project_individuals(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    _individuals = json_displays.individual_list(project.get_individuals())

    return render(request, 'individual/individuals.html', {
        'project': project,
        'individuals_json': json.dumps(_individuals),
    })


@login_required
def edit_individuals(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

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
        raise PermissionDenied

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
        raise PermissionDenied

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
        raise PermissionDenied

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
        raise PermissionDenied

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
        raise PermissionDenied

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
        raise PermissionDenied

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
        raise PermissionDenied
    
    variants = get_all_saved_variants_for_project(project)
    if 'family' in request.GET:
        requested_family_id = request.GET.get('family')
        variants = filter(lambda v: v.extras['family_id'] == requested_family_id, variants)
        
    variants = sorted(variants, key=lambda v: (v.extras['family_id'], v.xpos))
    grouped_variants = itertools.groupby(variants, key=lambda v: v.extras['family_id'])
    for family_id, family_variants in grouped_variants:
        family = Family.objects.get(project=project, family_id=family_id)
        family_variants = list(family_variants)

        add_extra_info_to_variants_family(get_reference(), family, family_variants)

    return render(request, 'project/saved_variants.html', {
        'project': project,
        'tag': None,
        'variants_json': json.dumps([v.toJSON() for v in variants]),
        'families_json': json.dumps({family.family_id: family.get_json_obj() for family in project.get_families()})
    })


@login_required
@log_request('variants_with_tag')
def variants_with_tag(request, project_id, tag):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    project_tag = get_object_or_404(ProjectTag, project=project, tag=tag)

    variants = get_variants_by_tag(project, tag)
    if 'family' in request.GET:
        requested_family_id = request.GET.get('family')
        variants = filter(lambda v: v.extras['family_id'] == requested_family_id, variants)
    
    variants = sorted(variants, key=lambda v: (v.extras['family_id'], v.xpos))
    grouped_variants = itertools.groupby(variants, key=lambda v: v.extras['family_id'])
    for family_id, family_variants in grouped_variants:
        try:
            family = Family.objects.get(project=project, family_id=family_id)
        except ObjectDoesNotExist as e:
            print("family: %s not found" % str(family_id))
            continue

        family_variants = list(family_variants)
        add_extra_info_to_variants_family(get_reference(), family, family_variants)

    if request.GET.get('download', ''):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}_{}.csv"'.format(project_id, tag)

        header_fields = ["chrom", "pos", "ref", "alt",  "tags", "notes", "family", "gene", "effect",
                         "1kg_wgs_phase3", "1kg_wgs_phase3_popmax", "exac_v3", "exac_v3_popmax",
                         "sift", "polyphen", "hgvsc", "hgvsp"]

        genotype_header_fields = ['sample_id', 'GT_genotype', 'filter', 'AD_allele_depth', 'DP_read_depth', 'GQ_genotype_quality', 'AB_allele_balance']
        for i in range(0, 10):
            for h in genotype_header_fields:
                header_fields.append("%s_%d" % (h, i))

        writer = csv.writer(response)
        writer.writerow(header_fields)
        for variant in variants:
            worst_annotation_idx = variant.annotation["worst_vep_annotation_index"]
            worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx]

            family_id = variant.extras["family_id"]
            family = Family.objects.get(project=project, family_id=family_id)

            genotype_values = []
            for individual in family.get_individuals():
                genotype_values.append(individual.indiv_id)

                genotype = variant.get_genotype(individual.indiv_id)
                genotype_values.append("/".join(genotype.alleles) if genotype.alleles else "./.")
                genotype_values.append(genotype.filter)
                genotype_values.append(genotype.extras["ad"])
                genotype_values.append(genotype.extras["dp"])
                genotype_values.append(genotype.gq if genotype.gq is not None else "")
                genotype_values.append("%0.3f" % genotype.ab if genotype.ab is not None else "")


            writer.writerow(map(str,
                [ variant.chr,
                  variant.pos,
                  variant.ref,
                  variant.alt,
                  "|".join([tag['tag'] for tag in variant.extras['family_tags']]) if 'family_tags' in variant.extras else '',

                  "|".join([note['user']['display_name'] +":"+ note['note'] for note in variant.extras['family_notes']]) if 'family_notes' in variant.extras else '',

                  variant.extras["family_id"],
                  worst_annotation.get("symbol", ""),
                  variant.annotation.get("vep_consequence", ""),

                  variant.annotation["freqs"].get("1kg_wgs_phase3", ""),
                  variant.annotation["freqs"].get("1kg_wgs_phase3_popmax", ""),
                  variant.annotation["freqs"].get("exac_v3", ""),
                  variant.annotation["freqs"].get("exac_v3_popmax", ""),
                  worst_annotation.get("sift", ""),
                  worst_annotation.get("polyphen", ""),
                  worst_annotation.get("hgvsc", ""),
                  worst_annotation.get("hgvsp", "").replace("%3D", "="),
                  ] + genotype_values))

        return response
    else:
        return render(request, 'project/saved_variants.html', {
            'project': project,
            'tag': tag,
            'variants_json': json.dumps([v.toJSON() for v in variants]),
            'families_json': json.dumps({family.family_id: family.get_json_obj() for family in project.get_families()})
    })


@login_required
@log_request('causal_variants')
def causal_variants(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    variants = get_causal_variants_for_project(project)
    variants = sorted(variants, key=lambda v: (v.extras['family_id'], v.xpos))
    grouped_variants = itertools.groupby(variants, key=lambda v: v.extras['family_id'])
    for family_id, family_variants in grouped_variants:
        family = Family.objects.get(project=project, family_id=family_id)
        family_variants = list(family_variants)
        add_extra_info_to_variants_family(get_reference(), family, family_variants)

    return render(request, 'project/causal_variants.html', {
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
        raise PermissionDenied

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
            return redirect('project_collaborators', project_id)

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

    if project.project_status == Project.NEEDS_MORE_PHENOTYPES and not request.user.is_staff:
        return render(request, 'analysis_unavailable.html', {
            'reason': 'Awaiting phenotype data.'
        })


    if gene_id is None:
        return render(request, 'project/gene_quicklook.html', {
            'project': project,
            'gene': None,
            'gene_json': None,
            'rare_variants_json': None,
            'individuals_json': None,
            'knockouts_json': None,
        })
        
        
    gene_id = get_gene_id_from_str(gene_id, get_reference())
    gene = get_reference().get_gene(gene_id)
    sys.stderr.write(project_id + " - staring gene search for: %s %s \n" % (gene_id, gene))

    # all rare coding variants
    variant_filter = get_default_variant_filter('all_coding', mall.get_annotator().reference_population_slugs)

    rare_variants = []
    for variant in project_analysis.get_variants_in_gene(project, gene_id, variant_filter=variant_filter):
        max_af = max(variant.annotation['freqs'].values())
        if not any([indiv_id for indiv_id, genotype in variant.genotypes.items() if genotype.num_alt > 0]):
            continue
        if max_af < .01:
            rare_variants.append(variant)
    #sys.stderr.write("gene_id: %s, variant: %s\n" % (gene_id, variant.toJSON()['annotation']['vep_annotation']))
    add_extra_info_to_variants_project(get_reference(), project, rare_variants)

    # compute knockout individuals
    individ_ids_and_variants = []
    knockout_ids, variation = get_knockouts_in_gene(project, gene_id)
    for indiv_id in knockout_ids:
        variants = variation.get_relevant_variants_for_indiv_ids([indiv_id])
        add_extra_info_to_variants_project(get_reference(), project, variants)
        individ_ids_and_variants.append({
            'indiv_id': indiv_id,
            'variants': variants,
        })

    sys.stderr.write("Project-wide gene search retrieved %s rare variants for gene: %s \n" % (len(rare_variants), gene_id))

    download_csv = request.GET.get('download', '')
    if download_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}_{}.csv"'.format(download_csv, gene["transcript_name"])

        if download_csv == 'knockouts':

            individuals_to_include = [individ_id_and_variants["indiv_id"] for individ_id_and_variants in individ_ids_and_variants]

            rows = []
            for individ_id_and_variants in individ_ids_and_variants:
                rare_variants = individ_id_and_variants["variants"]
                for variant in rare_variants:
                    worst_annotation_idx = variant.annotation["worst_vep_index_per_gene"][gene_id]
                    worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx]
                    genotypes = []
                    all_genotypes_string = ""
                    for indiv_id in individuals_to_include:
                        genotype = variant.genotypes[indiv_id]
                        allele_string = ">".join(genotype.alleles)
                        all_genotypes_string += indiv_id + ":" + allele_string + "  "
                        if genotype.num_alt > 0:
                            genotypes.append(allele_string + "   (" + str(genotype.gq) + ")")
                        else:
                            genotypes.append("")

                    measureset_id, clinvar_significance = settings.CLINVAR_VARIANTS.get(variant.unique_tuple(), ("", ""))

                    rows.append(map(str,
                        [ gene["symbol"],
                          variant.chr,
                          variant.pos,
                          variant.ref,
                          variant.alt,
                          variant.vcf_id or "",
                          variant.annotation.get("vep_consequence", ""),
                          worst_annotation.get("hgvsc", ""),
                          worst_annotation.get("hgvsp", "").replace("%3D", "="),
                          worst_annotation.get("sift", ""),
                          worst_annotation.get("polyphen", ""),
                          worst_annotation.get("mutationtaster_pred", ""),
                          ";".join(set(worst_annotation.get("fathmm_pred", "").split('%3B'))),

                          measureset_id,
                          clinvar_significance,

                          variant.annotation["freqs"].get("1kg_wgs_phase3", ""),
                          variant.annotation["freqs"].get("1kg_wgs_phase3_popmax", ""),
                          variant.annotation["freqs"].get("exac_v3", ""),
                          variant.annotation["freqs"].get("exac_v3_popmax", ""),
                          all_genotypes_string,
                        ] + genotypes))
        elif download_csv == 'rare_variants':
            individuals_to_include = []
            for variant in rare_variants:
                for indiv_id, genotype in variant.genotypes.items():
                    if genotype.num_alt > 0 and indiv_id not in individuals_to_include:
                        individuals_to_include.append(indiv_id)
            rows = []
            for variant in rare_variants:
                worst_annotation_idx = variant.annotation["worst_vep_index_per_gene"][gene_id]
                worst_annotation = variant.annotation["vep_annotation"][worst_annotation_idx]
                genotypes = []
                all_genotypes_string = ""
                for indiv_id in individuals_to_include:
                    genotype = variant.genotypes[indiv_id]
                    allele_string = ">".join(genotype.alleles)
                    all_genotypes_string += indiv_id + ":" + allele_string + "  "
                    if genotype.num_alt > 0:
                        genotypes.append(allele_string + "   (" + str(genotype.gq) + ")")
                    else:
                        genotypes.append("")

                measureset_id, clinvar_significance = settings.CLINVAR_VARIANTS.get(variant.unique_tuple(), ("", ""))
                rows.append(map(str,
                    [ gene["symbol"],
                      variant.chr,
                      variant.pos,
                      variant.ref,
                      variant.alt,
                      variant.vcf_id or "",
                      variant.annotation.get("vep_consequence", ""),
                      worst_annotation.get("hgvsc", ""),
                      worst_annotation.get("hgvsp", "").replace("%3D", "="),
                      worst_annotation.get("sift", ""),
                      worst_annotation.get("polyphen", ""),
                      worst_annotation.get("mutationtaster_pred", ""),
                      ";".join(set(worst_annotation.get("fathmm_pred", "").split('%3B'))),
                      measureset_id,
                      clinvar_significance,
                      variant.annotation["freqs"].get("1kg_wgs_phase3", ""),
                      variant.annotation["freqs"].get("1kg_wgs_phase3_popmax", ""),
                      variant.annotation["freqs"].get("exac_v3", ""),
                      variant.annotation["freqs"].get("exac_v3_popmax", ""),
                      all_genotypes_string,
                    ] + genotypes))


        header = ["gene", "chr", "pos", "ref", "alt", "rsID", "impact",
                  "HGVS.c", "HGVS.p", "sift", "polyphen", "muttaster", "fathmm", "clinvar_id", "clinvar_clinical_sig",
                  "freq_1kg_wgs_phase3", "freq_1kg_wgs_phase3_popmax",
                  "freq_exac_v3", "freq_exac_v3_popmax",
                  "all_genotypes"] + individuals_to_include

        writer = csv.writer(response)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
        return response
    else:
        for individ_id_and_variants in individ_ids_and_variants:
            variants = individ_id_and_variants["variants"]
            individ_id_and_variants["variants"] = [v.toJSON() for v in variants]

        return render(request, 'project/gene_quicklook.html', {
            'gene': gene,
            'gene_json': json.dumps(gene),
            'project': project,
            'rare_variants_json': json.dumps([v.toJSON() for v in rare_variants]),
            'individuals_json': json.dumps([i.get_json_obj() for i in project.get_individuals()]),
            'knockouts_json': json.dumps(individ_ids_and_variants),
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


@login_required()
def project_tags(request, project_id):
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


@login_required
def add_tag(request, project_id):
    """For HTTP GET requests, this view generates the html page for creating a tag.
    For HTTP POST, it saves the submitted changes.

    Args:
        request: Django HTTP request object
        project_id: seqr project ID string
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    error = None
    if request.method == 'POST':
        form = AddTagForm(project, request.POST)
        if form.is_valid():
            ProjectTag.objects.create(
                project=project,
                tag=form.cleaned_data['tag'],
                title=form.cleaned_data['title'],
            )
            return redirect('project_home', project_id=project_id)
        else:
            error = server_utils.form_error_string(form)
    else:
        form = AddTagForm(project)

    return render(request, 'project/add_or_edit_tag.html', {
        'project': project,
        'form': form,
        'error': error,
    })


@login_required
def edit_tag(request, project_id, tag_name, tag_title):
    """For HTTP GET requests, this view generates the html page for editing a tag.
    For HTTP POST, it saves the submitted changes.

    Args:
        request: Django HTTP request object
        project_id: seqr project ID string
        tag_name: name of the tag to edit
        tag_title: title of the tag to edit
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    try:
        tag = ProjectTag.objects.get(project=project, tag=tag_name, title=tag_title)
    except ObjectDoesNotExist as e:
        return HttpResponse("Error: tag not found: %s - %s" % (tag_name, tag_title))

    if request.method == 'POST':
        form = AddTagForm(project, request.POST)
        if form.is_valid():
            tag.tag = form.cleaned_data['tag']
            tag.title = form.cleaned_data['title']
            tag.save()
            return redirect('project_home', project_id=project_id)

        error = server_utils.form_error_string(form)
    else:
        error = None
        form = AddTagForm(project)

    return render(request, 'project/add_or_edit_tag.html', {
        'project': project,
        'tag_name': tag.tag,
        'tag_title': tag.title,
        'form': form,
        'error': error,
    })



@login_required
def delete_tag(request, project_id, tag_name, tag_title):
    """Deletes the tag with the given tag_name and tag_title.

    Args:
        request: Django HTTP request object
        project_id: seqr project ID string
        tag_name: name of the tag to edit
        tag_title: title of the tag to edit
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    try:
        tag = ProjectTag.objects.get(project=project, tag=tag_name, title=tag_title)
        tag.delete()
    except ObjectDoesNotExist as e:
        return HttpResponse("Error: tag not found: %s - %s. Maybe it's already been deleted? " % (tag_name, tag_title))
    else:
        return redirect('project_home', project_id=project_id)

@login_required
def project_gene_list(request, project_id, gene_list_slug):
    """
    View a gene list for a project.
    This is the same view as a regular gene list view, but we might add project specific data later,
    like how many causal variants in each gene.
    """

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    gene_list = get_object_or_404(GeneList, slug=gene_list_slug)
    return render(request, 'project/project_gene_list.html', {
        'project': project,
        'gene_list': gene_list,
        'genes': gene_list.get_genes(),
    })


@login_required
def project_gene_list_download(request, project_id, gene_list_slug):
    """
    Download CSV for a project gene list
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    gene_list = get_object_or_404(GeneList, slug=gene_list_slug)
    return gene_list_download_response(gene_list)
