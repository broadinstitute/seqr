from collections import Counter
import json

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist

from xbrowse_server.gene_lists.models import GeneList
from xbrowse_server import server_utils
from xbrowse.reference.utils import get_coding_regions_from_gene_structure
from xbrowse.core import genomeloc
from xbrowse_server.base.forms import EditFamilyForm, EditFamilyCauseForm
from xbrowse_server.base.models import Project, Family, FamilySearchFlag, ProjectGeneList, CausalVariant, ANALYSIS_STATUS_CHOICES
from xbrowse_server.decorators import log_request
from xbrowse_server.base.lookups import get_saved_variants_for_family
from xbrowse_server.api.utils import add_extra_info_to_variants_family
from xbrowse_server import json_displays
from xbrowse_server import sample_management
from xbrowse_server.mall import get_reference, get_datastore, get_coverage_store
from django.conf import settings
from django.core.exceptions import PermissionDenied


@login_required
@log_request('families')
def families(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    families_json = json_displays.family_list(project.get_families())
    
    return render(request, 'family/families.html', {
        'project': project,
        'families_json': json.dumps(families_json),
        'analysis_statuses':  json.dumps(dict(ANALYSIS_STATUS_CHOICES)),
        'is_manager': 'true' if project.can_admin(request.user) else 'false',
    })


@login_required
@log_request('family_home')
def family_home(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    else:
        #phenotips_supported=False
        #if not (settings.PROJECTS_WITHOUT_PHENOTIPS is None or project_id in settings.PROJECTS_WITHOUT_PHENOTIPS):
        #    phenotips_supported=True
        phenotips_supported=True
        if settings.PROJECTS_WITHOUT_PHENOTIPS is not None and project_id in settings.PROJECTS_WITHOUT_PHENOTIPS:
          phenotips_supported=False

        analysis_status_json = family.get_analysis_status_json()
        analysis_status_choices = dict(ANALYSIS_STATUS_CHOICES)
        analysis_status_desc_and_icon = analysis_status_choices[family.analysis_status]
        return render(request, 'family/family_home.html', {
            'phenotips_supported':phenotips_supported,
            'project': project,
            'family': family,
            'user_can_edit': family.can_edit(request.user),
            'user_is_admin': project.can_admin(request.user),
            'saved_variants': FamilySearchFlag.objects.filter(family=family).order_by('-date_saved'),
            'analysis_status_desc_and_icon': analysis_status_desc_and_icon,
            'analysis_status_json': analysis_status_json,
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
            family.short_description = form.cleaned_data['short_description']
            family.about_family_content = form.cleaned_data['about_family_content']
            family.analysis_summary_content = form.cleaned_data['analysis_summary_content']

            if family.analysis_status != form.cleaned_data['analysis_status']:
                family.analysis_status = form.cleaned_data['analysis_status']
                family.analysis_status_date_saved = timezone.now()
                family.analysis_status_saved_by = request.user
            if 'pedigree_image' in request.FILES:
                family.pedigree_image = request.FILES['pedigree_image']
            family.save()

            return redirect('family_home', project_id=project.project_id, family_id=family.family_id)
    else:
        form = EditFamilyForm(initial={'short_description': family.short_description, 'about_family_content': family.about_family_content, 'analysis_summary_content': family.analysis_summary_content})

    return render(request, 'family_edit.html', {
        'project': project,
        'family': family,
        'error': error,
        'form': form,
        'analysis_statuses': ANALYSIS_STATUS_CHOICES,
    })


@login_required
@log_request('family_delete')
@csrf_exempt
def delete(request, project_id, family_id):
    error = None

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
    add_extra_info_to_variants_family(get_reference(), family, variants)

    return render(request, 'family/saved_family_variants.html', {
        'project': project,
        'family': family,
        'variants_json': json.dumps([v.toJSON() for v in variants]),
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
                c = CausalVariant.objects.create(
                    family=family,
                    xpos=int(xpos),
                    ref=ref,
                    alt=alt,
                )
                family.analysis_status = 'S'
                family.causal_inheritance_mode = form.cleaned_data['inheritance_mode']
                family.save()
            return redirect('family_home', project_id=project.project_id, family_id=family.family_id)
        else:
            error = server_utils.form_error_string(form)
    else:
        form = EditFamilyForm(family)

    variants = []
    for c in causal_variants:
        variants.append(get_datastore(project_id).get_single_variant(project_id, family_id, c.xpos, c.ref, c.alt))

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
            family.pedigree_image = None
            family.save()
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

    variant = get_datastore(project_id).get_single_variant(project_id, family_id, xpos, ref, alt)
    add_extra_info_to_variants_family(get_reference(), family, [variant])

    return render(request, 'family/family_variant_view.html', {
        'project': project,
        'family': family,
        'variant_json': json.dumps(variant.toJSON()),
    })
