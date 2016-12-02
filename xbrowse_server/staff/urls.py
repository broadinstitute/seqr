from django.conf.urls import url

from django.contrib import admin

import xbrowse_server.staff.views

admin.autodiscover()

urlpatterns = [
    url(r'^last1000$', xbrowse_server.staff.views.last_1000_views, name='last_1000_views'),
    url(r'^userinfo/(?P<username>[\w|-]+)', xbrowse_server.staff.views.userinfo, name='userinfo'),
]