from collections import Counter, OrderedDict
import json
import os
from django.urls.base import reverse

import settings

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

from xbrowse_server.base.model_utils import update_xbrowse_model
from xbrowse_server.gene_lists.models import GeneList
from xbrowse_server import server_utils
from xbrowse.reference.utils import get_coding_regions_from_gene_structure
from xbrowse.core import genomeloc
from xbrowse_server.base.forms import EditFamilyForm, EditFamilyCauseForm
from xbrowse_server.base.models import Project, Family, FamilySearchFlag, ProjectGeneList, CausalVariant, ANALYSIS_STATUS_CHOICES

from xbrowse_server.decorators import log_request
from xbrowse_server.base.lookups import get_saved_variants_for_family
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server import json_displays
from xbrowse_server import sample_management
from xbrowse_server.mall import get_reference, get_datastore, get_coverage_store
from django.conf import settings
from django.core.exceptions import PermissionDenied
from xbrowse_server.matchmaker.utilities import find_latest_family_member_submissions

import logging

log = logging.getLogger('xbrowse_server')

@login_required
@log_request('families')
def families(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    cursor = connection.cursor()

    loaded_vcfs_subquery = """
      SELECT 
        COUNT(*) 
      FROM base_vcffile AS v 
        JOIN base_individual_vcf_files AS vi ON v.id=vi.vcffile_id
        JOIN base_individual AS i2 ON i2.id=vi.individual_id
      WHERE i2.family_id=f.id AND v.loaded_date IS NOT NULL
    """

    families_query = """
        SELECT DISTINCT
          f.family_id AS family_id,
          f.family_name AS family_name,
          COUNT(*) AS num_individuals,
          f.short_description AS short_description,
          f.analysis_status AS analysis_status,
          ({loaded_vcfs_subquery}) AS is_loaded,
          f.pedigree_image AS pedigree_image_url
        FROM base_family AS f
          JOIN base_individual AS i ON i.family_id=f.id
        WHERE f.project_id=%s
        GROUP BY f.id
    """.strip().format(**locals())

    cursor.execute(families_query, [project.id])

    columns = [col[0] for col in cursor.description]
    family_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    families_json = []
    for family in family_rows:
        families_json.append({
            'url': reverse('family_home', args=(project.project_id, family["family_id"])),
            'family_id': family["family_id"],
            'family_name': family["family_name"],
            'data_status': "loaded" if family["is_loaded"] else "not_loaded",
            'project_id': project.project_id,
            'num_individuals': family["num_individuals"],
            'short_description': family["short_description"],
            'analysis_status': {
                "status": family["analysis_status"],
            },
            'pedigree_image_url': os.path.join("/media/", family["pedigree_image_url"]) if family.get('pedigree_image_url') else None,
        })

    return render(request, 'family/families.html', {
        'project': project,
        'families_json': json.dumps(families_json),
        'analysis_statuses':  json.dumps(dict(ANALYSIS_STATUS_CHOICES)),
        'is_manager': 'true' if project.can_admin(request.user) else 'false',
        'is_staff': 'true' if request.user.is_staff else 'false',
        'new_page_url': '/project/{}/project_page'.format(project.seqr_project.guid) if project.seqr_project else None,
    })


@login_required
@log_request('family_home')
def family_home(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:
        exported_to_matchmaker=None
        submission_records=settings.SEQR_ID_TO_MME_ID_MAP.find({'project_id':project_id,'family_id':family_id}).sort('insertion_date',-1)
        latest_submissions_from_family = find_latest_family_member_submissions(submission_records)
        if len(latest_submissions_from_family)>0:
            exported_to_matchmaker={}
        for individual,submission in latest_submissions_from_family.iteritems():
            was_deleted_on=None
            was_deleted_by=None
            if submission.has_key("deletion"):
                was_deleted_on = submission['deletion']['date'].strftime('%d %b %Y')
                was_deleted_by = submission['deletion']['by']
            exported_to_matchmaker[individual] = {'insertion_date':submission['insertion_date'],'deletion_date':was_deleted_on, 'by':was_deleted_by}                  
        phenotips_supported=True
        if settings.PROJECTS_WITHOUT_PHENOTIPS is not None and project_id in settings.PROJECTS_WITHOUT_PHENOTIPS:
          phenotips_supported=False
         
        #Activating all projects
        matchmaker_supported=project.is_mme_enabled

        analysis_status_json = family.get_analysis_status_json()
        analysis_status_choices = dict(ANALYSIS_STATUS_CHOICES)
        analysis_status_desc_and_icon = analysis_status_choices[family.analysis_status]

        return render(request, 'family/family_home.html', {
            'phenotips_supported':phenotips_supported,
            'matchmaker_supported':matchmaker_supported,
            'project': project,
            'family': family,
            'user_can_edit': family.can_edit(request.user),
            'user_is_admin': project.can_admin(request.user),
            'saved_variants': FamilySearchFlag.objects.filter(family=family).order_by('-date_saved'),
            'analysis_status_desc_and_icon': analysis_status_desc_and_icon,
            'analysis_status_json': analysis_status_json,
            'exported_to_matchmaker':exported_to_matchmaker,
            #  TODO add matchmaker integration info to new page before depracating
            # 'new_page_url': '/project/{0}/family_page/{1}'.format(
            #     family.seqr_family.project.guid, family.seqr_family.guid) if family.seqr_family else None,
        })


@login_required
@log_request('family_edit')
@csrf_exempt
def edit_family(request, project_id, family_id):
    error = None

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        form = EditFamilyForm(request.POST, request.FILES)
        if form.is_valid():
            update_xbrowse_model(
                family,
                coded_phenotype=form.cleaned_data['coded_phenotype'],
                short_description=form.cleaned_data['short_description'],
                about_family_content=form.cleaned_data['about_family_content'],
                analysis_summary_content=form.cleaned_data['analysis_summary_content'],
                post_discovery_omim_number=form.cleaned_data['post_discovery_omim_number'])

            if family.analysis_status != form.cleaned_data['analysis_status']:
                if family.analysis_status not in ('Q', 'I'):
                    if not settings.DEBUG: settings.EVENTS_COLLECTION.insert({
                            'event_type': 'family_analysis_status_changed', 'project_id': project_id, 'family_id': family_id, 'date': timezone.now(), 
                            'username': request.user.username, 'email': request.user.email,
                            'from': family.analysis_status, 'to': form.cleaned_data['analysis_status'] })

                update_xbrowse_model(
                    family,
                    analysis_status=form.cleaned_data['analysis_status'],
                    analysis_status_date_saved=timezone.now(),
                    analysis_status_saved_by=request.user)

            if 'pedigree_image' in request.FILES:
                update_xbrowse_model(
                    family,
                    pedigree_image = request.FILES['pedigree_image'])

            return redirect('family_home', project_id=project.project_id, family_id=family.family_id)
    else:
        form = EditFamilyForm(initial={
            'coded_phenotype': family.coded_phenotype,
            'short_description': family.short_description,
            'about_family_content': family.about_family_content,
            'analysis_summary_content': family.analysis_summary_content,
            'post_discovery_omim_number': family.post_discovery_omim_number,
        })

    return render(request, 'family_edit.html', {
        'user': request.user,
        'project': project,
        'family': family,
        'error': error,
        'form': form,
        'analysis_statuses': ANALYSIS_STATUS_CHOICES,
        'new_page_url': '/project/{0}/family_page/{1}'.format(
            family.seqr_family.project.guid, family.seqr_family.guid) if family.seqr_family else None,
    })


@login_required
@log_request('family_delete')
@csrf_exempt
def delete(request, project_id, family_id):
    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            sample_management.delete_family(project.project_id, family.family_id)
            return redirect('families', project_id)

    return render(request, 'family/delete.html', {
        'project': project,
        'family': family,
    })

@login_required
@log_request('saved_family_variants')
def saved_variants(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    variants, couldntfind = get_saved_variants_for_family(family)

    # TODO: first this shouldnt be in API - base should never depend on api
    # TODO: also this should have better naming
    add_extra_info_to_variants_project(get_reference(), project, variants, add_family_tags=True, add_populations=True)

    return render(request, 'family/saved_family_variants.html', {
        'project': project,
        'family': family,
        'variants_json': json.dumps([v.toJSON() for v in variants]),
        'new_page_url': '/project/{0}/family_page/{1}'.format(
                family.seqr_family.project.guid, family.seqr_family.guid) if family.seqr_family else None,
    })


@login_required
@log_request('diagnostic_search')
def diagnostic_search(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    if not family.has_data('variation'):
        return render(request, 'analysis_unavailable.html', {
            'reason': 'This family does not have any variant data.'
        })
    elif project.project_status == Project.NEEDS_MORE_PHENOTYPES and not request.user.is_staff:
        return render(request, 'analysis_unavailable.html', {
            'reason': 'Awaiting phenotype data.'
        })

    gene_lists = project.get_gene_lists()
    gene_lists.extend(list(GeneList.objects.filter(owner=request.user)))
    gene_lists = list(set(gene_lists))

    return render(request, 'family/diagnostic_search.html', {
        'project': project,
        'family': family,
        'gene_lists_json': json.dumps([g.toJSON() for g in gene_lists]),
    })


@login_required
@log_request('family_coverage')
def family_coverage(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    if not family.has_data('exome_coverage'):
        return render(request, 'analysis_unavailable.html', {
            'reason': """Exome coverage data is not available for this family.
            These data must be generated from BAM files, which are not loaded to xBrowse by default -
            contact us if you want to activate this feature."""
        })

    gene_id = request.GET.get('gene_id')
    if gene_id:
        return family_coverage_gene(request, family, gene_id)

    gene_list_slug = request.GET.get('gene_list')
    if gene_list_slug:
        try:
            gene_list = GeneList.objects.get(slug=gene_list_slug)
        except ObjectDoesNotExist:
            return HttpResponse("Invalid gene list")
        if not ProjectGeneList.objects.filter(gene_list=gene_list, project=project):
            return HttpResponse("Invalid gene list")
        return family_coverage_gene_list(request, family, gene_list)

    return render(request, 'coverage/family_coverage.html', {
        'project': project,
        'family': family,
    })


# Not to be served directly
def family_coverage_gene(request, family, gene_id):

    project_id = family.project.project_id
    gene = get_reference().get_gene(gene_id)
    gene_structure = get_reference().get_gene_structure(gene_id)
    individuals = family.get_individuals()
    indiv_ids = [i.indiv_id for i in individuals]
    num_individuals = len(indiv_ids)

    coding_regions = []
    for c in get_coding_regions_from_gene_structure(gene_id, gene_structure):
        coding_region = {}
        coding_region['start'] = genomeloc.get_chr_pos(c.xstart)[1]
        coding_region['stop'] = genomeloc.get_chr_pos(c.xstop)[1]
        coding_region['gene_id'] = c.gene_id
        coding_region['size'] = c.xstop-c.xstart+1
        coding_regions.append(coding_region)

    coverages = {}
    for individual in individuals:
        coverages[individual.indiv_id] = get_coverage_store().get_coverage_for_gene(
            str(individual.pk),
            gene['gene_id']
        )

    whole_gene = Counter({'callable': 0, 'low_coverage': 0, 'poor_mapping': 0})
    for coverage_spec in coverages.values():
        whole_gene['callable'] += coverage_spec['gene_totals']['callable']
        whole_gene['low_coverage'] += coverage_spec['gene_totals']['low_coverage']
        whole_gene['poor_mapping'] += coverage_spec['gene_totals']['poor_mapping']
    gene_coding_size = 0
    for c in coding_regions:
        gene_coding_size += c['stop']-c['start']+1
    totalsize = gene_coding_size*num_individuals
    whole_gene['ratio_callable'] = whole_gene['callable'] / float(totalsize)
    whole_gene['ratio_low_coverage'] = whole_gene['low_coverage'] / float(totalsize)
    whole_gene['ratio_poor_mapping'] = whole_gene['poor_mapping'] / float(totalsize)
    whole_gene['gene_coding_size'] = gene_coding_size

    return render(request, 'coverage/family_coverage_gene.html', {
        'project': family.project,
        'family': family,
        'gene': gene,
        'coverages_json': json.dumps(coverages),
        'whole_gene_json': json.dumps(whole_gene),
        'coding_regions_json': json.dumps(coding_regions),
        'indiv_ids_json': json.dumps(indiv_ids),
        'individuals': individuals,
        'whole_gene': whole_gene,
    })


def family_coverage_gene_list(request, family, gene_list):
    """
    Table of summary coverages for each gene in the gene list
    """
    sample_id_list = [str(individual.pk) for individual in family.get_individuals()]

    cache_key = ('family_coverage_gene_list', family.project.project_id, family.family_id, gene_list.slug)
    cached_results = server_utils.get_cached_results(cache_key)
    if cached_results:
        gene_coverages = cached_results
    else:
        gene_coverages = []
        for gene_id in gene_list.gene_id_list():
            d = {
                'gene_id': gene_id,
                'gene_name': get_reference().get_gene_symbol(gene_id),
                'totals': get_coverage_store().get_coverage_totals_for_gene(gene_id, sample_id_list)
            }
            d['coding_size'] = sum(d['totals'].values())
            try:
                d['percent'] = float(d['totals']['callable'])*100 / d['coding_size']
            except ZeroDivisionError:
                d['percent'] = 0
            gene_coverages.append(d)
        server_utils.save_results_cache(cache_key, gene_coverages)

    return render(request, 'coverage/family_coverage_gene_list.html', {
        'project': family.project,
        'family': family,
        'gene_list': gene_list,
        'gene_coverages': gene_coverages,
    })


def family_gene_lookup(request, project_id, family_id):
    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    # variants = None
    # if request.GET.get('gene_id'):
    #     variants = list(settings.DATASTORE.get_variants_in_gene(project.project_id, family.family_id))
    #     add_extra_info_to_variants_family(settings.REFERENCE, family, variants)

    return render(request, 'family/gene_lookup.html', {
        'project': project,
        'family': family,
    })


@login_required
@log_request('edit_cause')
@csrf_exempt
def edit_family_cause(request, project_id, family_id):
    error = None

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    causal_variants = list(CausalVariant.objects.filter(family=family))

    if request.GET.get('variant'):
        xpos, ref, alt = request.GET['variant'].split('|')
        c = CausalVariant.objects.get_or_create(
            family=family,
            xpos=int(xpos),
            ref=ref,
            alt=alt,
        )[0]
        causal_variants = list(CausalVariant.objects.filter(family=family))

    if request.method == 'POST':
        form = EditFamilyCauseForm(family, request.POST)
        if form.is_valid():
            CausalVariant.objects.filter(family=family).delete()
            for v_str in request.POST.getlist('variants'):
                xpos, ref, alt = v_str.split('|')
                CausalVariant.objects.create(
                    family=family,
                    xpos=int(xpos),
                    ref=ref,
                    alt=alt,
                )
                update_xbrowse_model(
                    family,
                    analysis_status = 'S',
                    causal_inheritance_mode = form.cleaned_data['inheritance_mode'])

            return redirect('family_home', project_id=project.project_id, family_id=family.family_id)
        else:
            error = server_utils.form_error_string(form)
    else:
        form = EditFamilyForm(family)

    variants = []
    for c in causal_variants:
        variants.append(get_datastore(project).get_single_variant(project_id, family_id, c.xpos, c.ref, c.alt))

    return render(request, 'family/edit_cause.html', {
        'project': project,
        'family': family,
        'error': error,
        'form': form,
        'variants': [v.toJSON() for v in variants],
    })


@login_required
@log_request('pedigree_image_delete')
@csrf_exempt
def pedigree_image_delete(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_admin(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            update_xbrowse_model(family, pedigree_image = None)
            return redirect('family_home', project.project_id, family.family_id)

    return render(request, 'family/pedigree_image_delete.html', {
        'project': project,
        'family': family,
    })



# @login_required
# @log_request('family_slides')
# def slides(request, project_id, family_id):
#     project = get_object_or_404(Project, project_id=project_id)
#     family = get_object_or_404(Family, project=project, family_id=family_id)
#
#     if not project.can_view(request.user):
#         raise PermissionDenied
#
#     return render(request, 'family/slides.html', {
#         'project': project,
#         'family': family,
#         'slides': slides,
#     })


@login_required
@log_request('family_variant_view')
@csrf_exempt
def family_variant_view(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    try:
        xpos = int(request.GET.get('xpos'))
        ref = request.GET.get('ref')
        alt = request.GET.get('alt')
    except:
        return HttpResponse('Invalid View')

    variant = get_datastore(project).get_single_variant(project_id, family_id, xpos, ref, alt)
    add_extra_info_to_variants_project(get_reference(), project, [variant], add_family_tags=True, add_populations=True)

    return render(request, 'family/family_variant_view.html', {
        'project': project,
        'family': family,
        'variant_json': json.dumps(variant.toJSON()),
    })
