import datetime
import csv

from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from xbrowse.analysis_modules.combine_mendelian_families import get_variants_by_family_for_gene
from xbrowse_server.analysis.diagnostic_search import get_gene_diangostic_info
from xbrowse_server.base.models import Project, Family, FamilySearchFlag, VariantNote, ProjectTag, VariantTag
from xbrowse_server.api.utils import get_project_and_family_for_user, get_project_and_cohort_for_user, add_extra_info_to_variants_family
from xbrowse_server.api import utils as api_utils
from xbrowse_server.api import forms as api_forms
from xbrowse_server.search_cache import utils as cache_utils
from xbrowse_server.decorators import log_request
from xbrowse_server.server_utils import JSONResponse
import utils
from xbrowse.variant_search import cohort as cohort_search
from xbrowse import Variant
from xbrowse.analysis_modules.mendelian_variant_search import MendelianVariantSearchSpec
from xbrowse.core import displays as xbrowse_displays
from xbrowse_server import server_utils
from . import basicauth
from xbrowse_server import user_controls


@csrf_exempt
@basicauth.logged_in_or_basicauth()
@log_request('projects_api')
def projects(request):
    """
    List the projects that this user has access to
    """
    user_projects = user_controls.get_projects_for_user(request.user)
    project_ids = [p.project_id for p in user_projects]
    response_format = request.GET.get('format', 'json')
    if response_format == 'json':
        return JSONResponse({'projects': project_ids})
    elif response_format == 'tsv':
        return HttpResponse('\n'.join(project_ids))
    else:
        raise Exception("Invalid format")


@csrf_exempt
@login_required
@log_request('mendelian_variant_search_api')
def mendelian_variant_search(request):

    # TODO: how about we move project getter into the form, and just test for authX here?
    # esp because error should be described in json, not just 404
    project, family = get_project_and_family_for_user(request.user, request.GET)

    form = api_forms.MendelianVariantSearchForm(request.GET)
    if form.is_valid():

        search_spec = form.cleaned_data['search_spec']
        search_spec.family_id = family.family_id

        variants = api_utils.calculate_mendelian_variant_search(search_spec, family.xfamily())
        search_hash = cache_utils.save_results_for_spec(project.project_id, search_spec.toJSON(), [v.toJSON() for v in variants])
        add_extra_info_to_variants_family(settings.REFERENCE, family, variants)

        return_type = request.GET.get('return_type', 'json')
        if return_type == 'json':
            return JSONResponse({
                'is_error': False,
                'variants': [v.toJSON() for v in variants],
                'search_hash': search_hash,
            })
        elif return_type == 'csv':
            return ''
        else:
            return HttpResponse("Return type not implemented")

    else:
        return JSONResponse({
            'is_error': True,
            'error': server_utils.form_error_string(form)
        })


@csrf_exempt
@login_required
@log_request('mendelian_variant_search_spec_api')
def mendelian_variant_search_spec(request):

    project, family = get_project_and_family_for_user(request.user, request.GET)

    # TODO: use form

    search_hash = request.GET.get('search_hash')
    search_spec_dict, variants = cache_utils.get_cached_results(project.project_id, search_hash)
    search_spec = MendelianVariantSearchSpec.fromJSON(search_spec_dict)
    if variants is None:
        variants = api_utils.calculate_mendelian_variant_search(search_spec, family.xfamily())
    else:
        variants = [Variant.fromJSON(v) for v in variants]
    add_extra_info_to_variants_family(settings.REFERENCE, family, variants)
    return_type = request.GET.get('return_type')
    if return_type == 'json' or not return_type:
        return JSONResponse({
            'is_error': False,
            'variants': [v.toJSON() for v in variants],
            'search_spec': search_spec_dict,
        })
    elif request.GET.get('return_type') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="xbrowse_results_{}.csv"'.format(search_hash)
        writer = csv.writer(response)
        indiv_ids = family.indiv_ids_with_variant_data()
        headers = xbrowse_displays.get_variant_display_headers(indiv_ids)
        writer.writerow(headers)
        for variant in variants:
            fields = xbrowse_displays.get_display_fields_for_variant(variant, settings.REFERENCE, indiv_ids)
            writer.writerow(fields)
        return response


@csrf_exempt
@login_required
@log_request('get_cohort_variants')
def cohort_variant_search(request):

    project, cohort = get_project_and_cohort_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    form = api_forms.CohortVariantSearchForm(request.GET)
    if form.is_valid():
        search_spec = form.cleaned_data['search_spec']
        search_spec.family_id = cohort.cohort_id

        variants = api_utils.calculate_mendelian_variant_search(search_spec, cohort.xfamily())
        search_hash = cache_utils.save_results_for_spec(project.project_id, search_spec.toJSON(), [v.toJSON() for v in variants])
        api_utils.add_extra_info_to_variants_cohort(settings.REFERENCE, cohort, variants)

        return JSONResponse({
            'is_error': False,
            'variants': [v.toJSON() for v in variants],
            'search_hash': search_hash,
        })

    else:
        return JSONResponse({
            'is_error': True,
            'error': server_utils.form_error_string(form)
        })


@csrf_exempt
@login_required
@log_request('cohort_variant_search_spec_api')
def cohort_variant_search_spec(request):

    project, cohort = get_project_and_cohort_for_user(request.user, request.GET)

    # TODO: use form

    search_spec_dict, variants = cache_utils.get_cached_results(project.project_id, request.GET.get('search_hash'))
    search_spec = MendelianVariantSearchSpec.fromJSON(search_spec_dict)
    if variants is None:
        variants = api_utils.calculate_mendelian_variant_search(search_spec, cohort.xfamily())
    else:
        variants = [Variant.fromJSON(v) for v in variants]
    api_utils.add_extra_info_to_variants_cohort(settings.REFERENCE, cohort, variants)

    return JSONResponse({
        'is_error': False,
        'variants': [v.toJSON() for v in variants],
        'search_spec': search_spec.toJSON(),
    })


@csrf_exempt
@login_required
@log_request('cohort_gene_search')
def cohort_gene_search(request):

    project, cohort = get_project_and_cohort_for_user(request.user, request.GET)

    form = api_forms.CohortGeneSearchForm(request.GET)
    if form.is_valid():
        search_spec = form.cleaned_data['search_spec']
        search_spec.cohort_id = cohort.cohort_id

        genes = api_utils.calculate_cohort_gene_search(cohort, search_spec)
        search_hash = cache_utils.save_results_for_spec(project.project_id, search_spec.toJSON(), genes)
        api_utils.add_extra_info_to_genes(project, settings.REFERENCE, genes)

        return JSONResponse({
            'is_error': False,
            'genes': genes,
            'search_hash': search_hash,
        })

    else:
        return JSONResponse({
            'is_error': True,
            'error': server_utils.form_error_string(form)
        })


@csrf_exempt
@login_required
@log_request('cohort_gene_search_spec')
def cohort_gene_search_spec(request):

    project, cohort = get_project_and_cohort_for_user(request.user, request.GET)

    # TODO: use form

    search_spec, genes = cache_utils.get_cached_results(project.project_id, request.GET.get('search_hash'))
    if genes is None:
        genes = api_utils.calculate_cohort_gene_search(cohort, search_spec)
    api_utils.add_extra_info_to_genes(project, settings.REFERENCE, genes)

    return JSONResponse({
        'is_error': False,
        'genes': genes,
        'search_spec': search_spec,
    })


@csrf_exempt
@login_required
@log_request('cohort_gene_search_variants')
def cohort_gene_search_variants(request):

    # TODO: this view not like the others - refactor to forms

    error = None

    project, cohort = get_project_and_cohort_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    form = api_forms.CohortGeneSearchVariantsForm(request.GET)
    if form.is_valid():
        gene_id = form.cleaned_data['gene_id']
        inheritance_mode = form.cleaned_data['inheritance_mode']
        variant_filter = form.cleaned_data['variant_filter']
        quality_filter = form.cleaned_data['quality_filter']
    else:
        error = server_utils.form_error_string(form)

    if not error:

        indivs_with_inheritance, gene_variation = cohort_search.get_individuals_with_inheritance_in_gene(
            settings.DATASTORE,
            settings.REFERENCE,
            cohort.xcohort(),
            inheritance_mode,
            gene_id,
            variant_filter=variant_filter,
            quality_filter=quality_filter
        )

        relevant_variants = gene_variation.get_relevant_variants_for_indiv_ids(cohort.indiv_id_list())

        api_utils.add_extra_info_to_variants_family(settings.REFERENCE, cohort, relevant_variants)

        ret = {
            'is_error': False, 
            'variants': [v.toJSON() for v in relevant_variants],
            'gene_info': settings.REFERENCE.get_gene(gene_id),
        }
        return JSONResponse(ret)

    else: 
        ret = {
            'is_error': True, 
            'error': error
        }
        return JSONResponse(ret)


@login_required
@log_request('gene_info')
def gene_info(request, gene_id):

    gene = settings.REFERENCE.get_gene(gene_id)
    gene['expression'] = settings.REFERENCE.get_tissue_expression_display_values(gene_id)

    ret = {
        'gene': gene,
        'is_error': False, 
        'found_gene': gene is not None, 
    }

    return JSONResponse(ret)


@login_required
@log_request('family_variant_annotation')
def family_variant_annotation(request):

    # TODO: this view not like the others - refactor to forms

    error = None

    for key in ['project_id', 'family_id', 'xpos', 'ref', 'alt']:
        if request.GET.get(key) is None:
            error = "%s is requred", key

    if not error:
        project = get_object_or_404(Project, project_id=request.GET.get('project_id'))
        family = get_object_or_404(Family, project=project, family_id=request.GET.get('family_id'))
        if not project.can_view(request.user):
            return HttpResponse('unauthorized')

    if not error:
        variant = settings.DATASTORE.get_single_variant(
            family.project.project_id,
            family.family_id,
            int(request.GET['xpos']),
            request.GET['ref'],
            request.GET['alt']
        )

        if not variant:
            error = "Variant does not exist"

    if not error:
        ret = {
            'variant': variant.toJSON(),
            'is_error': False,
            }

    else:
        ret = {
            'is_error': True,
            'error': error,
        }

    return JSONResponse(ret)


@login_required
@log_request('add_flag')
def add_family_search_flag(request):

    # TODO: this view not like the others - refactor to forms

    error = None

    for key in ['project_id', 'family_id', 'xpos', 'ref', 'alt', 'note', 'flag_type', 'flag_inheritance_mode']:
        if request.GET.get(key, None) == None:
            error = "%s is requred" % key

    if not error:
        project = get_object_or_404(Project, project_id=request.GET.get('project_id'))
        family = get_object_or_404(Family, project=project, family_id=request.GET.get('family_id'))
        if not project.can_edit(request.user):
            return HttpResponse('unauthorized')

    if not error:
        xpos = int(request.GET['xpos'])
        ref=request.GET.get('ref')
        alt=request.GET['alt']
        note=request.GET.get('note')
        flag_type=request.GET.get('flag_type')
        flag_inheritance_mode=request.GET.get('flag_inheritance_mode')

        # todo: more validation - is variant valid?

        flag = FamilySearchFlag(user=request.user,
            family=family,
            xpos=int(request.GET['xpos']),
            ref=ref,
            alt=alt,
            note=note,
            flag_type=flag_type,
            suggested_inheritance=flag_inheritance_mode,
            date_saved = datetime.datetime.now(),
        )

    if not error:
        flag.save()
        variant = settings.DATASTORE.get_single_variant(family.project.project_id, family.family_id,
            xpos, ref, alt )
        api_utils.add_extra_info_to_variant(settings.REFERENCE, family, variant)

        ret = {
            'is_error': False,
            'variant': variant.toJSON(),
        }

    else:
        ret = {
            'is_error': True,
            'error': error,
        }
    return JSONResponse(ret)


@login_required
@log_request('add_variant_note')
def add_variant_note(request):
    """

    """
    family = None
    if 'family_id' in request.GET:
        project, family = get_project_and_family_for_user(request.user, request.GET)
    else:
        project = utils.get_project_for_user(request.user, request.GET)

    form = api_forms.VariantNoteForm(project, request.GET)
    if form.is_valid():
        note = VariantNote.objects.create(
            user=request.user,
            date_saved=datetime.datetime.now(),
            project=project,
            note=form.cleaned_data['note_text'],
            xpos=form.cleaned_data['xpos'],
            ref=form.cleaned_data['ref'],
            alt=form.cleaned_data['alt'],
        )
        if family:
            note.family = family
            note.save()
        variant = settings.DATASTORE.get_single_variant(
            project.project_id,
            family.family_id,
            form.cleaned_data['xpos'],
            form.cleaned_data['ref'],
            form.cleaned_data['alt'],
        )
        add_extra_info_to_variants_family(settings.REFERENCE, family, [variant,])
        ret = {
            'is_error': False,
            'variant': variant.toJSON(),
        }
    else:
        ret = {
            'is_error': True,
            'error': server_utils.form_error_string(form)
        }
    return JSONResponse(ret)


@login_required
@log_request('edit_variant_tags')
def edit_variant_tags(request):

    family = None
    if 'family_id' in request.GET:
        project, family = get_project_and_family_for_user(request.user, request.GET)
    else:
        project = utils.get_project_for_user(request.user, request.GET)

    form = api_forms.VariantTagsForm(project, request.GET)
    if form.is_valid():
        VariantTag.objects.filter(family=family).delete()
        for project_tag in form.cleaned_data['project_tags']:
            VariantTag.objects.create(
                project_tag=project_tag,
                family=family,
                xpos=form.cleaned_data['xpos'],
                ref=form.cleaned_data['ref'],
                alt=form.cleaned_data['alt'],
            )
        variant = settings.DATASTORE.get_single_variant(
            project.project_id,
            family.family_id,
            form.cleaned_data['xpos'],
            form.cleaned_data['ref'],
            form.cleaned_data['alt'],
        )
        add_extra_info_to_variants_family(settings.REFERENCE, family, [variant,])
        ret = {
            'is_error': False,
            'variant': variant.toJSON(),
        }
    else:
        ret = {
            'is_error': True,
            'error': server_utils.form_error_string(form)
        }
    return JSONResponse(ret)


GENE_ITEMS = {
    v.lower(): {
        'gene_id': k,
        'symbol': v
    }
    for k, v in settings.REFERENCE.get_gene_symbols().items()
}


def gene_autocomplete(request):

    query = request.GET.get('q', '')

    genes = [{
        'value': item['gene_id'],
        'label': item['symbol'],
    } for k, item in GENE_ITEMS.items() if k.startswith(query.lower())][:20]

    return JSONResponse(genes)


@login_required
@log_request('variant_info')
def variant_info(request):
    pass


@csrf_exempt
@login_required
@log_request('combine_mendelian_families_api')
def combine_mendelian_families(request):

    project, family_group = utils.get_project_and_family_group_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    form = api_forms.CombineMendelianFamiliesForm(request.GET)
    if form.is_valid():

        search_spec = form.cleaned_data['search_spec']
        search_spec.family_group_id = family_group.slug

        genes = api_utils.calculate_combine_mendelian_families(family_group, search_spec)
        search_hash = cache_utils.save_results_for_spec(project.project_id, search_spec.toJSON(), genes)
        api_utils.add_extra_info_to_genes(project, settings.REFERENCE, genes)

        return JSONResponse({
            'is_error': False,
            'genes': genes,
            'search_hash': search_hash,
        })

    else:
        return JSONResponse({
            'is_error': True,
            'error': server_utils.form_error_string(form)
        })


@csrf_exempt
@login_required
@log_request('mendelian_variant_search_spec_api')
def combine_mendelian_families_spec(request):

    project, family_group = utils.get_project_and_family_group_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    search_spec, genes = cache_utils.get_cached_results(project.project_id, request.GET.get('search_hash'))
    if genes is None:
        genes = api_utils.calculate_combine_mendelian_families(family_group, search_spec)
    api_utils.add_extra_info_to_genes(project, settings.REFERENCE, genes)
    return JSONResponse({
        'is_error': False,
        'genes': genes,
        'search_spec': search_spec,
    })



@csrf_exempt
@login_required
@log_request('combine_mendelian_families_variants_api')
def combine_mendelian_families_variants(request):

    project, family_group = utils.get_project_and_family_group_for_user(request.user, request.GET)

    form = api_forms.CombineMendelianFamiliesVariantsForm(request.GET)
    if form.is_valid():
        variants_grouped = get_variants_by_family_for_gene(
            settings.DATASTORE,
            settings.REFERENCE,
            [f.xfamily() for f in form.cleaned_data['families']],
            form.cleaned_data['inheritance_mode'],
            form.cleaned_data['gene_id'],
            variant_filter=form.cleaned_data['variant_filter'],
            quality_filter=form.cleaned_data['quality_filter']
        )
        variants_by_family = []
        for family in form.cleaned_data['families']:
            variants = variants_grouped[(family.project.project_id, family.family_id)]
            add_extra_info_to_variants_family(settings.REFERENCE, family, variants)
            variants_by_family.append({
                'project_id': family.project.project_id,
                'family_id': family.family_id,
                'family_name': str(family),
                'variants': [v.toJSON() for v in variants],
            })
        return JSONResponse({
            'is_error': False,
            'variants_by_family': variants_by_family,
        })

    else:
        return JSONResponse({
            'is_error': True,
            'error': server_utils.form_error_string(form)
        })


@csrf_exempt
@login_required
@log_request('diagnostic_search')
def diagnostic_search(request):

    project, family = utils.get_project_and_family_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    form = api_forms.DiagnosticSearchForm(family, request.GET)
    if form.is_valid():

        search_spec = form.cleaned_data['search_spec']
        search_spec.family_id = family.family_id

        gene_list = form.cleaned_data['gene_list']
        diagnostic_info_list = []
        for gene_id in gene_list.gene_id_list():
            diagnostic_info = get_gene_diangostic_info(family, gene_id, search_spec.variant_filter)
            add_extra_info_to_variants_family(settings.REFERENCE, family, diagnostic_info._variants)
            diagnostic_info_list.append(diagnostic_info)



        return JSONResponse({
            'is_error': False,
            'gene_diagnostic_info_list': [d.toJSON() for d in diagnostic_info_list],
            'gene_list_info': gene_list.toJSON(details=True),
            'data_summary': family.get_data_summary(),
        })

    else:
        return JSONResponse({
            'is_error': True,
            'error': server_utils.form_error_string(form)
        })


def family_gene_lookup(request):
    project, family = utils.get_project_and_family_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')
    gene_id = request.GET.get('gene_id')
    if not settings.REFERENCE.is_valid_gene_id(gene_id):
        return JSONResponse({
            'is_error': True,
            'error': 'Invalid gene',
        })
    family_gene_data = get_gene_diangostic_info(family, gene_id)
    add_extra_info_to_variants_family(settings.REFERENCE, family, family_gene_data._variants)
    return JSONResponse({
        'is_error': False,
        'family_gene_data': family_gene_data.toJSON(),
        'data_summary': family.get_data_summary(),
        'gene': settings.REFERENCE.get_gene(gene_id),
    })
