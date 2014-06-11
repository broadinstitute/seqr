from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^last1000$', 'xbrowse_server.staff.views.last_1000_views', name='last_1000_views'),
    url(r'^userinfo/(?P<username>[\w|-]+)', 'xbrowse_server.staff.views.userinfo', name='userinfo'),
)