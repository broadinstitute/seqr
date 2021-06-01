"""seqr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
"""
from seqr.views.react_app import main_app, no_login_main_app
from seqr.views.status import status_view
from seqr.views.apis.dataset_api import add_variants_dataset_handler
from settings import ENABLE_DJANGO_DEBUG_TOOLBAR, MEDIA_ROOT, API_LOGIN_REQUIRED_URL, LOGIN_URL, DEBUG, \
    API_POLICY_REQUIRED_URL
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic.base import RedirectView
import django.views.static

from seqr.views.apis.family_api import \
    update_family_fields_handler, \
    edit_families_handler, \
    delete_families_handler, \
    update_family_assigned_analyst, \
    update_family_analysed_by, \
    receive_families_table_handler, \
    update_family_pedigree_image

from seqr.views.apis.individual_api import \
    get_hpo_terms, \
    update_individual_hpo_terms, \
    update_individual_handler, \
    edit_individuals_handler, \
    delete_individuals_handler, \
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
    locus_list_info, \
    create_locus_list_handler, \
    update_locus_list_handler, \
    delete_locus_list_handler, \
    add_project_locus_lists, \
    delete_project_locus_lists

from matchmaker.views.matchmaker_api import \
    get_individual_mme_matches, \
    search_individual_mme_matches, \
    update_mme_submission, \
    delete_mme_submission, \
    update_mme_result_status, \
    update_mme_contact_note, \
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
    delete_saved_search_handler

from seqr.views.apis.users_api import \
    get_all_collaborator_options, \
    get_all_analyst_options, \
    create_project_collaborator, \
    update_project_collaborator, \
    delete_project_collaborator, \
    set_password, \
    update_policies, \
    update_user, \
    forgot_password

from seqr.views.apis.data_manager_api import elasticsearch_status, upload_qc_pipeline_output, proxy_to_kibana
from seqr.views.apis.report_api import \
    anvil_export, \
    discovery_sheet, \
    get_cmg_projects, \
    sample_metadata_export, \
    seqr_stats
from seqr.views.apis.summary_data_api import success_story, saved_variants_page, mme_details
from seqr.views.apis.superuser_api import get_all_users

from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.apis.auth_api import login_required_error, login_view, logout_view, policies_required_error
from seqr.views.apis.igv_api import fetch_igv_track, receive_igv_table_handler, update_individual_igv_sample, \
    igv_genomes_proxy
from seqr.views.apis.analysis_group_api import update_analysis_group_handler, delete_analysis_group_handler
from seqr.views.apis.project_api import create_project_handler, update_project_handler, delete_project_handler, \
    project_page_data
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace
from matchmaker.views import external_api
from seqr.views.utils.file_utils import save_temp_file

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
    'login',
    'users/forgot_password',
    'users/set_password/(?P<user_token>.+)',
    'matchmaker/matchbox',
    'matchmaker/disclaimer',
    'privacy_policy',
    'terms_of_service',

]

# NOTE: the actual url will be this with an '/api' prefix
api_endpoints = {
    'individual/(?P<individual_guid>[\w.|-]+)/update': update_individual_handler,
    'individual/(?P<individual_guid>[\w.|-]+)/update_hpo_terms': update_individual_hpo_terms,
    'individual/(?P<individual_guid>[\w.|-]+)/update_igv_sample': update_individual_igv_sample,
    'individual/(?P<individual_guid>[\w.|-]+)/update_case_review_discussion': update_case_review_discussion,
    'individual/(?P<individual_guid>[\w.|-]+)/update_case_review_status': update_case_review_status,

    'family/(?P<family_guid>[\w.|-]+)/update_case_review_notes': save_internal_case_review_notes,
    'family/(?P<family_guid>[\w.|-]+)/update_case_review_summary': save_internal_case_review_summary,
    'family/(?P<family_guid>[\w.|-]+)/update': update_family_fields_handler,
    'family/(?P<family_guid>[\w.|-]+)/update_assigned_analyst': update_family_assigned_analyst,
    'family/(?P<family_guid>[\w.|-]+)/update_analysed_by': update_family_analysed_by,
    'family/(?P<family_guid>[\w.|-]+)/update_pedigree_image': update_family_pedigree_image,

    'dashboard': dashboard_page_data,

    'project/(?P<project_guid>[^/]+)/details': project_page_data,

    'project/create_project': create_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project': update_project_handler,
    'project/(?P<project_guid>[^/]+)/delete_project': delete_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project_categories': update_project_categories_handler,

    'project/(?P<project_guid>[^/]+)/saved_variants/(?P<variant_guids>[^/]+)?': saved_variant_data,

    'project/(?P<project_guid>[^/]+)/edit_families': edit_families_handler,
    'project/(?P<project_guid>[^/]+)/delete_families': delete_families_handler,
    'project/(?P<project_guid>[^/]+)/edit_individuals': edit_individuals_handler,
    'project/(?P<project_guid>[^/]+)/delete_individuals': delete_individuals_handler,
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
    'project/(?P<project_guid>[^/]+)/update_saved_variant_json': update_saved_variant_json,

    'search/variant/(?P<variant_id>[^/]+)': query_single_variant_handler,
    'search/(?P<search_hash>[^/]+)': query_variants_handler,
    'search/(?P<search_hash>[^/]+)/download': export_variants_handler,
    'search/(?P<search_hash>[^/]+)/gene_breakdown': get_variant_gene_breakdown,
    'search_context': search_context_handler,
    'saved_search/all': get_saved_search_handler,
    'saved_search/create': create_saved_search_handler,
    'saved_search/(?P<saved_search_guid>[^/]+)/update': update_saved_search_handler,
    'saved_search/(?P<saved_search_guid>[^/]+)/delete': delete_saved_search_handler,

    'saved_variant/create': create_saved_variant_handler,
    'saved_variant/(?P<variant_guids>[^/]+)/update_tags': update_variant_tags_handler,
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
    'igv_genomes/(?P<file_path>.*)': igv_genomes_proxy,

    'locus_lists/(?P<locus_list_guid>[^/]+)/update': update_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)/delete': delete_locus_list_handler,
    'locus_lists/create': create_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)': locus_list_info,
    'locus_lists': locus_lists,
    'project/(?P<project_guid>[^/]+)/add_locus_lists': add_project_locus_lists,
    'project/(?P<project_guid>[^/]+)/delete_locus_lists': delete_project_locus_lists,

    'matchmaker/get_mme_matches/(?P<submission_guid>[\w.|-]+)': get_individual_mme_matches,
    'matchmaker/search_mme_matches/(?P<submission_guid>[\w.|-]+)': search_individual_mme_matches,
    'matchmaker/submission/create': update_mme_submission,
    'matchmaker/submission/(?P<submission_guid>[\w.|-]+)/update': update_mme_submission,
    'matchmaker/submission/(?P<submission_guid>[\w.|-]+)/delete': delete_mme_submission,
    'matchmaker/result_status/(?P<matchmaker_result_guid>[\w.|-]+)/update': update_mme_result_status,
    'matchmaker/send_email/(?P<matchmaker_result_guid>[\w.|-]+)': send_mme_contact_email,
    'matchmaker/contact_notes/(?P<institution>[^/]+)/update': update_mme_contact_note,

    'login': login_view,
    'users/forgot_password': forgot_password,
    'users/(?P<username>[^/]+)/set_password': set_password,
    'users/update': update_user,
    'users/update_policies': update_policies,

    'users/get_options': get_all_collaborator_options,
    'users/get_analyst_options': get_all_analyst_options,
    'project/(?P<project_guid>[^/]+)/collaborators/create': create_project_collaborator,
    'project/(?P<project_guid>[^/]+)/collaborators/(?P<username>[^/]+)/update': update_project_collaborator,
    'project/(?P<project_guid>[^/]+)/collaborators/(?P<username>[^/]+)/delete': delete_project_collaborator,

    'awesomebar': awesomebar_autocomplete_handler,

    'upload_temp_file': save_temp_file,

    'report/anvil/(?P<project_guid>[^/]+)': anvil_export,
    'report/sample_metadata/(?P<project_guid>[^/]+)': sample_metadata_export,
    'report/discovery_sheet/(?P<project_guid>[^/]+)': discovery_sheet,
    'report/get_cmg_projects': get_cmg_projects,
    'report/seqr_stats': seqr_stats,

    'data_management/elasticsearch_status': elasticsearch_status,
    'data_management/upload_qc_pipeline_output': upload_qc_pipeline_output,
    'data_management/get_all_users': get_all_users,

    'summary_data/saved_variants/(?P<tag>[^/]+)': saved_variants_page,
    'summary_data/success_story/(?P<success_story_types>[^/]+)': success_story,
    'summary_data/matchmaker': mme_details,

    # EXTERNAL APIS: DO NOT CHANGE
    # matchmaker public facing MME URLs
    'matchmaker/v1/match': external_api.mme_match_proxy,
    'matchmaker/v1/metrics': external_api.mme_metrics_proxy,

    'create_project_from_workspace/submit/(?P<namespace>[^/]+)/(?P<name>[^/]+)': create_project_from_workspace,
}

urlpatterns = [url('^status', status_view)]

# anvil workspace
anvil_workspace_url = 'workspace/(?P<namespace>[^/]+)/(?P<name>[^/]+)'
urlpatterns += [url("^%(anvil_workspace_url)s$" % locals(), anvil_workspace_page)]

# core react page templates
urlpatterns += [url("^%(url_endpoint)s$" % locals(), main_app) for url_endpoint in react_app_pages]
urlpatterns += [url("^%(url_endpoint)s$" % locals(), no_login_main_app) for url_endpoint in no_login_react_app_pages]

# api
for url_endpoint, handler_function in api_endpoints.items():
    urlpatterns.append( url("^api/%(url_endpoint)s$" % locals(), handler_function) )

# login/ logout
urlpatterns += [
    url('^logout$', logout_view),
    url(API_LOGIN_REQUIRED_URL.lstrip('/'), login_required_error),
    url(API_POLICY_REQUIRED_URL.lstrip('/'), policies_required_error),
]

kibana_urls = '^(?:{})'.format('|'.join([
    'app', '\d+/built_assets', '\d+/bundles', 'bundles', 'elasticsearch', 'es_admin', 'node_modules/@kbn', 'internal',
    'plugins', 'translations', 'ui', 'api/apm', 'api/console', 'api/core', 'api/index_management', 'api/index_patterns',
    'api/kibana', 'api/licensing', 'api/monitoring', 'api/reporting', 'api/saved_objects', 'api/telemetry',
    'api/timelion', 'api/ui_metric', 'api/xpack',
]))

urlpatterns += [
    url(kibana_urls, proxy_to_kibana, name='proxy_to_kibana'),
]

urlpatterns += [
    url(r'^admin/login/$', RedirectView.as_view(url=LOGIN_URL, permanent=True, query_string=True)),
    url(r'^admin/', admin.site.urls),
    url(r'^media/(?P<path>.*)$', django.views.static.serve, {
        'document_root': MEDIA_ROOT,
    }),
]

urlpatterns += [
    url('', include('social_django.urls')),
]

if DEBUG:
    urlpatterns += [
        url(r'^hijack/', include('hijack.urls')),
    ]

# django debug toolbar
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
