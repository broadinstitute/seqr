from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

from django.conf import settings
import xbrowse_server.base.views.igv_views
import xbrowse_server.base.views.family_group_views
import xbrowse_server.base.views.reference_views
import xbrowse_server.phenotips.views
import xbrowse_server.gene_lists.urls
import xbrowse_server.staff.urls
import django.contrib.admindocs.urls
import django.views.static
import xbrowse_server.api.urls
from breakpoint_search.views import breakpoint_search, breakpoints,\
    project_breakpoint
#import seqr.urls

admin.autodiscover()


urlpatterns = [
    # Breakpoint search
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/breakpoint-search', breakpoint_search, name='breakpoint_search'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/breakpoints', breakpoints, name='breakpoints'),
    url(r'^project/(?P<project_id>[\w.|-]+)/breakpoint/(?P<breakpoint_id>[\w.|-]+)', project_breakpoint, name='project_breakpoint'),
]

