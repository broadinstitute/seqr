import datetime
import csv
import json
import logging
import sys
import traceback
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

from xbrowse_server.phenotips.reporting_utilities import phenotype_entry_metric_for_individual
from xbrowse_server.base.models import ANALYSIS_STATUS_CHOICES
from xbrowse_server.matchmaker.utilities import get_all_clinical_data_for_family
from xbrowse_server.matchmaker.utilities import is_a_valid_patient_structure
from xbrowse_server.matchmaker.utilities import generate_slack_notification_for_incoming_match
from xbrowse_server.matchmaker.utilities import generate_slack_notification_for_seqr_match
from xbrowse_server.matchmaker.utilities import find_latest_family_member_submissions
from xbrowse_server.matchmaker.utilities import convert_matchbox_id_to_seqr_id
from xbrowse_server.matchmaker.utilities import gather_all_annotated_genes_in_seqr
from xbrowse_server.matchmaker.utilities import find_projects_with_families_in_matchbox
from xbrowse_server.matchmaker.utilities import find_families_of_this_project_in_matchbox

import requests
import time
import token
from django.contrib.messages.storage.base import Message
from django.contrib.admin.views.decorators import staff_member_required

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
    request_dict = request.GET or request.POST
    project, family = get_project_and_family_for_user(request.user, request_dict)

    form = api_forms.MendelianVariantSearchForm(request_dict)
    if form.is_valid():

        search_spec = form.cleaned_data['search_spec']
        search_spec.family_id = family.family_id

        try:
            variants = api_utils.calculate_mendelian_variant_search(search_spec, family.xfamily())
        except Exception as e:
            traceback.print_exc()
            return JSONResponse({
                    'is_error': True,
                    'error': str(e.args[0]) if e.args else str(e)
            })

        sys.stderr.write("done fetching %s variants. Adding extra info..\n" % len(variants))
        hashable_search_params = search_spec.toJSON()
        hashable_search_params['family_id'] = family.family_id

        search_hash = cache_utils.save_results_for_spec(project.project_id, hashable_search_params, [v.toJSON() for v in variants])
        add_extra_info_to_variants_family(get_reference(), family, variants)
        sys.stderr.write("done adding extra info to %s variants. Sending response..\n" % len(variants))
        return_type = request_dict.get('return_type', 'json')

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
        raise PermissionDenied

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
        raise PermissionDenied

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
            raise PermissionDenied

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
            raise PermissionDenied

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
        raise PermissionDenied

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
    


@csrf_exempt
@login_required
@log_request('API_project_phenotypes')    
def export_project_individuals_phenotypes(request,project_id):
    """
    Export all HPO terms entered for this project individuals. A direct proxy
    from PhenoTips API
    Args:
        project_id
    Returns:
        A JSON string of HPO terms entered
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    project = get_object_or_404(Project, project_id=project_id)
    result={}
    for individual in project.get_individuals():
        ui_display_name = individual.indiv_id
        ext_id=individual.phenotips_id
        result[ui_display_name] = phenotype_entry_metric_for_individual(project_id, ext_id)['raw']
    return JSONResponse(result)



@csrf_exempt
@login_required
@log_request('API_project_phenotypes')    
def export_project_family_statuses(request,project_id):
    """
    Exports the status of all families in this project
    Args:
        Project ID
    Returns:
        All statuses of families
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    project = get_object_or_404(Project, project_id=project_id)
    
    status_description_map = {}
    for abbrev, details in ANALYSIS_STATUS_CHOICES:
        status_description_map[abbrev] = details[0]
    
    
    result={}
    for family in project.get_families():
        fam_details =family.toJSON()
        result[fam_details['family_id']] = status_description_map.get(family.analysis_status, 'unknown')
    return JSONResponse(result)




@csrf_exempt
@login_required
@log_request('API_project_phenotypes')    
def export_project_variants(request,project_id):
    """
    Export all variants associated to this project
    Args:
        Project id
    Returns:
        A JSON object of variant information
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    
    status_description_map = {}
    for abbrev, details in ANALYSIS_STATUS_CHOICES:
        status_description_map[abbrev] = details[0]

    variants=[]
    project_tags = ProjectTag.objects.filter(project__project_id=project_id)
    for project_tag in project_tags:
        variant_tags = VariantTag.objects.filter(project_tag=project_tag)
        for variant_tag in variant_tags:        
            variant = get_datastore(project.project_id).get_single_variant(
                    project.project_id,
                    variant_tag.family.family_id if variant_tag.family else '',
                    variant_tag.xpos,
                    variant_tag.ref,
                    variant_tag.alt,
            )

            
            variant_json = variant.toJSON() if variant is not None else {'xpos': variant_tag.xpos, 'ref': variant_tag.ref, 'alt': variant_tag.alt}
            
            family_status = ''
            if variant_tag.family:
                family_status = status_description_map.get(variant_tag.family.analysis_status, 'unknown')

            variants.append({"variant":variant_json,
                             "tag":project_tag.tag,
                             "description":project_tag.title,
                             "family":variant_tag.family.toJSON(),
                             "family_status":family_status})
    return JSONResponse(variants)



@login_required
@log_request('matchmaker_individual_add')
def get_submission_candidates(request,project_id,family_id,indiv_id):
    """
    Gathers submission candidate individuals from this family
    Args:
        individual_id: an individual ID
        project_id: project this individual belongs to
    Returns:
        Status code
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:          
        id_map,affected_patient = get_all_clinical_data_for_family(project_id,family_id,indiv_id)
        return JSONResponse({
                             "submission_candidate":affected_patient,
                             "id_map":id_map
                             })

@csrf_exempt
@login_required
@log_request('matchmaker_individual_add')
def add_individual(request):
    """
    Adds given individual to the local database
    Args:
        submission information of a single patient is expected in the POST data
    Returns:
        Submission status information
    """   
    affected_patient =  json.loads(request.POST.get("patient_data","wasn't able to parse patient_data in POST!"))
    seqr_id =  request.POST.get("localId","wasn't able to parse Id (as seqr knows it) in POST!")
    family_id = request.POST.get("familyId","wasn't able to parse family Id in POST!")
    project_id =  request.POST.get("projectId","wasn't able to parse project Id in POST!")
    
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    
    submission = json.dumps({'patient':affected_patient})
    
    validity_check=is_a_valid_patient_structure(affected_patient)
    if not validity_check['status']:
        return JSONResponse({
                        'http_result':{"message":validity_check['reason'] + ", the patient was not submitted to matchmaker"},
                        'status_code':400,
                        })
    
    headers={
           'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
           'Accept': settings.MME_NODE_ACCEPT_HEADER,
           'Content-Type': settings.MME_CONTENT_TYPE_HEADER
         }
    result = requests.post(url=settings.MME_ADD_INDIVIDUAL_URL,
                   headers=headers,
                   data=submission)
    
    #if successfully submitted to MME, persist info
    if result.status_code==200 or result.status_code==409:
        settings.SEQR_ID_TO_MME_ID_MAP.insert({
                                               'submitted_data':{'patient':affected_patient},
                                               'seqr_id':seqr_id,
                                               'family_id':family_id,
                                               'project_id':project_id,
                                               'insertion_date':datetime.datetime.now()
                                               })
    if result.status_code==401:
        return JSONResponse({
                        'http_result':{"message":"sorry, authorization failed, I wasn't able to insert that individual"},
                        'status_code':result.status_code,
                        })
    return JSONResponse({
                        'http_result':result.json(),
                        'status_code':result.status_code,
                        })
        

@login_required
@log_request('matchmaker_family_submissions')
def get_family_submissions(request,project_id,family_id):
    """
    Gets the last 4 submissions for this family
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    else:          
        #find latest submission
        #submission_records=settings.SEQR_ID_TO_MME_ID_MAP.find({'project_id':project_id, 
        #                                     'family_id':family_id}).sort('insertion_date',-1).limit(1)
                                             
        submission_records=settings.SEQR_ID_TO_MME_ID_MAP.find({'project_id':project_id, 
                                             'family_id':family_id}).sort('insertion_date',-1)
                                                                                 
        latest_submissions_from_family = find_latest_family_member_submissions(submission_records)

        family_submissions=[]
        family_members_submitted=[]
        for individual,submission in latest_submissions_from_family.iteritems():  
            family_submissions.append({'submitted_data':submission['submitted_data'],
                                       'seqr_id':submission['seqr_id'],
                                       'family_id':submission['family_id'],
                                       'project_id':submission['project_id'],
                                       'insertion_date':submission['insertion_date'].strftime("%b %d %Y %H:%M:%S"),
                                       })
            family_members_submitted.append(individual)
        #TODO: figure out when more than 1 indi for a family. For now returning a list. Eventually
        #this must be the latest submission for every indiv in a family
        return JSONResponse({
                             "family_submissions":family_submissions,
                             "family_members_submitted":family_members_submitted
                             })


@login_required
@csrf_exempt
@log_request('match_internally_and_externally')
def match_internally_and_externally(request,project_id):
    """
    Looks for matches for the given individual. Expects a single patient (MME spec) in the POST
    data field under key "patient_data"
    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Status code and results
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    
    patient_data = request.POST.get("patient_data","wasn't able to parse POST!")
    headers={
           'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
           'Accept': settings.MME_NODE_ACCEPT_HEADER,
           'Content-Type': settings.MME_CONTENT_TYPE_HEADER
         }
    results={}
    #first look in the local MME database
    internal_result = requests.post(url=settings.MME_LOCAL_MATCH_URL,
                           headers=headers,
                           data=patient_data
                           )
    ids=[]
    for internal_res in internal_result.json().get('results',[]):
        ids.append(internal_res['patient']['id'])
        
    print "internal MME search:",internal_result
    results['local_results']={"result":internal_result.json(), 
                              "status_code":internal_result.status_code
                              }
    #then externally (unless turned off)
    if settings.SEARCH_IN_EXTERNAL_MME_NODES:
        extnl_result = requests.post(url=settings.MME_EXTERNAL_MATCH_URL,
                               headers=headers,
                               data=patient_data
                               )
        results['external_results']={"result":extnl_result.json(),
                                     "status_code":str(extnl_result.status_code)
                         }
        print "external MME search:",extnl_result
        for ext_res in extnl_result.json().get('results',[]):
            ids.append(ext_res['patient']['id'])
       
    result_analysis_state={}
    for id in ids:
        persisted_result_dets = settings.MME_SEARCH_RESULT_ANALYSIS_STATE.find({"result_id":id,"seqr_project_id":project_id})
        if persisted_result_dets.count()>0:
            for persisted_result_det in persisted_result_dets:
                mongo_id=str(persisted_result_det['_id'])
                persisted_result_det['seen_on']=str(timezone.now())
                del persisted_result_det['_id']
                settings.MME_SEARCH_RESULT_ANALYSIS_STATE.update({'_id':mongo_id},{"$set": persisted_result_det}, upsert=False,manipulate=False)
                result_analysis_state[id]={
                                            "result_id":persisted_result_det['result_id'],
                                            "we_contacted_host":persisted_result_det['we_contacted_host'],
                                            "host_contacted_us":persisted_result_det['host_contacted_us'],
                                            "seen_on":persisted_result_det['seen_on'],
                                            "deemed_irrelevant":persisted_result_det['deemed_irrelevant'],
                                            "comments":persisted_result_det['comments'],
                                            "seqr_project_id":project_id,
                                            "flag_for_analysis":persisted_result_det['flag_for_analysis']
                                           }
        else:
            record={
                    "result_id":id,
                    "we_contacted_host":False,
                    "host_contacted_us":False,
                    "seen_on":None,
                    "deemed_irrelevant":False,
                    "comments":"",
                    "seqr_project_id":project_id,
                    "flag_for_analysis":False
                }
            result_analysis_state[id]=record
            settings.MME_SEARCH_RESULT_ANALYSIS_STATE.insert(record,manipulate=False)
    #post to slack
    seqr_id = convert_matchbox_id_to_seqr_id(json.loads(patient_data)['patient']['id'])
    if settings.SLACK_TOKEN is not None:
        generate_slack_notification_for_seqr_match(results,project_id,seqr_id) 
    
    return JSONResponse({
                         "match_results":results,
                         "result_analysis_state":result_analysis_state
                         })
    
    
@login_required
@csrf_exempt
@log_request('get_project_individuals')
def get_project_individuals(request,project_id):
    """
    Get a list of individuals with their family IDs of this project
    Args:
        project_id
    Returns:
        map of individuals and their family
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    indivs=[]
    for indiv in project.get_individuals():
        strct={'guid':indiv.id}
        for k,v in indiv.to_dict().iteritems():
            if k not in ['phenotypes']:
                strct[k] = v 
        indivs.append(strct)
    return JSONResponse({
                         "individuals":indivs
                         })
    
    
    

@csrf_exempt
@log_request('match')
def match(request):
    """    
    -This is a proxy URL for backend MME server as per MME spec.
    -Looks for matches for the given individual ONLY in the local MME DB. 
    -Expects a single patient (as per MME spec) in the POST
    
    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Status code and results (as per MME spec), returns raw results from MME Server
    NOTES: 
    1. login is not required, since AUTH is handled by MME server, hence missing
    decorator @login_required
        
    """
    try:
        mme_headers={
                     'X-Auth-Token':request.META['HTTP_X_AUTH_TOKEN'],
                     'Accept':request.META['HTTP_ACCEPT'],
                     'Content-Type':request.META['CONTENT_TYPE']
                     }
        query_patient_data=''  
        for line in request.readlines():
          query_patient_data = query_patient_data + ' ' + line
        r = requests.post(url=settings.MME_LOCAL_MATCH_URL,
                          data=query_patient_data,
                          headers=mme_headers)
        if r.status_code==200:
            generate_slack_notification_for_incoming_match(r,request,query_patient_data)
        resp = HttpResponse(r.text)
        resp.status_code=r.status_code
        for k,v in r.headers.iteritems():
            if k=='Content-Type':
                resp[k]=v
                if ';' in v:
                    resp[k]=v.split(';')[0]
        return resp
    except:
        raise
        r = HttpResponse('{"message":"message not formatted properly and possibly missing header information", "status":400}',status=400)
        r.status_code=400
        return r
    

@login_required
@staff_member_required
@log_request('matchmaker_get_matchbox_id_details')
def get_matchbox_id_details(request,matchbox_id):
    """
    Gets information of this matchbox_id
    """                           
    submission_records=settings.SEQR_ID_TO_MME_ID_MAP.find({'submitted_data.patient.id':matchbox_id},
                                                           {'_id':0}).sort('insertion_date',-1)
                                    
    records=[]                                         
    for record in submission_records:  
        r={}
        for k,v in record.iteritems():
            if k=="submitted_data":
                genomicFatures=[]
                for g_feature in v['patient']['genomicFeatures']:
                    genomicFatures.append({'gene_id':g_feature['gene']['id'],
                                           'variant_start':g_feature['variant']['start'],
                                           'variant_end': g_feature['variant']['end']})
                r['submitted_genomic_features']=genomicFatures
                
                features=[]
                for feature in v['patient']['features']:
                    id=feature['id']
                    label=''
                    if feature.has_key('label'):
                        label=feature['label']
                    features.append({'id':id,
                                    'label':label}),      
                r['submitted_features']=features
            else:
                r[k]=str(v)
        records.append(r)
    return JSONResponse({
                         'submission_records':records
                         })





@login_required
@staff_member_required
@log_request('matchmaker_get_matchbox_metrics')
def get_matchbox_metrics(request):
    """
    Gets matchbox metrics
    """     
    mme_headers={
           'X-Auth-Token': settings.MME_NODE_ADMIN_TOKEN,
           'Accept': settings.MME_NODE_ACCEPT_HEADER,
           'Content-Type': settings.MME_CONTENT_TYPE_HEADER
         }
    r = requests.get(url=settings.MME_MATCHBOX_METRICS_URL,
                          headers=mme_headers)
    if r.status_code==200:
        matchbox_metrics = r.json()['metrics']
        genes_in_matchbox=matchbox_metrics['geneCounts'].keys()
        seqr__gene_info = gather_all_annotated_genes_in_seqr()
        seqr_metrics={"genes_in_seqr":len(seqr__gene_info),
                      "genes_found_in_matchbox":0}
        unique_genes=[]
        for gene_ids,proj in seqr__gene_info.iteritems():
            if gene_ids[0] in genes_in_matchbox:
                unique_genes.append(gene_ids[0])
        seqr_metrics['genes_found_in_matchbox'] = len(set(unique_genes))
        seqr_metrics["submission_info"]=find_projects_with_families_in_matchbox()
                       
        return JSONResponse({"from_matchbox":r.json(),
                             "from_seqr":seqr_metrics})
    else:
        resp = HttpResponse('{"message":"error contacting matchbox to gain metrics", "status":' + r.status_code + '}',status=r.status_code)
        resp.status_code=r.status_code
        return resp
    
    
@login_required
@log_request('matchmaker_get_matchbox_metrics')
def get_matchbox_metrics_for_project(request,project_id):
    """
    Gets matchbox submission metrics for project (accessible to non-staff)
    """         
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied  
    try:                   
        return JSONResponse({"families":find_families_of_this_project_in_matchbox(project_id)})
    except:
        raise

    
    
@login_required
@csrf_exempt
@log_request('update_match_comment')
def update_match_comment(request,project_id,indiv_id):
    """
    Update a comment made about a match
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied
    
    parse_json_error_mesg="wasn't able to parse POST!" 
    comment = request.POST.get("comment",parse_json_error_mesg)
    if comment == parse_json_error_mesg:
        return HttpResponse('{"message":"' + parse_json_error_mesg +'"}',status=500)
    
    persisted_result_dets = settings.MME_SEARCH_RESULT_ANALYSIS_STATE.find({"result_id":indiv_id,"seqr_project_id":project_id})
    if persisted_result_dets.count()>0:
        for persisted_result_det in persisted_result_dets:
                    mongo_id=persisted_result_det['_id']
                    persisted_result_det['comments']=comment.strip()
                    del persisted_result_det['_id']
                    settings.MME_SEARCH_RESULT_ANALYSIS_STATE.update({'_id':mongo_id},{"$set": persisted_result_det}, upsert=False,manipulate=False)
        resp = HttpResponse('{"message":"OK"}',status=200)
        return resp
    else:
        return HttpResponse('{"message":"error updating database"}',status=500)




    
@login_required
@csrf_exempt
@log_request('match_state_update')
def match_state_update(request,project_id,indiv_id):
    """
    Update a state change made about a match
    """
    project = get_object_or_404(Project, project_id=project_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    state_type = request.POST.get('state_type', None)
    state =  request.POST.get('state',None)
    if state_type is None or state is None:
        return HttpResponse('{"message":"error parsing POST"}',status=500)
        
    persisted_result_det = settings.MME_SEARCH_RESULT_ANALYSIS_STATE.find_one({"result_id":indiv_id,"seqr_project_id":project_id})
    mongo_id=persisted_result_det['_id']
    try:
        if state_type == 'flag_for_analysis':
            persisted_result_det['flag_for_analysis']=False
            if state == "true":
                persisted_result_det['flag_for_analysis']=True
        if state_type == 'deemed_irrelevant':
            persisted_result_det['deemed_irrelevant']=False
            if state == "true":
                persisted_result_det['deemed_irrelevant']=True
        if state_type == 'we_contacted_host':
            persisted_result_det['we_contacted_host']=False   
            if state == "true":
                persisted_result_det['we_contacted_host']=True
        if state_type == 'host_contacted_us':
            persisted_result_det['host_contacted_us']=False
            if state == "true":
                persisted_result_det['host_contacted_us']=True   
        del persisted_result_det['_id']  
        settings.MME_SEARCH_RESULT_ANALYSIS_STATE.update({'_id':mongo_id},{"$set": persisted_result_det}, upsert=False,manipulate=False)
    except:
        return HttpResponse('{"message":"error updating database"}',status=500)
    
    return HttpResponse('{"message":"successfully updated database"}',status=200)
    
    
    


@csrf_exempt
@log_request('get_public_metrics')
def get_public_metrics(request):
    """    
    -This is a proxy URL for backend MME server as per MME spec.
    -Proxies public metrics endpoint
    
    Args:
        None, all data in POST under key "patient_data"
    Returns:
        Metric JSON from matchbox
    NOTES: 
    1. seqr login IS NOT required, since AUTH via toke in POST is handled by MME server, hence no
    decorator @login_required. This is a PUBLIC endpoint
        
    """
    try:
        if not request.META.has_key('HTTP_X_AUTH_TOKEN'):
            r = HttpResponse('{"message":"missing or improperly written HTTP_X_AUTH_TOKEN information", "status":400}',status=400)
            r.status_code=400
            return r
        if not request.META.has_key('HTTP_ACCEPT'):
            r = HttpResponse('{"message":"missing or improperly written HTTP_ACCEPT information", "status":400}',status=400)
            r.status_code=400
            return r
        mme_headers={
                     'X-Auth-Token':request.META['HTTP_X_AUTH_TOKEN'],
                     'Accept':request.META['HTTP_ACCEPT'],
                     'Content-Type':request.META['CONTENT_TYPE']
                     }
        r = requests.get(url=settings.MME_MATCHBOX_PUBLIC_METRICS_URL,headers=mme_headers)
        if r.status_code==200:
            print "processed external metrics request"
        resp = HttpResponse(r.text)
        resp.status_code=r.status_code
        for k,v in r.headers.iteritems():
            if k=='Content-Type':
                resp[k]=v
                if ';' in v:
                    resp[k]=v.split(';')[0]
        return resp
    except:
        raise
        r = HttpResponse('{"message":"message not formatted properly and possibly missing header information", "status":400}',status=400)
        r.status_code=400
        return r