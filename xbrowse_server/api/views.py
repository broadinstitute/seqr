import datetime
import csv
import json
import logging
import sys
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

from xbrowse.analysis_modules.combine_mendelian_families import get_variants_by_family_for_gene
from xbrowse_server.analysis.diagnostic_search import get_gene_diangostic_info
from xbrowse_server.base.models import Project, Family, FamilySearchFlag, VariantNote, ProjectTag, VariantTag
from xbrowse_server.api.utils import get_project_and_family_for_user, get_project_and_cohort_for_user, add_extra_info_to_variants_family
from xbrowse.variant_search.family import get_variants_with_inheritance_mode
from xbrowse_server.api import utils as api_utils
from xbrowse_server.api import forms as api_forms
from xbrowse_server.mall import get_reference, get_datastore, get_mall
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
from django.utils import timezone


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

        try:
            variants = api_utils.calculate_mendelian_variant_search(search_spec, family.xfamily())
        except Exception as e:
            return JSONResponse({
                    'is_error': True,
                    'error': str(e.args[0]) if e.args else str(e)
            })

        hashable_search_params = search_spec.toJSON()
        hashable_search_params['family_id'] = family.family_id

        search_hash = cache_utils.save_results_for_spec(project.project_id, hashable_search_params, [v.toJSON() for v in variants])
        add_extra_info_to_variants_family(get_reference(), family, variants)

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

    search_hash = request.GET.get('search_hash')
    search_spec_dict, variants = cache_utils.get_cached_results(project.project_id, search_hash)
    search_spec = MendelianVariantSearchSpec.fromJSON(search_spec_dict)
    if variants is None:
        variants = api_utils.calculate_mendelian_variant_search(search_spec, family.xfamily())
    else:
        variants = [Variant.fromJSON(v) for v in variants]
    add_extra_info_to_variants_family(get_reference(), family, variants)
    return_type = request.GET.get('return_type')
    if return_type == 'json' or not return_type:
        return JSONResponse({
            'is_error': False,
            'variants': [v.toJSON() for v in variants],
            'search_spec': search_spec_dict,
        })
    elif request.GET.get('return_type') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="results_{}.csv"'.format(search_hash)
        writer = csv.writer(response)
        indiv_ids = family.indiv_ids_with_variant_data()
        headers = xbrowse_displays.get_variant_display_headers(get_mall(project.project_id), project, indiv_ids)
        writer.writerow(headers)
        for variant in variants:
            fields = xbrowse_displays.get_display_fields_for_variant(get_mall(project.project_id), project, variant, indiv_ids)
            writer.writerow(fields)
        return response


@csrf_exempt
@login_required
@log_request('get_cohort_variants')
def cohort_variant_search(request):

    project, cohort = get_project_and_cohort_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return PermissionDenied

    form = api_forms.CohortVariantSearchForm(request.GET)
    if form.is_valid():
        search_spec = form.cleaned_data['search_spec']
        search_spec.family_id = cohort.cohort_id

        sys.stderr.write("cohort_variant_search - starting: %s  %s\n" % (json.dumps(search_spec.toJSON()), cohort.xfamily().family_id))
        variants = api_utils.calculate_mendelian_variant_search(search_spec, cohort.xfamily())

        list_of_variants = [v.toJSON() for v in variants]
        sys.stderr.write("cohort_variant_search - done calculate_mendelian_variant_search: %s  %s %s\n" % (json.dumps(search_spec.toJSON()), cohort.xfamily().family_id, len(list_of_variants)))
        search_hash = cache_utils.save_results_for_spec(project.project_id, search_spec.toJSON(), list_of_variants)

        sys.stderr.write("cohort_variant_search - done save_results_for_spec: %s  %s\n" % (json.dumps(search_spec.toJSON()), cohort.xfamily().family_id))
        api_utils.add_extra_info_to_variants_cohort(get_reference(), cohort, variants)

        sys.stderr.write("cohort_variant_search - done add_extra_info_to_variants_cohort: %s  %s\n" % (json.dumps(search_spec.toJSON()), cohort.xfamily().family_id))
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
    api_utils.add_extra_info_to_variants_cohort(get_reference(), cohort, variants)

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
    sys.stderr.write("cohort_gene_search %s  %s: starting ... \n" % (project.project_id, cohort.cohort_id))
    form = api_forms.CohortGeneSearchForm(request.GET)
    if form.is_valid():
        search_spec = form.cleaned_data['search_spec']
        search_spec.cohort_id = cohort.cohort_id
        sys.stderr.write("cohort_gene_search %s  %s: search spec: %s \n" % (project.project_id, cohort.cohort_id, str(search_spec.toJSON())))
        genes = api_utils.calculate_cohort_gene_search(cohort, search_spec)
        sys.stderr.write("cohort_gene_search %s  %s: get %s genes \n" % (project.project_id, cohort.cohort_id, len(genes)))
        search_hash = cache_utils.save_results_for_spec(project.project_id, search_spec.toJSON(), genes)
        api_utils.add_extra_info_to_genes(project, get_reference(), genes)
        sys.stderr.write("cohort_gene_search %s  %s: done adding extra info \n" % (project.project_id, cohort.cohort_id))
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

    search_spec, genes = cache_utils.get_cached_results(project.project_id, request.GET.get('search_hash'))
    if genes is None:
        genes = api_utils.calculate_cohort_gene_search(cohort, search_spec)
    api_utils.add_extra_info_to_genes(project, get_reference(), genes)

    return JSONResponse({
        'is_error': False,
        'genes': genes,
        'search_spec': search_spec,
    })


@csrf_exempt
@login_required
@log_request('cohort_gene_search_variants')
def cohort_gene_search_variants(request):

    error = None

    project, cohort = get_project_and_cohort_for_user(request.user, request.GET)
    if not project.can_view(request.user):
        return PermissionDenied

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
            get_datastore(project.project_id),
            get_reference(),
            cohort.xcohort(),
            inheritance_mode,
            gene_id,
            variant_filter=variant_filter,
            quality_filter=quality_filter
        )

        relevant_variants = gene_variation.get_relevant_variants_for_indiv_ids(cohort.indiv_id_list())

        api_utils.add_extra_info_to_variants_family(get_reference(), cohort, relevant_variants)

        ret = {
            'is_error': False, 
            'variants': [v.toJSON() for v in relevant_variants],
            'gene_info': get_reference().get_gene(gene_id),
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

    gene = get_reference().get_gene(gene_id)
    gene['expression'] = get_reference().get_tissue_expression_display_values(gene_id)

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
            return PermissionDenied

    if not error:
        variant = get_datastore(project.project_id).get_single_variant(
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

    error = None

    for key in ['project_id', 'family_id', 'xpos', 'ref', 'alt', 'note', 'flag_type', 'flag_inheritance_mode']:
        if request.GET.get(key, None) == None:
            error = "%s is requred" % key

    if not error:
        project = get_object_or_404(Project, project_id=request.GET.get('project_id'))
        family = get_object_or_404(Family, project=project, family_id=request.GET.get('family_id'))
        if not project.can_edit(request.user):
            return PermissionDenied

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
            date_saved=timezone.now(),
        )

    if not error:
        flag.save()
        variant = get_datastore(project.project_id).get_single_variant(family.project.project_id, family.family_id,
            xpos, ref, alt )
        api_utils.add_extra_info_to_variant(get_reference(), family, variant)

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
@log_request('delete_variant_note')
def delete_variant_note(request, note_id):
    ret = {
        'is_error': False,
    }

    notes = VariantNote.objects.filter(id=note_id)
    if not notes:
        ret['is_error'] = True
        ret['error'] = 'note id %s not found' % note_id
    else:
        note = list(notes)[0]
        if not note.project.can_edit(request.user):
            raise PermissionDenied

        note.delete()

    return JSONResponse(ret)

@login_required
@log_request('add_or_edit_variant_note')
def add_or_edit_variant_note(request):
    """Add a variant note"""
    family = None
    if 'family_id' in request.GET:
        project, family = get_project_and_family_for_user(request.user, request.GET)
    else:
        project = utils.get_project_for_user(request.user, request.GET)

    form = api_forms.VariantNoteForm(project, request.GET)
    if not form.is_valid():
        return JSONResponse({
            'is_error': True,
            'error': server_utils.form_error_string(form)
        })

    variant = get_datastore(project.project_id).get_single_variant(
        project.project_id,
        family.family_id,
        form.cleaned_data['xpos'],
        form.cleaned_data['ref'],
        form.cleaned_data['alt'],
    )

    if not variant:
        variant = Variant.fromJSON({
            'xpos' : form.cleaned_data['xpos'], 'ref': form.cleaned_data['ref'], 'alt': form.cleaned_data['alt'],
            'genotypes': {}, 'extras': {},
        })

    if 'note_id' in form.cleaned_data and form.cleaned_data['note_id']:
        event_type = "edit_variant_note"

        notes = VariantNote.objects.filter(
            id=form.cleaned_data['note_id'],
            project=project,
            xpos=form.cleaned_data['xpos'],
            ref=form.cleaned_data['ref'],
            alt=form.cleaned_data['alt'],
        )
        if not notes:
            return JSONResponse({
                'is_error': True,
                'error': 'note id %s not found' % form.cleaned_data['note_id']
            })

        note = notes[0]
        note.user = request.user
        note.note = form.cleaned_data['note_text']
        note.date_saved = timezone.now()
        if family:
            note.family = family
        note.save()
    else:
        event_type = "add_variant_note"

        VariantNote.objects.create(
            user=request.user,
            project=project,
            xpos=form.cleaned_data['xpos'],
            ref=form.cleaned_data['ref'],
            alt=form.cleaned_data['alt'],
            note=form.cleaned_data['note_text'],
            date_saved=timezone.now(),
            family=family,
        )

    add_extra_info_to_variants_family(get_reference(), family, [variant,])

    try:
        settings.EVENTS_COLLECTION.insert({
            'event_type': event_type,
            'date': timezone.now(),
            'project_id': ''.join(project.project_id),
            'family_id': family.family_id,
            'note': form.cleaned_data['note_text'],

            'xpos':form.cleaned_data['xpos'],
            'pos':variant.pos,
            'chrom': variant.chr,
            'ref':form.cleaned_data['ref'],
            'alt':form.cleaned_data['alt'],
            'gene_names': ", ".join(variant.extras['gene_names'].values()),
            'username': request.user.username,
            'email': request.user.email,
        })
    except Exception as e:
        logging.error("Error while logging %s event: %s" % (event_type, e))


    return JSONResponse({
        'is_error': False,
        'variant': variant.toJSON(),
    })



@login_required
@log_request('add_or_edit_variant_tags')
def add_or_edit_variant_tags(request):

    family = None
    if 'family_id' in request.GET:
        project, family = get_project_and_family_for_user(request.user, request.GET)
    else:
        project = utils.get_project_for_user(request.user, request.GET)

    form = api_forms.VariantTagsForm(project, request.GET)
    if not form.is_valid():
        ret = {
            'is_error': True,
            'error': server_utils.form_error_string(form)
        }
        return JSONResponse(ret)

    variant = get_datastore(project.project_id).get_single_variant(
            project.project_id,
            family.family_id,
            form.cleaned_data['xpos'],
            form.cleaned_data['ref'],
            form.cleaned_data['alt'],
    )

    if not variant:
        variant = Variant(form.cleaned_data['xpos'], form.cleaned_data['ref'], form.cleaned_data['alt'])

    variant_tags_to_delete = {
        variant_tag.id: variant_tag for variant_tag in VariantTag.objects.filter(
            family=family,
            xpos=form.cleaned_data['xpos'],
            ref=form.cleaned_data['ref'],
            alt=form.cleaned_data['alt'])
    }

    project_tag_events = {}
    for project_tag in form.cleaned_data['project_tags']:
        # retrieve tags
        tag, created = VariantTag.objects.get_or_create(
            project_tag=project_tag,
            family=family,
            xpos=form.cleaned_data['xpos'],
            ref=form.cleaned_data['ref'],
            alt=form.cleaned_data['alt'],
        )

        if not created:
            # this tag already exists so just keep it (eg. remove it from the set of tags that will be deleted)
            del variant_tags_to_delete[tag.id]
            continue

        # this a new tag, so update who saved it and when
        project_tag_events[project_tag] = "add_variant_tag"

        tag.user = request.user
        tag.date_saved = timezone.now()
        tag.search_url = form.cleaned_data['search_url']
        tag.save()

    # delete the tags that are no longer checked.
    for variant_tag in variant_tags_to_delete.values():
        project_tag_events[variant_tag.project_tag] = "delete_variant_tag"
        variant_tag.delete()


    # add the extra info after updating the tag info in the database, so that the new tag info is added to the variant JSON
    add_extra_info_to_variants_family(get_reference(), family, [variant,])

    # log tag creation
    for project_tag, event_type in project_tag_events.items():
        try:
            settings.EVENTS_COLLECTION.insert({
                'event_type': event_type,
                'date': timezone.now(),
                'project_id': ''.join(project.project_id),
                'family_id': family.family_id,
                'tag': project_tag.tag,
                'title': project_tag.title,

                'xpos':form.cleaned_data['xpos'],
                'pos':variant.pos,
                'chrom': variant.chr,
                'ref':form.cleaned_data['ref'],
                'alt':form.cleaned_data['alt'],
                'gene_names': ", ".join(variant.extras['gene_names'].values()),
                'username': request.user.username,
                'email': request.user.email,
                'search_url': form.cleaned_data.get('search_url'),
            })
        except Exception as e:
            logging.error("Error while logging add_variant_tag event: %s" % e)

    return JSONResponse({
        'is_error': False,
        'variant': variant.toJSON(),
    })



try:
    GENE_ITEMS = {
        v.lower(): {
            'gene_id': k,
            'symbol': v
            }
        for k, v in get_reference().get_gene_symbols().items()
        }
except Exception as e:
    print("WARNING: %s" % e)


def gene_autocomplete(request):

    query = request.GET.get('q', '')
    #sys.stderr.write("Gene autocomplete for: " + str(query) + "\n")

    gene_items = sorted([(k, item) for k, item in GENE_ITEMS.items() if k.startswith(query.lower())], key=lambda i: len(i[0]))
    genes = [{
        'value': item['gene_id'],
        'label': item['symbol'],
    } for k, item in gene_items[:20]]

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
        return PermissionDenied

    form = api_forms.CombineMendelianFamiliesForm(request.GET)
    if form.is_valid():

        search_spec = form.cleaned_data['search_spec']
        search_spec.family_group_id = family_group.slug

        genes = api_utils.calculate_combine_mendelian_families(family_group, search_spec)
        search_hash = cache_utils.save_results_for_spec(project.project_id, search_spec.toJSON(), genes)
        api_utils.add_extra_info_to_genes(project, get_reference(), genes)

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
        raise PermissionDenied

    search_hash = request.GET.get('search_hash')
    search_spec, genes = cache_utils.get_cached_results(project.project_id, search_hash)
    search_spec_obj = MendelianVariantSearchSpec.fromJSON(search_spec)

    if request.GET.get('return_type') != 'csv' or not request.GET.get('group_by_variants'):
        if genes is None:
            genes = api_utils.calculate_combine_mendelian_families(family_group, search_spec)
        api_utils.add_extra_info_to_genes(project, get_reference(), genes)
    
        if request.GET.get('return_type') != 'csv':
            return JSONResponse({
                    'is_error': False,
                    'genes': genes,
                    'search_spec': search_spec,
                    })
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="family_group_results_{}.csv"'.format(search_hash)
            writer = csv.writer(response)
            writer.writerow(["gene", "# families", "family list", "chrom", "start", "end"])
            for gene in genes:
                family_id_list = [family_id for (project_id, family_id) in gene["family_id_list"]]
                writer.writerow(map(str, [gene["gene_name"], len(family_id_list), " ".join(family_id_list), gene["chr"], gene["start"], gene["end"], ""]))
            return response
    else:
        # download results grouped by variant
        indiv_id_list = []
        for family in family_group.get_families():
            indiv_id_list.extend(family.indiv_ids_with_variant_data())

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="results_{}.csv"'.format(search_hash)
        writer = csv.writer(response)
        
        headers = ['genes','chr','pos','ref','alt','worst_annotation' ]
        headers.extend(project.get_reference_population_slugs())
        headers.extend([ 'polyphen','sift','muttaster','fathmm'])
        for indiv_id in indiv_id_list:
            headers.append(indiv_id)
            headers.append(indiv_id+'_gq')
            headers.append(indiv_id+'_dp')
        
        writer.writerow(headers)

        mall = get_mall(project.project_id)
        variant_key_to_individual_id_to_variant = defaultdict(dict)
        variant_key_to_variant = {}
        for family in family_group.get_families():
            for variant in get_variants_with_inheritance_mode(
                mall,
                family.xfamily(),
                search_spec_obj.inheritance_mode,
                search_spec_obj.variant_filter,
                search_spec_obj.quality_filter,
                ):
                if len(variant.coding_gene_ids) == 0:
                    continue

                variant_key = (variant.xpos, variant.ref, variant.alt)
                variant_key_to_variant[variant_key] = variant
                for indiv_id in family.indiv_ids_with_variant_data():
                    variant_key_to_individual_id_to_variant[variant_key][indiv_id] = variant
                    
        for variant_key in sorted(variant_key_to_individual_id_to_variant.keys()):
            variant = variant_key_to_variant[variant_key]
            individual_id_to_variant = variant_key_to_individual_id_to_variant[variant_key]

            genes = [mall.reference.get_gene_symbol(gene_id) for gene_id in variant.coding_gene_ids]
            fields = []
            fields.append(','.join(genes))
            fields.extend([
                        variant.chr,
                        str(variant.pos),
                        variant.ref,
                        variant.alt,
                        variant.annotation.get('vep_group', '.'),
                        ])
            for ref_population_slug in project.get_reference_population_slugs():
                fields.append(variant.annotation['freqs'][ref_population_slug])
            for field_key in ['polyphen', 'sift', 'muttaster', 'fathmm']:
                fields.append(variant.annotation[field_key])

            for indiv_id in indiv_id_list:
                variant = individual_id_to_variant.get(indiv_id)                    
                genotype = None
                if variant is not None:
                    genotype = variant.get_genotype(indiv_id)

                if genotype is None:
                    fields.extend(['.', '.', '.'])
                else:
                    if genotype.num_alt == 0:
                        fields.append("%s/%s" % (variant.ref, variant.ref))
                    elif genotype.num_alt == 1:
                        fields.append("%s/%s" % (variant.ref, variant.alt))
                    elif genotype.num_alt == 2:
                        fields.append("%s/%s" % (variant.alt, variant.alt))
                    else:
                        fields.append("./.")

                    fields.append(str(genotype.gq) if genotype.gq is not None else '.')
                    fields.append(genotype.extras['dp'] if genotype.extras.get('dp') is not None else '.')    
            writer.writerow(fields)
        return response        


@csrf_exempt
@login_required
@log_request('combine_mendelian_families_variants_api')
def combine_mendelian_families_variants(request):

    project, family_group = utils.get_project_and_family_group_for_user(request.user, request.GET)

    form = api_forms.CombineMendelianFamiliesVariantsForm(request.GET)
    if form.is_valid():
        variants_grouped = get_variants_by_family_for_gene(
            get_mall(project.project_id),
            [f.xfamily() for f in form.cleaned_data['families']],
            form.cleaned_data['inheritance_mode'],
            form.cleaned_data['gene_id'],
            variant_filter=form.cleaned_data['variant_filter'],
            quality_filter=form.cleaned_data['quality_filter']
        )
        variants_by_family = []
        for family in form.cleaned_data['families']:
            variants = variants_grouped[(family.project.project_id, family.family_id)]
            add_extra_info_to_variants_family(get_reference(), family, variants)
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
        raise PermissionDenied

    form = api_forms.DiagnosticSearchForm(family, request.GET)
    if form.is_valid():

        search_spec = form.cleaned_data['search_spec']
        search_spec.family_id = family.family_id

        gene_list = form.cleaned_data['gene_list']
        diagnostic_info_list = []
        for gene_id in gene_list.gene_id_list():
            diagnostic_info = get_gene_diangostic_info(family, gene_id, search_spec.variant_filter)
            add_extra_info_to_variants_family(get_reference(), family, diagnostic_info._variants)
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
        raise PermissionDenied
    gene_id = request.GET.get('gene_id')
    if not get_reference().is_valid_gene_id(gene_id):
        return JSONResponse({
            'is_error': True,
            'error': 'Invalid gene',
        })
    family_gene_data = get_gene_diangostic_info(family, gene_id)
    add_extra_info_to_variants_family(get_reference(), family, family_gene_data._variants)
    return JSONResponse({
        'is_error': False,
        'family_gene_data': family_gene_data.toJSON(),
        'data_summary': family.get_data_summary(),
        'gene': get_reference().get_gene(gene_id),
    })
