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

from django.conf.urls import url
import seqr.views.pages
import seqr.views.api

page_endpoints = {
    'dashboard': seqr.views.pages.dashboard,
    'search': seqr.views.pages.search,
    'project/(?P<project_guid>[\w.|-]+)/case_review': seqr.views.pages.case_review,
}

api_endpoints = {
    'user': seqr.views.api.user,
    'projects_and_stats': seqr.views.api.projects_and_stats,
    'projects': seqr.views.api.projects,

    'project/(?P<project_guid>[\w.|-]+)/case_review_data': seqr.views.api.case_review_data,
    'project/(?P<project_guid>[\w.|-]+)/save_case_review_status': seqr.views.api.save_case_review_status,
    'project/(?P<project_guid>[\w.|-]+)/family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_notes': seqr.views.api.save_internal_case_review_notes,
    'project/(?P<project_guid>[\w.|-]+)/family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_summary': seqr.views.api.save_internal_case_review_summary,
}


# page templates
urlpatterns = []

urlpatterns += [
    url("^%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in page_endpoints.items()
]

# api
urlpatterns += [
    url("^api/%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in api_endpoints.items()
]

#urlpatterns += [url("^api/v1/%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in api_endpoints.items()]

