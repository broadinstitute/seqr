from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

from django.conf import settings
import xbrowse_server.base.views.individual_views
import xbrowse_server.base.views.igv_views
import xbrowse_server.base.views.family_group_views
import xbrowse_server.base.views.reference_views
import xbrowse_server.phenotips.views
import xbrowse_server.api.urls
import xbrowse_server.gene_lists.urls
import xbrowse_server.staff.urls
import django.contrib.admindocs.urls
import django.views.static

admin.autodiscover()

urlpatterns = [

    #
    # Public
    #
    url(r'^landingpage$', xbrowse_server.base.views.landing_page, name='landing_page'),
    url(r'^$', xbrowse_server.base.views.home, name='home'),
    url(r'^about$', xbrowse_server.base.views.about, name='about'),

    #
    # Account
    #
    url(r'^login$', xbrowse_server.base.views.login_view, name='login_view'),
    url(r'^logout$', xbrowse_server.base.views.logout_view, name='logout_view'),
    url(r'^set-password$', xbrowse_server.base.views.set_password, name='set_password'),
    url(r'^forgot-password$', xbrowse_server.base.views.forgot_password, name='forgot_password'),
    url(r'^forgot-password-sent$', xbrowse_server.base.views.forgot_password_sent, name='forgot_password_sent'),
    url(r'^users', xbrowse_server.base.views.users, name='users'),
    url(r'^user/(?P<username>\w+)', xbrowse_server.base.views.user_summary, name='user_summary'),

    #
    # Project
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/?$', xbrowse_server.base.views.project_home, name='project_home'),
    url(r'^project/(?P<project_id>[\w.|-]+)/manage$', xbrowse_server.base.views.project_views.manage_project, name='manage_project'),

    url(r'^project/(?P<project_id>[\w.|-]+)/individuals$', xbrowse_server.base.views.project_individuals, name='project_individuals'),
    url(r'^project/(?P<project_id>[\w.|-]+)/saved-variants', xbrowse_server.base.views.project_views.saved_variants, name='saved_variants'),
    url(r'^project/(?P<project_id>[\w.|-]+)/variants/(?P<tag>[^/]+)$', xbrowse_server.base.views.project_views.variants_with_tag, name='variants_with_tag'),
    url(r'^project/(?P<project_id>[\w.|-]+)/causal-variants$', xbrowse_server.base.views.project_views.causal_variants, name='causal_variants'),
    
    url(r'^project/(?P<project_id>[\w.|-]+)/settings$', xbrowse_server.base.views.project_settings, name='project_settings'),
    url(r'^project/(?P<project_id>[\w.|-]+)/project_gene_list_settings', xbrowse_server.base.views.project_gene_list_settings, name='project_gene_list_settings'),
    url(r'^project/(?P<project_id>[\w.|-]+)/collaborators', xbrowse_server.base.views.project_collaborators, name='project_collaborators'),
    url(r'^project/(?P<project_id>[\w.|-]+)/settings/reference-populations$', xbrowse_server.base.views.edit_project_refpops, name='edit_project_refpops'),
    url(r'^project/(?P<project_id>[\w.|-]+)/settings/add-collaborator$', xbrowse_server.base.views.add_collaborator, name='add_collaborator'),
    url(r'^project/(?P<project_id>[\w.|-]+)/settings/add-gene-list', xbrowse_server.base.views.add_gene_list, name='add_gene_list'),
    url(r'^project/(?P<project_id>[\w.|-]+)/gene-list/(?P<gene_list_slug>[\w|-]+)$', xbrowse_server.base.views.project_gene_list, name='project_gene_list'),
    url(r'^project/(?P<project_id>[\w.|-]+)/gene-list/(?P<gene_list_slug>[\w|-]+)/download$', xbrowse_server.base.views.project_gene_list_download, name='project_gene_list_download'),
    url(r'^project/(?P<project_id>[\w.|-]+)/gene-list/(?P<gene_list_slug>[\w|-]+)/remove', xbrowse_server.base.views.remove_gene_list, name='project_remove_gene_list'),
    url(r'^project/(?P<project_id>[\w.|-]+)/settings/remove-gene-list', xbrowse_server.base.views.remove_gene_list, name='remove_gene_list'),

    url(r'^project/(?P<project_id>[\w.|-]+)/edit-individuals$', xbrowse_server.base.views.edit_individuals, name='edit_individuals'),
    url(r'^project/(?P<project_id>[\w.|-]+)/save-all-individuals', xbrowse_server.base.views.save_all_individuals, name='save_all_individuals'),
    url(r'^project/(?P<project_id>[\w.|-]+)/save-one-individual', xbrowse_server.base.views.save_one_individual, name='save_one_individual'),
    url(r'^project/(?P<project_id>[\w.|-]+)/update-project-from-fam', xbrowse_server.base.views.update_project_from_fam, name='update_project_from_fam'),
    url(r'^project/(?P<project_id>[\w.|-]+)/delete-individuals', xbrowse_server.base.views.delete_individuals, name='delete_individuals'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-phenotype', xbrowse_server.base.views.add_phenotype, name='add_phenotype'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-individuals', xbrowse_server.base.views.add_individuals, name='add_individuals'),

    url(r'^project/(?P<project_id>[\w.|-]+)/edit-basic-info$', xbrowse_server.base.views.project_views.edit_basic_info, name='edit_basic_info'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-collaborator$', xbrowse_server.base.views.project_views.add_collaborator, name='add_collaborator'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-collaborator-confirm$', xbrowse_server.base.views.project_views.add_collaborator_confirm, name='add_collaborator_confirm'),
    url(r'^project/(?P<project_id>[\w.|-]+)/collaborator/(?P<username>[\w|-]+)/edit$', xbrowse_server.base.views.project_views.edit_collaborator, name='edit_collaborator'),
    url(r'^project/(?P<project_id>[\w.|-]+)/collaborator/(?P<username>[\w|-]+)/delete$', xbrowse_server.base.views.project_views.delete_collaborator, name='delete_collaborator'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-tag', xbrowse_server.base.views.project_views.add_tag, name='add_tag'),

    url(r'^project/(?P<project_id>[\w.|-]+)/gene/?(?P<gene_id>\w+)?$', xbrowse_server.base.views.project_views.gene_quicklook, name='project_gene_quicklook'),
    url(r'^project/(?P<project_id>[\w.|-]+)/edit-tag/(?P<tag_name>[^/]+)/tag-title/(?P<tag_title>[^/]+)',    xbrowse_server.base.views.project_views.edit_tag, name='edit_tag'),
    url(r'^project/(?P<project_id>[\w.|-]+)/delete-tag/(?P<tag_name>[^/]+)/tag-title/(?P<tag_title>[^/]+)', xbrowse_server.base.views.project_views.delete_tag, name='delete_tag'),


    #
    # Individual views
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/individual/(?P<indiv_id>[\w|-]+)/?$', xbrowse_server.base.views.individual_views.individual_home, name='individual_home'),

    #
    # IGV.js views
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/igv-track/(?P<igv_track_name>.+)$', xbrowse_server.base.views.igv_views.fetch_igv_track, name='fetch_igv_track'),

    #
    # Family views
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/families$', xbrowse_server.base.views.family_views.families, name='families'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/?$', xbrowse_server.base.views.family_home, name='family_home'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/mendelian-variant-search', xbrowse_server.base.views.mendelian_variant_search, name='mendelian_variant_search'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/variant', xbrowse_server.base.views.family_views.family_variant_view, name='family_variant_view'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/edit$', xbrowse_server.base.views.edit_family, name='edit_family'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/delete$', xbrowse_server.base.views.family_views.delete, name='delete_family'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/coverage$', xbrowse_server.base.views.family_views.family_coverage, name='family_coverage'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/saved-variants$', xbrowse_server.base.views.family_views.saved_variants, name='saved_family_variants'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/diagnostic-search', xbrowse_server.base.views.family_views.diagnostic_search, name='diagnostic_search'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/gene$', xbrowse_server.base.views.family_views.family_gene_lookup, name='family_gene_lookup'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/cause$', xbrowse_server.base.views.family_views.edit_family_cause, name='edit_family_cause'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/pedigreeimage/delete', xbrowse_server.base.views.family_views.pedigree_image_delete, name='pedigree_image_delete'),

    #
    # Cohort views
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/cohorts$', xbrowse_server.base.views.cohort_views.cohorts, name='cohorts'),
    url(r'^project/(?P<project_id>[\w.|-]+)/cohorts/add', xbrowse_server.base.views.cohort_views.add, name='cohort_add'),
    url(r'^project/(?P<project_id>[\w.|-]+)/cohort/(?P<cohort_id>[\w.|-]+)$', xbrowse_server.base.views.cohort_home, name='cohort_home'),
    url(r'^project/(?P<project_id>[\w.|-]+)/cohort/(?P<cohort_id>[\w.|-]+)/edit$', xbrowse_server.base.views.cohort_views.edit, name='cohort_edit'),
    url(r'^project/(?P<project_id>[\w.|-]+)/cohort/(?P<cohort_id>[\w.|-]+)/delete', xbrowse_server.base.views.cohort_views.delete, name='cohort_delete'),
    url(r'^project/(?P<project_id>[\w.|-]+)/cohort/(?P<cohort_id>[\w.|-]+)/variant-search', xbrowse_server.base.views.cohort_variant_search, name='cohort_variant_search'),
    url(r'^project/(?P<project_id>[\w.|-]+)/cohort/(?P<cohort_id>[\w.|-]+)/cohort-gene-search$', xbrowse_server.base.views.cohort_gene_search, name='cohort_gene_search'),


    #
    # Family group views
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/family-groups$', xbrowse_server.base.views.family_group_views.family_groups, name='family_groups'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-family-group$', xbrowse_server.base.views.family_group_views.add_family_group, name='add_family_group'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-family-group-submit$', xbrowse_server.base.views.family_group_views.add_family_group_submit, name='add_family_group_submit'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family-group/(?P<family_group_slug>[\w.|-]+)$', xbrowse_server.base.views.family_group_views.family_group_home, name='family_group_home'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family-group/(?P<family_group_slug>[\w.|-]+)/edit$', xbrowse_server.base.views.family_group_views.family_group_edit, name='family_group_edit'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family-group/(?P<family_group_slug>[\w.|-]+)/delete$', xbrowse_server.base.views.family_group_views.delete, name='family_group_delete'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family-group/(?P<family_group_slug>[\w.|-]+)/combine-mendelian-families$', xbrowse_server.base.views.family_group_views.combine_mendelian_families, name='combine_mendelian_families'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family-group/(?P<family_group_slug>[\w.|-]+)/gene/(?P<gene_id>[\w|-]+)$', xbrowse_server.base.views.family_group_views.family_group_gene, name='family_group_gene'),
    
    url(r'^api/', include('xbrowse_server.api.urls')),
    url(r'^gene-lists/', include(xbrowse_server.gene_lists.urls)),

    url(r'^staff/', include(xbrowse_server.staff.urls)),

    url(r'^xadmin/doc/', include(django.contrib.admindocs.urls)),
    url(r'^xadmin/', include(admin.site.urls)),

    # TODO: new app
    url(r'^docs/(?P<doc_page_id>[\w|-]+)$', xbrowse_server.base.views.docs_md, name='docs_md'),

    url(r'^xstatic/style.css$', xbrowse_server.base.views.style_css, name='style_css'),

    url(r'^errorlog$', xbrowse_server.base.views.account_views.errorlog, name='errorlog'),

    url(r'^gene$', xbrowse_server.base.views.reference_views.gene_search, name='gene_search'),
    url(r'^gene/(?P<gene_str>[\S]+)/?$', xbrowse_server.base.views.reference_views.gene_info, name='gene_info'),
        
    #
    # To proxy Phenotips static resources (a bit of a hack to offload authentication and user management
    # to xBrowse)    
    url(r'^bin/get',xbrowse_server.phenotips.views.proxy_post, name='proxy_post'),
    url(r'^resources', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^rest/wikis/xwiki/spaces/data/pages/WebHome/objects',xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^rest/wikis/xwiki/spaces/data/pages', xbrowse_server.phenotips.views.proxy_post, name='proxy_post'),
    url(r'^rest', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/data',xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),    
    url(r'^webjars',xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/webjars',xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/skin', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/jsx', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/ssx', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/lock', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/download', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/cancel', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/rollback', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/preview', xbrowse_server.phenotips.views.proxy_post, name='proxy_post'),
    url(r'^bin/edit', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin/PhenoTips', xbrowse_server.phenotips.views.proxy_post, name='proxy_post'),
    url(r'^bin/objectadd', xbrowse_server.phenotips.views.proxy_post, name='proxy_post'),
    url(r'^bin/objectremove', xbrowse_server.phenotips.views.proxy_post, name='proxy_post'),
    url(r'^bin/XWiki', xbrowse_server.phenotips.views.proxy_get, name='proxy_get'),
    url(r'^bin', xbrowse_server.phenotips.views.proxy_get, name='proxy_get')
]

if settings.DEBUG != 4:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', django.views.static.serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
   ]

urlpatterns += staticfiles_urlpatterns()  # allow static files to be served through gunicorn
