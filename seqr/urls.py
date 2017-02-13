"""seqr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/

Examples:
Function views
1. Add an import:  from my_app import views
2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
1. Add an import:  from other_app.views import Home
2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
1. Import the include() function: from django.conf.urls import url, include
2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import url, include

from seqr.views.phenotips_api import \
    proxy_to_phenotips, \
    phenotips_edit_patient, \
    phenotips_view_patient_pdf

from seqr.views.case_review_page import \
    case_review_page, \
    case_review_page_data, \
    save_case_review_status, \
    save_internal_case_review_notes, \
    save_internal_case_review_summary

from seqr.views.dashboard_page import \
    dashboard_page, \
    dashboard_page_data

from seqr.views.awesomebar_api import awesomebar_autocomplete
from seqr.views.auth_api import login_required_error, API_LOGIN_REQUIRED_URL
from seqr.views.project_api import create_project, update_project, delete_project, update_project_categories

page_endpoints = {
    'dashboard': {
        'html': dashboard_page,
        'initial_json': dashboard_page_data,
    },
    'project/(?P<project_guid>[^/]+)/case_review': {
        'html': case_review_page,
        'initial_json': case_review_page_data,
    },
}

api_endpoints = {
    'project/(?P<project_guid>[^/]+)/save_case_review_status': save_case_review_status,
    'project/(?P<project_guid>[^/]+)/family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_notes': save_internal_case_review_notes,
    'project/(?P<project_guid>[^/]+)/family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_summary': save_internal_case_review_summary,

    'project/create_project': create_project,
    'project/(?P<project_guid>[^/]+)/update_project': update_project,
    'project/(?P<project_guid>[^/]+)/delete_project': delete_project,
    'project/(?P<project_guid>[^/]+)/update_project_categories': update_project_categories,

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
    'ssx', 'skin', 'get', 'lock', 'preview', 'download', 'export',
    'XWiki', 'cancel', 'resources', 'rest', 'webjars', 'bin', 'jsx'
]))

urlpatterns += [
    url(phenotips_urls, proxy_to_phenotips, name='proxy_to_phenotips'),
]

urlpatterns += [
    url('project/(?P<project_guid>[^/]+)/patient/(?P<patient_id>[^/]+)/phenotips_view_patient_pdf', phenotips_view_patient_pdf),
    url('project/(?P<project_guid>[^/]+)/patient/(?P<patient_id>[^/]+)/phenotips_edit_patient', phenotips_edit_patient),
]

#urlpatterns += [url("^api/v1/%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in api_endpoints.items()]

#urlpatterns += [
#    url(r'^hijack/', include('hijack.urls')),
#]

#urlpatterns += [
#    url(r'^su/', include('django_su.urls')),
#]