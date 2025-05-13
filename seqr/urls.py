"""seqr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
"""
from seqr.views.react_app import main_app, no_login_main_app
from seqr.views.status import status_view
from seqr.views.apis.dataset_api import add_variants_dataset_handler
from settings import ENABLE_DJANGO_DEBUG_TOOLBAR, MEDIA_ROOT, API_LOGIN_REQUIRED_URL, LOGIN_URL, DEBUG, \
    API_POLICY_REQUIRED_URL
from django.conf.urls import include
from django.urls import re_path, path
from django.contrib import admin
from django.views.generic.base import RedirectView
import django.views.static

from seqr.views.apis.family_api import \
    update_family_fields_handler, \
    edit_families_handler, \
    delete_families_handler, \
    update_family_assigned_analyst, \
    update_family_analysed_by, \
    update_family_analysis_groups, \
    receive_families_table_handler, \
    update_family_pedigree_image, \
    create_family_note, \
    update_family_note, \
    delete_family_note, \
    family_page_data, \
    get_family_rna_seq_data, \
    get_family_phenotype_gene_scores, \
    family_variant_tag_summary

from seqr.views.apis.individual_api import \
    get_individual_rna_seq_data, \
    get_hpo_terms, \
    update_individual_hpo_terms, \
    update_individual_handler, \
    edit_individuals_handler, \
    delete_individuals_handler, \
    import_gregor_metadata, \
    receive_individuals_table_handler, \
    save_individuals_table_handler, \
    receive_individuals_metadata_handler, \
    save_individuals_metadata_table_handler

from seqr.views.apis.case_review_api import \
    update_case_review_discussion, \
    update_case_review_status, \
    save_internal_case_review_notes, \
    save_internal_case_review_summary

from seqr.views.apis.saved_variant_api import \
    saved_variant_data, \
    create_saved_variant_handler, \
    update_variant_tags_handler, \
    update_variant_acmg_classification_handler, \
    update_variant_functional_data_handler, \
    create_variant_note_handler, \
    update_variant_note_handler, \
    delete_variant_note_handler, \
    update_variant_main_transcript, \
    update_saved_variant_json

from seqr.views.apis.dashboard_api import dashboard_page_data

from seqr.views.apis.gene_api import \
    gene_info, \
    genes_info, \
    create_gene_note_handler, \
    update_gene_note_handler, \
    delete_gene_note_handler

from seqr.views.apis.locus_list_api import \
    locus_lists, \
    all_locus_list_options, \
    locus_list_info, \
    create_locus_list_handler, \
    update_locus_list_handler, \
    delete_locus_list_handler, \
    add_project_locus_lists, \
    delete_project_locus_lists

from matchmaker.views.matchmaker_api import \
    get_individual_mme_matches, \
    get_mme_nodes, \
    search_local_individual_mme_matches, \
    search_individual_mme_matches, \
    finalize_mme_search, \
    update_mme_submission, \
    delete_mme_submission, \
    update_mme_result_status, \
    update_mme_contact_note, \
    update_mme_project_contact, \
    send_mme_contact_email

from seqr.views.apis.variant_search_api import \
    query_variants_handler, \
    query_single_variant_handler, \
    search_context_handler, \
    export_variants_handler, \
    get_saved_search_handler, \
    get_variant_gene_breakdown, \
    create_saved_search_handler,\
    update_saved_search_handler, \
    variant_lookup_handler, \
    vlm_lookup_handler, \
    search_results_redirect, \
    delete_saved_search_handler

from seqr.views.apis.users_api import \
    get_all_collaborator_options, \
    get_all_user_group_options, \
    get_project_collaborator_options, \
    create_project_collaborator, \
    update_project_collaborator, \
    delete_project_collaborator, \
    update_project_collaborator_group, \
    delete_project_collaborator_group, \
    set_password, \
    update_policies, \
    update_user, \
    forgot_password

from seqr.views.apis.data_manager_api import elasticsearch_status, delete_index, \
    update_rna_seq, load_rna_seq_sample_data, proxy_to_kibana, load_phenotype_prioritization_data, \
    validate_callset, get_loaded_projects, load_data, loading_vcfs, trigger_dag, proxy_to_luigi
from seqr.views.apis.report_api import \
    anvil_export, \
    family_metadata, \
    variant_metadata, \
    gregor_export, \
    seqr_stats
from seqr.views.apis.summary_data_api import success_story, saved_variants_page, mme_details, hpo_summary_data, \
    bulk_update_family_external_analysis, individual_metadata, send_vlm_email
from seqr.views.apis.superuser_api import get_all_users

from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.apis.auth_api import login_required_error, login_view, logout_view, policies_required_error
from seqr.views.apis.igv_api import fetch_igv_track, receive_igv_table_handler, update_individual_igv_sample, \
    receive_bulk_igv_table_handler
from seqr.views.apis.analysis_group_api import update_analysis_group_handler, delete_analysis_group_handler, \
    update_dynamic_analysis_group_handler, delete_dynamic_analysis_group_handler
from seqr.views.apis.project_api import create_project_handler, update_project_handler, delete_project_handler, \
    project_page_data, project_families, project_overview, project_mme_submisssions, project_individuals, \
    project_analysis_groups, update_project_workspace, project_family_notes, project_collaborators, project_locus_lists, \
    project_samples, project_notifications, mark_read_project_notifications, subscribe_project_notifications
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace, \
    grant_workspace_access, validate_anvil_vcf, add_workspace_data, get_anvil_vcf_list, get_anvil_igv_options
from matchmaker.views import external_api
from seqr.views.utils.file_utils import save_temp_file
from seqr.views.apis.feature_updates_api import get_feature_updates

react_app_pages = [
    'dashboard',
    'project/(?P<project_guid>[^/]+)/.*',
    'create_project_from_workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)',
    'gene_info/.*',
    'gene_lists/.*',
    'variant_search/.*',
    'report/.*',
    'data_management/.*',
    'summary_data/.*',
    'accept_policies',
]

no_login_react_app_pages = [
    r'^$',
    'login/',
    'login/error/.*',
    'login/forgot_password',
    'login/set_password/(?P<user_token>.+)',
    'matchmaker/matchbox',
    'matchmaker/disclaimer',
    'privacy_policy',
    'terms_of_service',
    'faq/.*',
    'feature_updates',
]

# NOTE: the actual url will be this with an '/api' prefix
api_endpoints = {
    'individual/(?P<individual_guid>[\w.|-]+)/update': update_individual_handler,
    'individual/(?P<individual_guid>[\w.|-]+)/update_hpo_terms': update_individual_hpo_terms,
    'individual/(?P<individual_guid>[\w.|-]+)/update_igv_sample': update_individual_igv_sample,
    'individual/(?P<individual_guid>[\w.|-]+)/update_case_review_discussion': update_case_review_discussion,
    'individual/(?P<individual_guid>[\w.|-]+)/update_case_review_status': update_case_review_status,
    'individual/(?P<individual_guid>[\w.|-]+)/rna_seq_data': get_individual_rna_seq_data,

    'family/(?P<family_guid>[\w.|-]+)/details': family_page_data,
    'family/(?P<family_guid>[\w.|-]+)/variant_tag_summary': family_variant_tag_summary,
    'family/(?P<family_guid>[\w.|-]+)/update_case_review_notes': save_internal_case_review_notes,
    'family/(?P<family_guid>[\w.|-]+)/update_case_review_summary': save_internal_case_review_summary,
    'family/(?P<family_guid>[\w.|-]+)/update': update_family_fields_handler,
    'family/(?P<family_guid>[\w.|-]+)/update_assigned_analyst': update_family_assigned_analyst,
    'family/(?P<family_guid>[\w.|-]+)/update_analysed_by': update_family_analysed_by,
    'family/(?P<family_guid>[\w.|-]+)/update_analysis_groups': update_family_analysis_groups,
    'family/(?P<family_guid>[\w.|-]+)/update_pedigree_image': update_family_pedigree_image,
    'family/(?P<family_guid>[\w.|-]+)/note/create': create_family_note,
    'family/(?P<family_guid>[\w.|-]+)/note/(?P<note_guid>[\w.|-]+)/update': update_family_note,
    'family/(?P<family_guid>[\w.|-]+)/note/(?P<note_guid>[\w.|-]+)/delete': delete_family_note,
    'family/(?P<family_guid>[\w.|-]+)/rna_seq_data/(?P<gene_id>[\w.|-]+)': get_family_rna_seq_data,
    'family/(?P<family_guid>[\w.|-]+)/phenotype_gene_scores': get_family_phenotype_gene_scores,  # noqa: W605

    'dashboard': dashboard_page_data,

    'project/(?P<project_guid>[^/]+)/details': project_page_data,
    'project/(?P<project_guid>[^/]+)/get_families': project_families,
    'project/(?P<project_guid>[^/]+)/get_individuals': project_individuals,
    'project/(?P<project_guid>[^/]+)/get_samples': project_samples,
    'project/(?P<project_guid>[^/]+)/get_family_notes': project_family_notes,
    'project/(?P<project_guid>[^/]+)/get_mme_submissions': project_mme_submisssions,
    'project/(?P<project_guid>[^/]+)/get_analysis_groups': project_analysis_groups,
    'project/(?P<project_guid>[^/]+)/get_locus_lists': project_locus_lists,
    'project/(?P<project_guid>[^/]+)/get_overview': project_overview,
    'project/(?P<project_guid>[^/]+)/get_collaborators': project_collaborators,
    'project/(?P<project_guid>[^/]+)/notifications/mark_read': mark_read_project_notifications,
    'project/(?P<project_guid>[^/]+)/notifications/subscribe': subscribe_project_notifications,
    'project/(?P<project_guid>[^/]+)/notifications/(?P<read_status>(un)?read)': project_notifications,

    'project/create_project': create_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project': update_project_handler,
    'project/(?P<project_guid>[^/]+)/delete_project': delete_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project_categories': update_project_categories_handler,
    'project/(?P<project_guid>[^/]+)/update_workspace': update_project_workspace,

    'project/(?P<project_guid>[^/]+)/saved_variants/(?P<variant_guids>[^/]+)?': saved_variant_data,

    'project/(?P<project_guid>[^/]+)/edit_families': edit_families_handler,
    'project/(?P<project_guid>[^/]+)/delete_families': delete_families_handler,
    'project/(?P<project_guid>[^/]+)/edit_individuals': edit_individuals_handler,
    'project/(?P<project_guid>[^/]+)/delete_individuals': delete_individuals_handler,
    'project/(?P<project_guid>[^/]+)/import_gregor_metadata': import_gregor_metadata,
    'project/(?P<project_guid>[^/]+)/upload_families_table': receive_families_table_handler,

    'project/(?P<project_guid>[^/]+)/upload_individuals_table': receive_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/save_individuals_table/(?P<upload_file_id>[^/]+)': save_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/upload_igv_dataset': receive_igv_table_handler,
    'project/(?P<project_guid>[^/]+)/add_dataset/variants': add_variants_dataset_handler,

    'project/(?P<project_guid>[^/]+)/igv_track/(?P<igv_track_path>.+)': fetch_igv_track,
    'project/(?P<project_guid>[^/]+)/upload_individuals_metadata_table': receive_individuals_metadata_handler,
    'project/(?P<project_guid>[^/]+)/save_individuals_metadata_table/(?P<upload_file_id>[^/]+)': save_individuals_metadata_table_handler,

    'project/(?P<project_guid>[^/]+)/analysis_groups/create': update_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/analysis_groups/(?P<analysis_group_guid>[^/]+)/update': update_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/analysis_groups/(?P<analysis_group_guid>[^/]+)/delete': delete_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/dynamic_analysis_groups/create': update_dynamic_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/dynamic_analysis_groups/(?P<analysis_group_guid>[^/]+)/update': update_dynamic_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/dynamic_analysis_groups/(?P<analysis_group_guid>[^/]+)/delete': delete_dynamic_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/update_saved_variant_json': update_saved_variant_json,
    'project/(?P<project_guid>[^/]+)/add_workspace_data': add_workspace_data,

    'search/variant/(?P<variant_id>[^/]+)': query_single_variant_handler,
    'search/(?P<search_hash>[^/]+)': query_variants_handler,
    'search/(?P<search_hash>[^/]+)/download': export_variants_handler,
    'search/(?P<search_hash>[^/]+)/gene_breakdown': get_variant_gene_breakdown,
    'variant_lookup': variant_lookup_handler,
    'vlm_lookup': vlm_lookup_handler,
    'search_context': search_context_handler,
    'saved_search/all': get_saved_search_handler,
    'saved_search/create': create_saved_search_handler,
    'saved_search/(?P<saved_search_guid>[^/]+)/update': update_saved_search_handler,
    'saved_search/(?P<saved_search_guid>[^/]+)/delete': delete_saved_search_handler,

    'saved_variant/create': create_saved_variant_handler,
    'saved_variant/(?P<variant_guids>[^/]+)/update_tags': update_variant_tags_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/update_acmg_classification': update_variant_acmg_classification_handler,
    'saved_variant/(?P<variant_guids>[^/]+)/update_functional_data': update_variant_functional_data_handler,
    'saved_variant/(?P<variant_guids>[^/]+)/note/create': create_variant_note_handler,
    'saved_variant/(?P<variant_guids>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_variant_note_handler,
    'saved_variant/(?P<variant_guids>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_variant_note_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/update_transcript/(?P<transcript_id>[^/]+)': update_variant_main_transcript,

    'genes_info': genes_info,
    'gene_info/(?P<gene_id>[^/]+)': gene_info,
    'gene_info/(?P<gene_id>[^/]+)/note/create': create_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_gene_note_handler,

    'hpo_terms/(?P<hpo_parent_id>[^/]+)': get_hpo_terms,

    'locus_lists/(?P<locus_list_guid>[^/]+)/update': update_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)/delete': delete_locus_list_handler,
    'locus_lists/create': create_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)': locus_list_info,
    'locus_lists': locus_lists,
    'all_locus_list_options': all_locus_list_options,
    'project/(?P<project_guid>[^/]+)/add_locus_lists': add_project_locus_lists,
    'project/(?P<project_guid>[^/]+)/delete_locus_lists': delete_project_locus_lists,

    'matchmaker/get_mme_matches/(?P<submission_guid>[\w.|-]+)': get_individual_mme_matches,
    'matchmaker/get_mme_nodes': get_mme_nodes,
    'matchmaker/search_local_mme_matches/(?P<submission_guid>[^/]+)': search_local_individual_mme_matches,
    'matchmaker/search_mme_matches/(?P<submission_guid>[^/]+)/(?P<node>[^/]+)': search_individual_mme_matches,
    'matchmaker/finalize_mme_search/(?P<submission_guid>[^/]+)': finalize_mme_search,
    'matchmaker/submission/create': update_mme_submission,
    'matchmaker/submission/(?P<submission_guid>[\w.|-]+)/update': update_mme_submission,
    'matchmaker/submission/(?P<submission_guid>[\w.|-]+)/delete': delete_mme_submission,
    'matchmaker/result_status/(?P<matchmaker_result_guid>[\w.|-]+)/update': update_mme_result_status,
    'matchmaker/send_email/(?P<matchmaker_result_guid>[\w.|-]+)': send_mme_contact_email,
    'matchmaker/contact_notes/(?P<institution>[^/]+)/update': update_mme_contact_note,
    'matchmaker/update_project_contact/(?P<project_guid>[^/]+)': update_mme_project_contact,

    'login': login_view,
    'users/forgot_password': forgot_password,
    'users/(?P<username>[^/]+)/set_password': set_password,
    'users/update': update_user,
    'users/update_policies': update_policies,

    'users/get_options': get_all_collaborator_options,
    'users/get_group_options': get_all_user_group_options,
    'users/get_options/(?P<project_guid>[^/]+)': get_project_collaborator_options,
    'project/(?P<project_guid>[^/]+)/collaborators/create': create_project_collaborator,
    'project/(?P<project_guid>[^/]+)/collaborators/(?P<username>[^/]+)/update': update_project_collaborator,
    'project/(?P<project_guid>[^/]+)/collaborators/(?P<username>[^/]+)/delete': delete_project_collaborator,
    'project/(?P<project_guid>[^/]+)/collaboratorGroups/(?P<name>[^/]+)/update': update_project_collaborator_group,
    'project/(?P<project_guid>[^/]+)/collaboratorGroups/(?P<name>[^/]+)/delete': delete_project_collaborator_group,

    'awesomebar': awesomebar_autocomplete_handler,

    'upload_temp_file': save_temp_file,

    'report/anvil/(?P<project_guid>[^/]+)': anvil_export,
    'report/family_metadata/(?P<project_guid>[^/]+)': family_metadata,
    'report/variant_metadata/(?P<project_guid>[^/]+)': variant_metadata,
    'report/gregor': gregor_export,
    'report/seqr_stats': seqr_stats,

    'data_management/elasticsearch_status': elasticsearch_status,
    'data_management/delete_index': delete_index,
    'data_management/get_all_users': get_all_users,
    'data_management/update_rna_seq': update_rna_seq,
    'data_management/load_rna_seq_sample/(?P<sample_guid>[^/]+)': load_rna_seq_sample_data,
    'data_management/load_phenotype_prioritization_data': load_phenotype_prioritization_data,
    'data_management/loading_vcfs': loading_vcfs,
    'data_management/validate_callset': validate_callset,
    'data_management/loaded_projects/(?P<genome_version>[^/]+)/(?P<sample_type>[^/]+)/(?P<dataset_type>[^/]+)': get_loaded_projects,
    'data_management/load_data': load_data,
    'data_management/add_igv': receive_bulk_igv_table_handler,
    'data_management/trigger_dag/(?P<dag_id>[^/]+)': trigger_dag,

    'summary_data/saved_variants/(?P<tag>[^/]+)': saved_variants_page,
    'summary_data/hpo/(?P<hpo_id>[^/]+)': hpo_summary_data,
    'summary_data/success_story/(?P<success_story_types>[^/]+)': success_story,
    'summary_data/matchmaker': mme_details,
    'summary_data/update_external_analysis': bulk_update_family_external_analysis,
    'summary_data/individual_metadata/(?P<project_guid>[^/]+)': individual_metadata,
    'summary_data/send_vlm_email': send_vlm_email,

    'create_project_from_workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)/grant_access': grant_workspace_access,
    'create_project_from_workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)/validate_vcf': validate_anvil_vcf,
    'create_project_from_workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)/submit': create_project_from_workspace,
    'create_project_from_workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)/get_vcf_list': get_anvil_vcf_list,
    'anvil_workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)/get_igv_options': get_anvil_igv_options,

    'feature_updates': get_feature_updates,

    # EXTERNAL APIS: DO NOT CHANGE
    # matchmaker public facing MME URLs
    'matchmaker/v1/match': external_api.mme_match_proxy,
    'matchmaker/v1/metrics': external_api.mme_metrics_proxy,
}

urlpatterns = [
    path('status', status_view),
    re_path('^(?:luigi_ui)', proxy_to_luigi),
    re_path('^report/custom_search/.*$', search_results_redirect)
]

# anvil workspace
anvil_workspace_url = 'workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)'
urlpatterns += [re_path(r"^%(anvil_workspace_url)s$" % locals(), anvil_workspace_page)]

# core react page templates
urlpatterns += [re_path(r"^%(url_endpoint)s$" % locals(), main_app) for url_endpoint in react_app_pages]
urlpatterns += [re_path(r"^%(url_endpoint)s$" % locals(), no_login_main_app) for url_endpoint in no_login_react_app_pages]

# api
for url_endpoint, handler_function in api_endpoints.items():
    urlpatterns.append(re_path(r"^api/%(url_endpoint)s$" % locals(), handler_function))


# login/ logout
urlpatterns += [
    path('logout', logout_view),
    path(API_LOGIN_REQUIRED_URL.lstrip('/'), login_required_error),
    path(API_POLICY_REQUIRED_URL.lstrip('/'), policies_required_error),
]

handler401 = 'seqr.views.apis.auth_api.app_login_required_error'

kibana_urls = '^(?:{})'.format('|'.join([
    'app', '\d+/built_assets', '\d+/bundles', 'bundles', 'elasticsearch', 'es_admin', 'node_modules/@kbn', 'internal',
    'plugins', 'translations', 'ui', 'api/apm', 'api/console', 'api/core', 'api/index_management', 'api/index_patterns',
    'api/kibana', 'api/licensing', 'api/monitoring', 'api/reporting', 'api/saved_objects', 'api/telemetry',
    'api/timelion', 'api/ui_metric', 'api/xpack', 'bootstrap',
]))

urlpatterns += [
    re_path(kibana_urls, proxy_to_kibana, name='proxy_to_kibana'),
]

urlpatterns += [
    re_path(r'^admin/login/$', RedirectView.as_view(url=LOGIN_URL, permanent=True, query_string=True)),
    re_path(r'^admin/', admin.site.urls),
]

# The /media urlpattern is not needed if we are storing static media in a GCS bucket,
# so this logic disables it in that case. If we want to serve media from a local filepath
# instead, set MEDIA_ROOT in settings.py to that local path, and then this urlpattern will be enabled.
if MEDIA_ROOT:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', django.views.static.serve, {
            'document_root': MEDIA_ROOT,
        }),
    ]

urlpatterns += [
    path('', include('social_django.urls')),
]

if DEBUG:
    urlpatterns += [
        re_path(r'^hijack/', include('hijack.urls')),
    ]

# django debug toolbar
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns = [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
