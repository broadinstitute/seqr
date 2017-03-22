"""seqr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
"""

from django.conf.urls import url, include

from seqr.views.apis.phenotips_api import \
    proxy_to_phenotips, \
    phenotips_edit_patient, \
    phenotips_view_patient_pdf

from seqr.views.pages.staff.case_review_page import \
    case_review_page, \
    case_review_page_data, \
    save_case_review_status, \
    save_internal_case_review_notes, \
    save_internal_case_review_summary, export_case_review_families, export_case_review_individuals

from seqr.views.pages.dashboard_page import \
    dashboard_page, \
    dashboard_page_data, export_projects_table
from seqr.views.pages.staff.users_page import users_template

from seqr.views.pages.variant_search_page import \
    variant_search_page, \
    variant_search_page_data

from seqr.views.apis.awesomebar_api import awesomebar_autocomplete
from seqr.views.apis.auth_api import login_required_error, API_LOGIN_REQUIRED_URL
from seqr.views.apis.project_api import create_project, update_project, delete_project
from seqr.views.apis.project_categories_api import update_project_categories
from seqr.views.apis.variant_search_api import query_variants


page_endpoints = {
    'dashboard': {
        'html': dashboard_page,
        'initial_json': dashboard_page_data,
    },
    'project/(?P<project_guid>[^/]+)/case_review': {
        'html': case_review_page,
        'initial_json': case_review_page_data,
    },
    'project/(?P<project_guid>[^/]+)/variant_search': {
        'html': variant_search_page,
        'initial_json': variant_search_page_data,
    },
}

api_endpoints = {
    'individuals/save_case_review_status': save_case_review_status,
    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_notes': save_internal_case_review_notes,
    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_summary': save_internal_case_review_summary,

    'dashboard/export_projects_table': export_projects_table,
    'project/(?P<project_guid>[^/]+)/export_case_review_families': export_case_review_families,
    'project/(?P<project_guid>[^/]+)/export_case_review_individuals': export_case_review_individuals,
    #'project/(?P<project_guid>[^/]+)/export_project_table': export_project_table,

    'project/create_project': create_project,
    'project/(?P<project_guid>[^/]+)/update_project': update_project,
    'project/(?P<project_guid>[^/]+)/delete_project': delete_project,
    'project/(?P<project_guid>[^/]+)/update_project_categories': update_project_categories,

    'project/(?P<project_guid>[^/]+)/query_variants': query_variants,

    'awesomebar': awesomebar_autocomplete,
}


# page templates
urlpatterns = []

for url_endpoint, handler_functions in page_endpoints.items():
    urlpatterns.append( url("^%(url_endpoint)s$" % locals() , handler_functions['html']) )
    urlpatterns.append( url("^api/%(url_endpoint)s$" % locals() , handler_functions['initial_json']) )

# api
for url_endpoint, handler_function in api_endpoints.items():
    urlpatterns.append( url("^api/%(url_endpoint)s$" % locals(), handler_function) )

# login redirect for ajax calls
urlpatterns += [
    url(API_LOGIN_REQUIRED_URL.lstrip('/'), login_required_error)
]

# phenotips urls
phenotips_urls = '^(?:%s)' % ('|'.join([
    'ssx', 'skin', 'skins', 'get', 'lock', 'preview', 'download', 'export',
    'XWiki', 'cancel', 'resources', 'rollback', 'rest', 'webjars', 'bin', 'jsx'
]))

#urlpatterns += [
#    url(phenotips_urls, proxy_to_phenotips, name='proxy_to_phenotips'),
#]

urlpatterns += [
    url('project/(?P<project_guid>[^/]+)/patient/(?P<patient_id>[^/]+)/phenotips_view_patient_pdf', phenotips_view_patient_pdf),
    url('project/(?P<project_guid>[^/]+)/patient/(?P<patient_id>[^/]+)/phenotips_edit_patient', phenotips_edit_patient),
]

#urlpatterns += [
#   url("^api/v1/%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in api_endpoints.items()]

# other staff-only endpoints
urlpatterns += [
    url("^users", users_template),
    url(r'^hijack/', include('hijack.urls')),
]
