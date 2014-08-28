from django.conf.urls import patterns, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
     url(r'^$', 'xbrowse_server.gene_lists.views.home', name='gene_lists_home'),
     url(r'^add$', 'xbrowse_server.gene_lists.views.add', name='gene_lists_add'),
     url(r'^(?P<slug>[\w|-]+)$', 'xbrowse_server.gene_lists.views.gene_list', name='gene_list'),
     url(r'^(?P<slug>[\w|-]+)/edit$', 'xbrowse_server.gene_lists.views.edit', name='gene_list_edit'),
     url(r'^(?P<slug>[\w|-]+)/download$', 'xbrowse_server.gene_lists.views.download', name='gene_list_download'),
)
