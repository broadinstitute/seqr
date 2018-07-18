from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

from django.conf import settings
import xbrowse_server.base.views.individual_views
import xbrowse_server.base.views.igv_views
import xbrowse_server.base.views.family_group_views
import xbrowse_server.base.views.reference_views
#import xbrowse_server.phenotips.views
import xbrowse_server.gene_lists.urls
import xbrowse_server.staff.urls
import django.contrib.admindocs.urls
import django.views.static
import xbrowse_server.api.urls


admin.autodiscover()


urlpatterns = [

    #
    # Public
    #
    url(r'^landingpage$', xbrowse_server.base.views.landing_page, name='landing_page'),
    url(r'^projects$', xbrowse_server.base.views.home, name='home'),  # DEPRECATED

    #
    # Account
    #
    url(r'^login$', xbrowse_server.base.views.login_view, name='login_view'),
    url(r'^logout$', xbrowse_server.base.views.logout_view, name='logout_view'),
    url(r'^set-password$', xbrowse_server.base.views.set_password, name='set_password'),
    url(r'^forgot-password$', xbrowse_server.base.views.forgot_password, name='forgot_password'),
    url(r'^forgot-password-sent$', xbrowse_server.base.views.forgot_password_sent, name='forgot_password_sent'),
    url(r'^user/(?P<username>\w+)', xbrowse_server.base.views.user_summary, name='user_summary'),

    #
    # Project
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/?$', xbrowse_server.base.views.project_home, name='project_home'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/manage$', xbrowse_server.base.views.project_views.manage_project, name='manage_project'),

    url(r'^project/(?P<project_id>[\w.|-]+)/individuals$', xbrowse_server.base.views.project_individuals, name='project_individuals'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/saved-variants', xbrowse_server.base.views.project_views.variants_with_tag, name='saved_variants'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/variants/(?P<tag>[^/]+)$', xbrowse_server.base.views.project_views.variants_with_tag, name='variants_with_tag'),  # DEPRECATED

    url(r'^project/(?P<project_id>[\w.|-]+)/settings$', xbrowse_server.base.views.project_settings, name='project_settings'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/project_gene_list_settings', xbrowse_server.base.views.project_gene_list_settings, name='project_gene_list_settings'),
    url(r'^project/(?P<project_id>[\w.|-]+)/collaborators', xbrowse_server.base.views.project_collaborators, name='project_collaborators'),
    url(r'^project/(?P<project_id>[\w.|-]+)/settings/add-collaborator$', xbrowse_server.base.views.add_collaborator, name='add_collaborator'),
    url(r'^project/(?P<project_id>[\w.|-]+)/settings/add-gene-list', xbrowse_server.base.views.add_gene_list, name='add_gene_list'),
    url(r'^project/(?P<project_id>[\w.|-]+)/gene-list/(?P<gene_list_slug>[\w|-]+)$', xbrowse_server.base.views.project_gene_list, name='project_gene_list'),
    url(r'^project/(?P<project_id>[\w.|-]+)/gene-list/(?P<gene_list_slug>[\w|-]+)/download$', xbrowse_server.base.views.project_gene_list_download, name='project_gene_list_download'),
    url(r'^project/(?P<project_id>[\w.|-]+)/gene-list/(?P<gene_list_slug>[\w|-]+)/remove', xbrowse_server.base.views.remove_gene_list, name='project_remove_gene_list'),
    url(r'^project/(?P<project_id>[\w.|-]+)/settings/remove-gene-list', xbrowse_server.base.views.remove_gene_list, name='remove_gene_list'),

    url(r'^project/(?P<project_id>[\w.|-]+)/edit-individuals$', xbrowse_server.base.views.edit_individuals, name='edit_individuals'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/save-all-individuals', xbrowse_server.base.views.save_all_individuals, name='save_all_individuals'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/save-one-individual', xbrowse_server.base.views.save_one_individual, name='save_one_individual'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/update-project-from-fam', xbrowse_server.base.views.update_project_from_fam, name='update_project_from_fam'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/delete-individuals', xbrowse_server.base.views.delete_individuals, name='delete_individuals'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/add-phenotype', xbrowse_server.base.views.add_phenotype, name='add_phenotype'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/add-individuals', xbrowse_server.base.views.add_individuals, name='add_individuals'),  # DEPRECATED

    url(r'^project/(?P<project_id>[\w.|-]+)/edit-basic-info$', xbrowse_server.base.views.project_views.edit_basic_info, name='edit_basic_info'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/add-collaborator$', xbrowse_server.base.views.project_views.add_collaborator, name='add_collaborator'),
    url(r'^project/(?P<project_id>[\w.|-]+)/add-collaborator-confirm$', xbrowse_server.base.views.project_views.add_collaborator_confirm, name='add_collaborator_confirm'),
    url(r'^project/(?P<project_id>[\w.|-]+)/collaborator/(?P<username>[\w|-]+)/edit$', xbrowse_server.base.views.project_views.edit_collaborator, name='edit_collaborator'),
    url(r'^project/(?P<project_id>[\w.|-]+)/collaborator/(?P<username>[\w|-]+)/delete$', xbrowse_server.base.views.project_views.delete_collaborator, name='delete_collaborator'),

    url(r'^project/(?P<project_id>[\w.|-]+)/gene/?(?P<gene_id>\w+)?$', xbrowse_server.base.views.project_views.gene_quicklook, name='project_gene_quicklook'),

    #
    # IGV.js views
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/igv-track/(?P<igv_track_name>.+)$', xbrowse_server.base.views.igv_views.fetch_igv_track, name='fetch_igv_track'),  # DEPRECATED

    #
    # Family views
    #
    url(r'^project/(?P<project_id>[\w.|-]+)/families$', xbrowse_server.base.views.family_views.families, name='families'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/?$', xbrowse_server.base.views.family_home, name='family_home'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/mendelian-variant-search', xbrowse_server.base.views.mendelian_variant_search, name='mendelian_variant_search'),
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/edit$', xbrowse_server.base.views.edit_family, name='edit_family'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/delete$', xbrowse_server.base.views.family_views.delete, name='delete_family'),  # DEPRECATED
    url(r'^project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w.|-]+)/coverage$', xbrowse_server.base.views.family_views.family_coverage, name='family_coverage'),
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

    url(r'', include('seqr.urls')),
    url(r'^api/', include('xbrowse_server.api.urls')),
    url(r'^gene-lists/', include(xbrowse_server.gene_lists.urls)),

    url(r'^staff/', include(xbrowse_server.staff.urls)),

    url(r'^xadmin/doc/', include(django.contrib.admindocs.urls)),
    url(r'^xadmin/', admin.site.urls),

    # TODO: new app
    url(r'^docs/(?P<doc_page_id>[\w|-]+)$', xbrowse_server.base.views.docs_md, name='docs_md'),

    url(r'^xstatic/style.css$', xbrowse_server.base.views.style_css, name='style_css'),

    url(r'^errorlog$', xbrowse_server.base.views.account_views.errorlog, name='errorlog'),

    url(r'^gene$', xbrowse_server.base.views.reference_views.gene_search, name='gene_search'),  # DEPRECATED
    url(r'^gene/(?P<gene_str>[\S]+)/?$', xbrowse_server.base.views.reference_views.gene_info, name='gene_info'),  # DEPRECATED

    #
    # Reporting pages
    #
    url(r'^report/project/(?P<project_id>[\w.|-]+)/?$', xbrowse_server.reports.views.project_report, name='project_report'),

    #
    # Matchmaker pages
    #
    url(r'^matchmaker/add/project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w|-]+)/individual/(?P<individual_id>[\w|-]+)$', xbrowse_server.matchmaker.views.matchmaker_add_page, name='matchmaker_add_page'),
    url(r'^matchmaker/search/project/(?P<project_id>[\w.|-]+)/family/(?P<family_id>[\w|-]+)$', xbrowse_server.matchmaker.views.matchmaker_search_page, name='matchmaker_search_page'),
    url(r'^matchmaker/disclaimer$', xbrowse_server.matchmaker.views.matchmaker_disclaimer_page, name='matchmaker_disclaimer_page'),
    url(r'^matchmaker/translate/matchbox_id$', xbrowse_server.matchmaker.views.matchbox_id_info, name='matchbox_id_info'),
    url(r'^matchmaker/matchbox_dashboard$', xbrowse_server.matchmaker.views.matchbox_dashboard, name='matchbox_dashboard'),
    url(r'^matchmaker/matchbox$', xbrowse_server.matchmaker.views.matchbox_info_page, name='matchbox_info_page'),

    #
    # Phenotype upload pages
    #
    url(r'^phenotypes/upload/project/(?P<project_id>[\w.|-]+)$', xbrowse_server.phenotips.views.phenotypes_upload_page, name='phenotypes_upload_page'),


    # Breakpoint Search
    url(r'', include('breakpoint_search.urls')),

]

#if settings.DEBUG:
urlpatterns += [
    url(r'^media/(?P<path>.*)$', django.views.static.serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]


#urlpatterns += staticfiles_urlpatterns()  # allow static files to be served through gunicorn
