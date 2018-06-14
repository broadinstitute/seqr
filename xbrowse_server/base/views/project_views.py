import csv
import json
import logging
import sys
import urllib

from django.db import connection
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls.base import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib import messages
from xbrowse_server.base.model_utils import update_xbrowse_model, delete_xbrowse_model, get_or_create_xbrowse_model, \
    create_xbrowse_model
from xbrowse_server.mall import get_project_datastore
from xbrowse_server.analysis.project import get_knockouts_in_gene
from xbrowse_server.base.forms import FAMFileForm, AddPhenotypeForm, AddFamilyGroupForm, AddTagForm
from xbrowse_server.base.models import Project, Individual, Family, FamilyGroup, ProjectCollaborator, ProjectPhenotype, \
    ProjectTag
from xbrowse_server import sample_management, json_displays
from xbrowse_server import server_utils
from xbrowse_server.base.utils import get_collaborators_for_user, get_filtered_families, get_loaded_projects_for_user
from xbrowse_server.gene_lists.models import GeneList
from xbrowse_server.base.models import ProjectGeneList
from xbrowse_server.base.lookups import get_all_saved_variants_for_project, get_variants_by_tag, get_causal_variants_for_project
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.base import forms as base_forms
from xbrowse_server import user_controls
from xbrowse_server.analysis import project as project_analysis
from xbrowse.utils.basic_utils import get_gene_id_from_str
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse_server.mall import get_reference
from xbrowse_server import mall
from xbrowse_server.gene_lists.views import download_response as gene_list_download_response
from xbrowse_server.decorators import log_request
from seqr.models import Project as SeqrProject


log = logging.getLogger('xbrowse_server')


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

    phenotips_supported=True
    if settings.PROJECTS_WITHOUT_PHENOTIPS is not None and project_id in settings.PROJECTS_WITHOUT_PHENOTIPS:
          phenotips_supported=False
    return render(request, 'project.html', {
        'phenotips_supported':phenotips_supported,
        'project': project,
        'auth_level': auth_level,
        'can_edit': project.can_edit(request.user),
        'is_manager': project.can_admin(request.user),
        'has_gene_search':
            get_project_datastore(project).project_collection_is_loaded(project)
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

    cursor = connection.cursor()

    loaded_vcfs_subquery = """
      SELECT 
        COUNT(*) 
      FROM base_vcffile AS v 
        JOIN base_individual_vcf_files AS vi ON v.id=vi.vcffile_id
      WHERE vi.individual_id=i.id AND v.loaded_date IS NOT NULL
    """

    individuals_query = """
        SELECT DISTINCT
          f.family_id AS family_id,
          i.indiv_id AS indiv_id,
          i.nickname AS nickname,
          i.maternal_id AS maternal_id,
          i.paternal_id AS paternal_id,
          i.gender AS gender,
          i.affected AS affected,
          i.case_review_status AS case_review_status,
          f.family_name AS family_name,
          ({loaded_vcfs_subquery}) AS has_variant_data,
          i.bam_file_path IS NULL AS has_read_data
        FROM base_individual AS i
          JOIN base_family AS f ON i.family_id=f.id
        WHERE f.project_id=%s
    """.strip().format(**locals())

    cursor.execute(individuals_query, [project.id])

    columns = [col[0] for col in cursor.description]
    individual_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    print(sorted(individual_rows)[0])

    #print("=====")
    #individuals_json = json_displays.individual_list(project.get_individuals())

    #print(sorted(individuals_json)[0])

    individuals_json = []
    for indiv in individual_rows:
        individuals_json.append({
            'indiv_id': indiv["indiv_id"],
            'nickname': indiv["nickname"],
            'family_id': indiv["family_id"],
            'family_url': reverse('family_home', args=(project_id, indiv["family_id"])),
            'maternal_id': indiv["maternal_id"],
            'paternal_id': indiv["paternal_id"],
            'gender': indiv["gender"],
            'affected_status': indiv["affected"],
            'in_case_review': indiv["case_review_status"] == "I" and (not indiv["has_variant_data"]),
            'case_review_status': indiv["case_review_status"],
            'has_variant_data': indiv["has_variant_data"],
            'has_read_data': indiv["has_read_data"],
        })

    return render(request, 'individual/individuals.html', {
        'project': project,
        'is_staff': 'true' if request.user.is_staff else 'false',
        'individuals_json': json.dumps(individuals_json),
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
        for i in Individual.objects.filter(project=project, indiv_id=indiv_id):
            to_delete.append(i)

    family_ids = set()
    for individual in to_delete:
        family_ids.add(individual.family.family_id)
        delete_xbrowse_model(individual)

    for family_id in family_ids:
        if len(Individual.objects.filter(family__family_id=family_id)) == 0:
            families = Family.objects.filter(family_id=family_id)
            if families:
                delete_xbrowse_model(families[0])

    try:
        if not settings.DEBUG: settings.EVENTS_COLLECTION.insert({
                'event_type': 'delete_individuals',
                'date': timezone.now(),
                'project_id': project_id,
                'individuals': ", ".join([i.indiv_id for i in to_delete]),
                'username': request.user.username,
                'email': request.user.email,
        })
    except Exception as e:
        logging.error("Error while logging add_variant_tag event: %s" % e)

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
    individual = get_or_create_xbrowse_model(Individual, indiv_id=indiv_dict['indiv_id'], project=project)[0]
    update_xbrowse_model(
        individual,
        gender = indiv_dict.get('gender'),
        affected = indiv_dict.get('affected'),
        nickname = indiv_dict.get('nickname', ''),
        paternal_id = indiv_dict.get('paternal_id', ''),
        maternal_id = indiv_dict.get('maternal_id', ''))

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
            create_xbrowse_model(Individual, project=project, indiv_id=indiv_id)

    if True:
        return server_utils.JSONResponse({'is_error': True, 'error': error})
    else:
        return server_utils.JSONResponse({'is_error': False})


@login_required
@log_request('variants_with_tag')
def variants_with_tag(request, project_id, tag=None):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    requested_family_id = request.GET.get('family')
    if tag:
        tag = urllib.unquote(tag)
        variants = get_variants_by_tag(project, tag, family_id=requested_family_id)
    else:
        variants = get_all_saved_variants_for_project(project, family_id=requested_family_id)
    add_extra_info_to_variants_project(get_reference(), project, variants, add_family_tags=True, add_populations=True)
    variants.sort(key=lambda var: var.xpos)

    if request.GET.get('download', ''):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}_{}.csv"'.format(project_id, tag)

        header_fields = [
            "chrom", "pos", "ref", "alt",  "tags", "notes", "family", "gene", "effect",
            "1kg_wgs_phase3", "1kg_wgs_phase3_popmax", "exac_v3", "exac_v3_popmax",
            "gnomad_exomes", "gnomad_exomes_popmax", "gnomad_genomes", "gnomad_genomes_popmax",
            "sift", "polyphen", "hgvsc", "hgvsp"
        ]

        genotype_header_fields = ['sample_id', 'GT_genotype', 'filter', 'AD_allele_depth', 'DP_read_depth', 'GQ_genotype_quality', 'AB_allele_balance']
        for i in range(0, 10):
            for h in genotype_header_fields:
                header_fields.append("%s_%d" % (h, i))

        writer = csv.writer(response)
        writer.writerow(header_fields)
        for variant in variants:
            if not (variant and variant.annotation and (variant.annotation.get('main_transcript') or variant.annotation.get("vep_annotation"))):
                continue

            worst_annotation_idx = variant.annotation["worst_vep_annotation_index"]
            worst_annotation = variant.annotation.get('main_transcript') or variant.annotation["vep_annotation"][worst_annotation_idx]

            family_id = variant.extras["family_id"]
            family = Family.objects.get(project=project, family_id=family_id)

            genotype_values = []
            for individual in family.get_individuals():
                genotype_values.append(individual.indiv_id)
                genotype = variant.get_genotype(individual.indiv_id)
                genotype_values.append("/".join(genotype.alleles) if genotype and genotype.alleles else "./.")
                genotype_values.append(genotype.filter if genotype else "")
                genotype_values.append(genotype.extras["ad"] if genotype else "")
                genotype_values.append(genotype.extras["dp"] if genotype else "")
                genotype_values.append(genotype.gq if genotype and genotype.gq is not None else "")
                genotype_values.append(genotype.ab if genotype and genotype.ab is not None else "")


            row = [
                variant.chr,
                variant.pos,
                variant.ref,
                variant.alt,
                "|".join([tag['tag'] for tag in variant.extras['family_tags']]) if 'family_tags' in variant.extras else '',

                "|".join([note['user']['display_name'] +":"+ note['note'] for note in variant.extras['family_notes']]) if 'family_notes' in variant.extras else '',

                variant.extras["family_id"],
                worst_annotation["gene_symbol"],
                variant.annotation.get("vep_consequence") or "",

                variant.annotation["freqs"].get("1kg_wgs_phase3") or variant.annotation["freqs"].get("1kg_wgs_AF") or "",
                variant.annotation["freqs"].get("1kg_wgs_phase3_popmax") or variant.annotation["freqs"].get("1kg_wgs_popmax_AF") or "",
                variant.annotation["freqs"].get("exac_v3") or variant.annotation["freqs"].get("exac_v3_AF") or "",
                variant.annotation["freqs"].get("exac_v3_popmax") or variant.annotation["freqs"].get("exac_v3_popmax_AF") or "",
                variant.annotation["freqs"].get("gnomad_exomes_AF") or "",
                variant.annotation["freqs"].get("gnomad_exomes_popmax_AF") or "",
                variant.annotation["freqs"].get("gnomad_genomes_AF") or "",
                variant.annotation["freqs"].get("gnomad_genomes_popmax_AF") or "",
                worst_annotation.get("sift") or "",
                worst_annotation.get("polyphen") or "",
                worst_annotation.get("hgvsc") or "",
                (worst_annotation.get("hgvsp") or "").replace("%3D", "="),
            ] + genotype_values
            writer.writerow(map(lambda s: unicode(s).encode('UTF-8'), row))

        return response
    else:
        family_ids = {variant.extras['family_id'] for variant in variants}
        families = get_filtered_families(filters={'project': project, 'family_id__in': family_ids}, fields=['family_id'])

        return render(request, 'project/saved_variants.html', {
            'project': project,
            'tag': tag,
            'variants_json': json.dumps([v.toJSON() for v in variants]),
            'families_json': json.dumps({family.family_id: {
                'project_id': project.project_id,
                'family_id': family.family_id,
                'individuals': family.get_individuals_json(project_id=project.project_id)
            } for family in families})
    })


@login_required
@log_request('causal_variants')
def causal_variants(request, project_id):

    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    variants = get_causal_variants_for_project(project)
    add_extra_info_to_variants_project(get_reference(), project, variants, add_family_tags=True, add_populations=True)

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
            return HttpResponse("Invalid form: " + str(form.cleaned_data))
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
                '{} has been added to this project, but he or she actually already had a seqr account. This project will be visible on their My Data page.'.format(collaborator.profile)
            )
        else:
            collaborator = user_controls.add_new_collaborator(collaborator_email, request.user)
            messages.add_message(
                request,
                messages.INFO,
                '{} has been added! He or she has been emailed to set up an seqr password.'.format(collaborator.email)
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
            seqr_project = project.seqr_project if project.seqr_project else (SeqrProject.objects.get(deprecated_project_id=project_id) if SeqrProject.objects.filter(deprecated_project_id=project_id) else None)
            if seqr_project:
                if form.cleaned_data['collaborator_type'] == 'manager':
                    seqr_project.can_edit_group.user_set.add(project_collaborator.user)
                    seqr_project.can_view_group.user_set.add(project_collaborator.user)
                elif form.cleaned_data['collaborator_type'] == 'collaborator':
                    seqr_project.can_edit_group.user_set.remove(project_collaborator.user)
                    seqr_project.can_view_group.user_set.add(project_collaborator.user)
                else:
                    raise ValueError("Unexpected collaborator_type: " + str(form.cleaned_data['collaborator_type']))

            project_collaborator.collaborator_type = form.cleaned_data['collaborator_type']
            project_collaborator.save()
            return redirect('project_collaborators', project_id)

    else:
        form = base_forms.EditCollaboratorForm(initial={
            "collaborator_type": project_collaborator.collaborator_type,
        })

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
            seqr_project = project.seqr_project if project.seqr_project else (SeqrProject.objects.get(deprecated_project_id=project_id) if SeqrProject.objects.filter(deprecated_project_id=project_id) else None)
            if seqr_project:
                seqr_project.can_edit_group.user_set.remove(project_collaborator.user)
                seqr_project.can_view_group.user_set.remove(project_collaborator.user)

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
    main_project = get_object_or_404(Project, project_id=project_id)
    if not main_project.can_view(request.user):
        return HttpResponse("Unauthorized")

    # other projects this user can view
    other_projects = get_loaded_projects_for_user(request.user, fields=['project_id', 'project_name'])

    if other_projects:
        other_projects_json = json.dumps([{'project_id': p.project_id, 'project_name': p.project_name} for p in sorted(other_projects, key=lambda p: p.project_id.lower())])
    else:
        other_projects_json = None

    if gene_id is None:
        return render(request, 'project/gene_quicklook.html', {
            'project': main_project,
            'gene': None,
            'gene_json': None,
            'rare_variants_json': None,
            'individuals_json': None,
            'knockouts_json': None,
            'other_projects_json': other_projects_json,
        })

    projects_to_search_param = request.GET.get('selected_projects')
    if projects_to_search_param:
        project_ids = projects_to_search_param.split(",")
        projects_to_search = [project for project in other_projects if project.project_id in project_ids]
        if len(projects_to_search) < len(project_ids):
            # If not all the specified project ids are in the other projects list then they are not authorized
            return HttpResponse("Unauthorized")
    else:
        project_ids = [main_project.project_id]
        projects_to_search = [main_project]

    gene_id = get_gene_id_from_str(gene_id, get_reference())
    gene = get_reference().get_gene(gene_id)

    # all rare coding variants
    variant_filter = get_default_variant_filter('all_coding', mall.get_annotator().reference_population_slugs)

    indiv_id_to_project_id = {}
    rare_variant_dict = {}
    rare_variants = []
    individ_ids_and_variants = []
    for project in projects_to_search:
        all_project_variants = project_analysis.get_variants_in_gene(project, gene_id, variant_filter=variant_filter)

        # compute knockout individuals
        knockout_ids, variation = get_knockouts_in_gene(project, gene_id, all_project_variants)
        for indiv_id in knockout_ids:
            variants = variation.get_relevant_variants_for_indiv_ids([indiv_id])
            individ_ids_and_variants.append({
                'indiv_id': indiv_id,
                'variants': variants,
            })

        # compute rare variants
        project_variants = []
        for i, variant in enumerate(all_project_variants):
            max_af = max([freq for label, freq in variant.annotation['freqs'].items() if label != "AF"])  # don't filter on within-cohort AF

            if not any([indiv_id for indiv_id, genotype in variant.genotypes.items() if genotype.num_alt > 0]):
                continue
            if max_af >= .01:
                continue

            # add project id to genotypes
            for indiv_id in variant.genotypes:
                indiv_id_to_project_id[indiv_id] = project.project_id

            # save this variant (or just the genotypes from this variant if the variant if it's been seen already in another project)
            variant_id = "%s-%s-%s-%s" % (variant.chr,variant.pos, variant.ref, variant.alt)
            if variant_id not in rare_variant_dict:
                rare_variant_dict[variant_id] = variant
                project_variants.append(variant)
            else:
                rare_variant_dict[variant_id].genotypes.update(variant.genotypes)

        rare_variants.extend(project_variants)

    all_variants = sum([i['variants'] for i in individ_ids_and_variants], rare_variants)
    add_extra_info_to_variants_project(get_reference(), project, all_variants, add_family_tags=True)
    download_csv = request.GET.get('download', '')
    if download_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}_{}.csv"'.format(download_csv, gene.get("symbol") or gene.get("transcript_name"))

        def get_row(variant, worst_annotation):
            measureset_id, clinvar_significance = get_reference().get_clinvar_info(*variant.unique_tuple())
            genotypes = []

            all_genotypes_string = ""
            for indiv_id in individuals_to_include:
                if indiv_id in variant.genotypes and variant.genotypes[indiv_id].num_alt > 0:
                    genotype = variant.genotypes[indiv_id]
                    allele_string = ">".join(genotype.alleles)
                    all_genotypes_string += indiv_id + ":" + allele_string + "  "
                    genotypes.append(allele_string + "   (" + str(genotype.gq) + ")")
                else:
                    genotypes.append("")
            return [
                gene["symbol"],
                variant.chr,
                variant.pos,
                variant.ref,
                variant.alt,
                variant.vcf_id or "",
                variant.annotation.get("vep_consequence") or "",
                worst_annotation.get("hgvsc") or "",
                (worst_annotation.get("hgvsp") or "").replace("%3D", "="),
                worst_annotation.get("sift") or "",
                worst_annotation.get("polyphen") or "",
                worst_annotation.get("mutationtaster_pred") or "",
                (";".join(set((worst_annotation.get("fathmm_pred") or "").split('%3B')))),

                measureset_id or "",
                clinvar_significance or "",

                variant.annotation["freqs"].get("1kg_wgs_phase3") or variant.annotation["freqs"].get("1kg_wgs_AF") or "",
                variant.annotation["freqs"].get("1kg_wgs_phase3_popmax") or variant.annotation["freqs"].get("1kg_wgs_popmax_AF") or "",
                variant.annotation["freqs"].get("exac_v3") or variant.annotation["freqs"].get("exac_v3_AF") or "",
                variant.annotation["freqs"].get("exac_v3_popmax") or variant.annotation["freqs"].get("exac_v3_popmax_AF") or "",
                variant.annotation["freqs"].get("gnomad_exomes_AF") or "",
                variant.annotation["freqs"].get("gnomad_exomes_popmax_AF") or "",
                variant.annotation["freqs"].get("gnomad_genomes_AF") or "",
                variant.annotation["freqs"].get("gnomad_genomes_popmax_AF") or "",
                all_genotypes_string,
            ] + genotypes

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
                        if indiv_id in variant.genotypes and variant.genotypes[indiv_id].num_alt > 0:
                            genotype = variant.genotypes[indiv_id]
                            allele_string = ">".join(genotype.alleles)
                            all_genotypes_string += indiv_id + ":" + allele_string + "  "
                            genotypes.append(allele_string + "   (" + str(genotype.gq) + ")")
                        else:
                            genotypes.append("")

                    rows.append(map(str, get_row(variant, worst_annotation)))

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

                rows.append(map(str, get_row(variant, worst_annotation)))

        header = ["gene", "chr", "pos", "ref", "alt", "rsID", "impact",
                  "HGVS.c", "HGVS.p", "sift", "polyphen", "muttaster", "fathmm", "clinvar_id", "clinvar_clinical_sig",
                  "freq_1kg_wgs_phase3", "freq_1kg_wgs_phase3_popmax",
                  "freq_exac_v3", "freq_exac_v3_popmax",
                  "freq_gnomad_exomes", "freq_gnomad_exomes_popmax",
                  "freq_gnomad_genomes", "freq_gnomad_genomes_popmax",
                  "all_genotypes"] + list(map(lambda i: i + " (from %s)" % indiv_id_to_project_id[i], individuals_to_include))

        writer = csv.writer(response)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
        return response
    else:
        for individ_id_and_variants in individ_ids_and_variants:
            variants = individ_id_and_variants["variants"]
            individ_id_and_variants["variants"] = [v.toJSON() for v in variants]

        individ_ids = {i['indiv_id'] for i in individ_ids_and_variants}
        for var in rare_variants:
            individ_ids.update(var.genotypes.keys())
        individuals = Individual.objects.filter(
            indiv_id__in=individ_ids, project__project_id__in=project_ids
        ).select_related('project').select_related('family').only('project__project_id', 'family__family_id', *Individual.INDIVIDUAL_JSON_FIELDS_NO_IDS)

        return render(request, 'project/gene_quicklook.html', {
            'gene': gene,
            'gene_json': json.dumps(gene),
            'project': main_project,
            'rare_variants_json': json.dumps([v.toJSON() for v in rare_variants]),
            'individuals_json': json.dumps([i.get_json_obj(skip_has_variant_data=True) for i in individuals]),
            'knockouts_json': json.dumps(individ_ids_and_variants),
            'other_projects_json': other_projects_json,
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
            update_xbrowse_model(
                project,
                project_name=form.cleaned_data['name'],
                description=form.cleaned_data['description'])

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
            update_xbrowse_model(
                project,
                project_name=form.cleaned_data['name'],
                description=form.cleaned_data['description'])

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
            create_xbrowse_model(
                ProjectTag,
                project=project,
                tag=form.cleaned_data['tag'],
                title=form.cleaned_data['title'])
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
    tag_name = urllib.unquote(tag_name)
    tag_title = urllib.unquote(tag_title)

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
            update_xbrowse_model(tag, tag=form.cleaned_data['tag'], title=form.cleaned_data['title'])

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

    tag_name = urllib.unquote(tag_name)
    tag_title = urllib.unquote(tag_title)
    try:
        tag = ProjectTag.objects.get(project=project, tag=tag_name, title=tag_title)
        delete_xbrowse_model(tag)
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

