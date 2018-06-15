"""seqr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
"""
from seqr.views.react_app import main_app
from seqr.views.apis.dataset_api import add_dataset_handler
from settings import ENABLE_DJANGO_DEBUG_TOOLBAR
from django.conf.urls import url, include

from seqr.views.apis.family_api import \
    update_family_fields_handler, \
    edit_families_handler, \
    delete_families_handler, \
    update_family_analysed_by

from seqr.views.apis.individual_api import \
    update_individual_handler, \
    edit_individuals_handler, \
    delete_individuals_handler, \
    receive_individuals_table_handler, \
    save_individuals_table_handler

from seqr.views.apis.phenotips_api import \
    proxy_to_phenotips_handler, \
    phenotips_pdf_handler, \
    phenotips_edit_handler

from seqr.views.apis.case_review_api import \
    save_internal_case_review_notes, \
    save_internal_case_review_summary

from seqr.views.apis.saved_variant_api import \
    saved_variant_data, \
    saved_variant_transcripts, \
    update_variant_tags_handler, \
    create_variant_note_handler, \
    update_variant_note_handler, \
    delete_variant_note_handler

from seqr.views.pages.case_review_page import \
    export_case_review_families_handler, \
    export_case_review_individuals_handler

from seqr.views.pages.dashboard_page import \
    dashboard_page_data, \
    export_projects_table_handler

from seqr.views.pages.project_page import \
    project_page_data, \
    export_project_families_handler, \
    export_project_individuals_handler

from seqr.views.apis.gene_api import \
    gene_info, \
    create_gene_note_handler, \
    update_gene_note_handler, \
    delete_gene_note_handler

from seqr.views.pages.staff.staff_pages import \
    staff_dashboard, \
    users_page

from seqr.views.pages.staff.discovery_sheet import discovery_sheet
from seqr.views.pages.staff.elasticsearch_status import elasticsearch_status

from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.apis.auth_api import login_required_error, API_LOGIN_REQUIRED_URL
from seqr.views.apis.igv_api import fetch_igv_track
from seqr.views.apis.project_api import create_project_handler, update_project_handler, delete_project_handler
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.apis.variant_search_api import query_variants_handler

react_app_pages = [
    'dashboard',
    'project/(?P<project_guid>[^/]+)/.*',
    'gene_info/.*'
]

# NOTE: the actual url will be this with an '/api' prefix
api_endpoints = {
    'individual/(?P<individual_guid>[\w.|-]+)/update': update_individual_handler,

    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_notes': save_internal_case_review_notes,
    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_summary': save_internal_case_review_summary,
    'family/(?P<family_guid>[\w.|-]+)/update': update_family_fields_handler,
    'family/(?P<family_guid>[\w.|-]+)/update_analysed_by': update_family_analysed_by,

    'dashboard': dashboard_page_data,
    'dashboard/export_projects_table': export_projects_table_handler,
    'project/(?P<project_guid>[^/]+)/export_case_review_families': export_case_review_families_handler,
    'project/(?P<project_guid>[^/]+)/export_case_review_individuals': export_case_review_individuals_handler,

    'project/(?P<project_guid>[^/]+)/details': project_page_data,
    'project/(?P<project_guid>[^/]+)/export_project_families': export_project_families_handler,
    'project/(?P<project_guid>[^/]+)/export_project_individuals': export_project_individuals_handler,

    'project/create_project': create_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project': update_project_handler,
    'project/(?P<project_guid>[^/]+)/delete_project': delete_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project_categories': update_project_categories_handler,

    'project/(?P<project_guid>[^/]+)/saved_variants': saved_variant_data,
    'project/(?P<project_guid>[^/]+)/query_variants': query_variants_handler,

    'project/(?P<project_guid>[^/]+)/edit_families': edit_families_handler,
    'project/(?P<project_guid>[^/]+)/delete_families': delete_families_handler,
    'project/(?P<project_guid>[^/]+)/edit_individuals': edit_individuals_handler,
    'project/(?P<project_guid>[^/]+)/delete_individuals': delete_individuals_handler,

    'project/(?P<project_guid>[^/]+)/upload_individuals_table': receive_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/save_individuals_table/(?P<upload_file_id>[^/]+)': save_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/add_dataset': add_dataset_handler,

    'project/(?P<project_guid>[^/]+)/igv_track/(?P<igv_track_path>.+)': fetch_igv_track,
    'project/(?P<project_guid>[^/]+)/patient/(?P<patient_id>[^/]+)/phenotips_pdf': phenotips_pdf_handler,
    'project/(?P<project_guid>[^/]+)/patient/(?P<patient_id>[^/]+)/phenotips_edit': phenotips_edit_handler,

    'saved_variant/(?P<variant_guid>[^/]+)/transcripts': saved_variant_transcripts,
    'saved_variant/(?P<variant_guid>[^/]+)/update_tags': update_variant_tags_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/create': create_variant_note_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_variant_note_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_variant_note_handler,

    'gene_info/(?P<gene_id>[^/]+)': gene_info,
    'gene_info/(?P<gene_id>[^/]+)/note/create': create_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_gene_note_handler,

    'awesomebar': awesomebar_autocomplete_handler,

}

urlpatterns = []

# phenotips urls
phenotips_urls = '^(?:%s)' % ('|'.join([
    'ssx', 'skin', 'skins', 'get', 'lock', 'preview', 'download', 'export',
    'XWiki', 'cancel', 'resources', 'rollback', 'rest', 'webjars', 'bin', 'jsx'
]))

urlpatterns += [
    url(phenotips_urls, proxy_to_phenotips_handler, name='proxy_to_phenotips'),
]

# core react page templates
urlpatterns += [url("^%(url_endpoint)s$" % locals(), main_app) for url_endpoint in react_app_pages]

# api
for url_endpoint, handler_function in api_endpoints.items():
    urlpatterns.append( url("^api/%(url_endpoint)s$" % locals(), handler_function) )

# login redirect for ajax calls
urlpatterns += [
    url(API_LOGIN_REQUIRED_URL.lstrip('/'), login_required_error)
]

#urlpatterns += [
#   url("^api/v1/%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in api_endpoints.items()]

# other staff-only endpoints
urlpatterns += [
    url("^staff/?$", staff_dashboard, name="staff_dashboard"),
    url("^staff/users/?", users_page, name="users_page"),
    url("^staff/discovery_sheet/?(?P<project_guid>[^/]+)?/?", discovery_sheet, name="discovery_sheet"),
    url("^staff/elasticsearch_status", elasticsearch_status, name="elasticsearch_status"),
]

urlpatterns += [
    url(r'^hijack/', include('hijack.urls')),
]

# django debug toolbar
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
