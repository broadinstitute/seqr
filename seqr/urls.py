"""seqr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
"""
from seqr.views.react_app import main_app, no_login_main_app
from seqr.views.apis.dataset_api import add_alignment_dataset_handler, add_variants_dataset_handler
from settings import ENABLE_DJANGO_DEBUG_TOOLBAR, MEDIA_ROOT
from django.conf.urls import url, include
from django.contrib import admin
import django.contrib.admindocs.urls
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
    update_individual_handler, \
    edit_individuals_handler, \
    delete_individuals_handler, \
    receive_individuals_table_handler, \
    save_individuals_table_handler

from seqr.views.apis.phenotips_api import \
    proxy_to_phenotips, \
    phenotips_pdf_handler, \
    phenotips_edit_handler, \
    receive_hpo_table_handler, \
    update_individual_hpo_terms

from seqr.views.apis.case_review_api import \
    save_internal_case_review_notes, \
    save_internal_case_review_summary

from seqr.views.apis.saved_variant_api import \
    saved_variant_data, \
    create_saved_variant_handler, \
    update_variant_tags_handler, \
    create_variant_note_handler, \
    update_variant_note_handler, \
    delete_variant_note_handler, \
    update_saved_variant_json

from seqr.views.pages.dashboard_page import \
    dashboard_page_data, \
    export_projects_table_handler

from seqr.views.pages.project_page import \
    project_page_data, \
    export_project_individuals_handler

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

from seqr.views.apis.matchmaker_api import \
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
    get_all_collaborators, \
    get_all_analysts, \
    create_project_collaborator, \
    update_project_collaborator, \
    delete_project_collaborator, \
    set_password, \
    forgot_password, \
    create_staff_user

from seqr.views.apis.staff_api import \
    anvil_export, \
    discovery_sheet, \
    get_projects_for_category, \
    elasticsearch_status, \
    saved_variants, \
    mme_metrics_proxy, \
    mme_submissions, \
    seqr_stats, \
    proxy_to_kibana

from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.apis.auth_api import login_required_error, API_LOGIN_REQUIRED_URL, login_view, logout_view
from seqr.views.apis.igv_api import fetch_igv_track
from seqr.views.apis.analysis_group_api import update_analysis_group_handler, delete_analysis_group_handler
from seqr.views.apis.project_api import create_project_handler, update_project_handler, delete_project_handler
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.apis import external_api
from seqr.views.utils.file_utils import save_temp_file

react_app_pages = [
    'dashboard',
    'project/(?P<project_guid>[^/]+)/.*',
    'gene_info/.*',
    'gene_lists/.*',
    'variant_search/.*',
    'staff/.*',
]

no_login_react_app_pages = [
    r'^$',
    'login',
    'users/forgot_password',
    'users/set_password/(?P<user_token>.+)',
    'matchmaker/matchbox',
    'matchmaker/disclaimer',
]

# NOTE: the actual url will be this with an '/api' prefix
api_endpoints = {
    'individual/(?P<individual_guid>[\w.|-]+)/update': update_individual_handler,
    'individual/(?P<individual_guid>[\w.|-]+)/update_hpo_terms': update_individual_hpo_terms,

    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_notes': save_internal_case_review_notes,
    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_summary': save_internal_case_review_summary,
    'family/(?P<family_guid>[\w.|-]+)/update': update_family_fields_handler,
    'family/(?P<family_guid>[\w.|-]+)/update_assigned_analyst': update_family_assigned_analyst,
    'family/(?P<family_guid>[\w.|-]+)/update_analysed_by': update_family_analysed_by,
    'family/(?P<family_guid>[\w.|-]+)/update_pedigree_image': update_family_pedigree_image,

    'dashboard': dashboard_page_data,
    'dashboard/export_projects_table': export_projects_table_handler,

    'project/(?P<project_guid>[^/]+)/details': project_page_data,
    'project/(?P<project_guid>[^/]+)/export_project_individuals': export_project_individuals_handler,

    'project/create_project': create_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project': update_project_handler,
    'project/(?P<project_guid>[^/]+)/delete_project': delete_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project_categories': update_project_categories_handler,

    'project/(?P<project_guid>[^/]+)/saved_variants/(?P<variant_guid>[^/]+)?': saved_variant_data,

    'project/(?P<project_guid>[^/]+)/edit_families': edit_families_handler,
    'project/(?P<project_guid>[^/]+)/delete_families': delete_families_handler,
    'project/(?P<project_guid>[^/]+)/edit_individuals': edit_individuals_handler,
    'project/(?P<project_guid>[^/]+)/delete_individuals': delete_individuals_handler,
    'project/(?P<project_guid>[^/]+)/upload_families_table': receive_families_table_handler,

    'project/(?P<project_guid>[^/]+)/upload_individuals_table': receive_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/save_individuals_table/(?P<upload_file_id>[^/]+)': save_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/add_dataset/align': add_alignment_dataset_handler,
    'project/(?P<project_guid>[^/]+)/add_dataset/variants': add_variants_dataset_handler,

    'project/(?P<project_guid>[^/]+)/igv_track/(?P<igv_track_path>.+)': fetch_igv_track,
    'project/(?P<project_guid>[^/]+)/individual/(?P<individual_guid>[\w.|-]+)/phenotips_pdf': phenotips_pdf_handler,
    'project/(?P<project_guid>[^/]+)/individual/(?P<individual_guid>[\w.|-]+)/phenotips_edit': phenotips_edit_handler,
    'project/(?P<project_guid>[^/]+)/upload_hpo_terms_table': receive_hpo_table_handler,

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
    'saved_variant/(?P<variant_guid>[^/]+)/update_tags': update_variant_tags_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/create': create_variant_note_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_variant_note_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_variant_note_handler,

    'genes_info': genes_info,
    'gene_info/(?P<gene_id>[^/]+)': gene_info,
    'gene_info/(?P<gene_id>[^/]+)/note/create': create_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_gene_note_handler,

    'locus_lists': locus_lists,
    'locus_lists/(?P<locus_list_guid>[^/]+)': locus_list_info,
    'locus_lists/create': create_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)/update': update_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)/delete': delete_locus_list_handler,
    'project/(?P<project_guid>[^/]+)/add_locus_lists': add_project_locus_lists,
    'project/(?P<project_guid>[^/]+)/delete_locus_lists': delete_project_locus_lists,

    'matchmaker/get_mme_matches/(?P<individual_guid>[\w.|-]+)': get_individual_mme_matches,
    'matchmaker/search_mme_matches/(?P<individual_guid>[\w.|-]+)': search_individual_mme_matches,
    'matchmaker/submission/(?P<individual_guid>[\w.|-]+)/update': update_mme_submission,
    'matchmaker/submission/(?P<individual_guid>[\w.|-]+)/delete': delete_mme_submission,
    'matchmaker/result_status/(?P<matchmaker_result_guid>[\w.|-]+)/update': update_mme_result_status,
    'matchmaker/send_email/(?P<matchmaker_result_guid>[\w.|-]+)': send_mme_contact_email,
    'matchmaker/contact_notes/(?P<institution>[^/]+)/update': update_mme_contact_note,

    'login': login_view,
    'users/forgot_password': forgot_password,
    'users/(?P<username>[^/]+)/set_password': set_password,

    'users/get_all': get_all_collaborators,
    'users/get_all_analysts': get_all_analysts,
    'users/create_staff_user': create_staff_user,
    'project/(?P<project_guid>[^/]+)/collaborators/create': create_project_collaborator,
    'project/(?P<project_guid>[^/]+)/collaborators/(?P<username>[^/]+)/update': update_project_collaborator,
    'project/(?P<project_guid>[^/]+)/collaborators/(?P<username>[^/]+)/delete': delete_project_collaborator,

    'awesomebar': awesomebar_autocomplete_handler,

    'upload_temp_file': save_temp_file,

    'staff/anvil/(?P<project_guid>[^/]+)': anvil_export,
    'staff/discovery_sheet/(?P<project_guid>[^/]+)': discovery_sheet,
    'staff/projects_for_category/(?P<project_category_name>[^/]+)': get_projects_for_category,
    'staff/elasticsearch_status': elasticsearch_status,
    'staff/matchmaker_metrics': mme_metrics_proxy,
    'staff/matchmaker_submissions': mme_submissions,
    'staff/saved_variants/(?P<tag>[^/]+)': saved_variants,
    'staff/seqr_stats': seqr_stats,

    # EXTERNAL APIS: DO NOT CHANGE
    # matchmaker public facing MME URLs
    'matchmaker/v1/match': external_api.mme_match_proxy,
    'matchmaker/v1/metrics': external_api.mme_metrics_proxy,

}

urlpatterns = []

phenotips_urls = '^(?:%s)' % ('|'.join([
    'ssx', 'skin', 'skins', 'get', 'lock', 'preview', 'download', 'export',
    'XWiki', 'cancel', 'resources', 'rollback', 'rest', 'webjars', 'bin', 'jsx'
]))

urlpatterns += [
    url(phenotips_urls, proxy_to_phenotips, name='proxy_to_phenotips'),
]

# core react page templates
urlpatterns += [url("^%(url_endpoint)s$" % locals(), main_app) for url_endpoint in react_app_pages]
urlpatterns += [url("^%(url_endpoint)s$" % locals(), no_login_main_app) for url_endpoint in no_login_react_app_pages]

# api
for url_endpoint, handler_function in api_endpoints.items():
    urlpatterns.append( url("^api/%(url_endpoint)s$" % locals(), handler_function) )

# login/ logout
urlpatterns += [
    url('logout', logout_view),
    url(API_LOGIN_REQUIRED_URL.lstrip('/'), login_required_error)
]

#urlpatterns += [
#   url("^api/v1/%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in api_endpoints.items()]

kibana_urls = '^(?:%s)' % ('|'.join([
    "app", "bundles", "elasticsearch", "plugins", "ui", "api/apm", "api/console", "api/index_management", "api/index_patterns",
    "api/kibana", "api/monitoring", "api/reporting", "api/saved_objects", "api/telemetry", "api/timelion", "api/xpack",
    "es_admin",
]))

urlpatterns += [
    url(kibana_urls, proxy_to_kibana, name='proxy_to_kibana'),
]

urlpatterns += [
    url(r'^hijack/', include('hijack.urls')),
    url(r'^xadmin/doc/', include(django.contrib.admindocs.urls)),
    url(r'^xadmin/', admin.site.urls),
    url(r'^media/(?P<path>.*)$', django.views.static.serve, {
        'document_root': MEDIA_ROOT,
    }),
]

# django debug toolbar
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
