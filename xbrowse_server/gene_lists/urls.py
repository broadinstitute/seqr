from django.conf.urls import patterns, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
     url(r'^(?P<slug>[\w|-]+)$', 'xbrowse_server.gene_lists.views.gene_list', name='gene_list'),
)
