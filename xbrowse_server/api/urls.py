from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    #
    # lookup methods
    #
    url(r'^projects$', 'xbrowse_server.api.views.projects', name='projects_api'),


    # reference info
    url(r'^gene-info/(?P<gene_id>[\w|-]+)$', 'xbrowse_server.api.views.gene_info', name='gene_info_api'),
    url(r'^variant$', 'xbrowse_server.api.views.variant_info', name='variant_info_api'),

    # family
    url(r'^mendelian-variant-search$', 'xbrowse_server.api.views.mendelian_variant_search', name='mendelian_variant_search_api'),
    url(r'^mendelian-variant-search-spec$', 'xbrowse_server.api.views.mendelian_variant_search_spec', name='mendelian_variant_search_spec_api'),

    url(r'^family/variant-annotation$', 'xbrowse_server.api.views.family_variant_annotation', name='family_variant_annotation_api'),

    # cohort
    url(r'^cohort-variant-search$', 'xbrowse_server.api.views.cohort_variant_search', name='cohort_variant_search_api'),
    url(r'^cohort-variant-search-spec$', 'xbrowse_server.api.views.cohort_variant_search_spec', name='cohort_variant_search_spec_api'),

    url(r'^cohort-gene-search$', 'xbrowse_server.api.views.cohort_gene_search', name='cohort_gene_search_api'),
    url(r'^cohort-gene-search-spec$', 'xbrowse_server.api.views.cohort_gene_search_spec', name='cohort_gene_search_spec_api'),
    url(r'^cohort-gene-search-variants$', 'xbrowse_server.api.views.cohort_gene_search_variants', name='cohort_gene_search_variants_api'),

    # family group
    url(r'^combine-mendelian-families$', 'xbrowse_server.api.views.combine_mendelian_families', name='combine_mendelian_families_api'),
    url(r'^combine-mendelian-families-spec', 'xbrowse_server.api.views.combine_mendelian_families_spec', name='combine_mendelian_families_spec_api'),
    url(r'^combine-mendelian-families-variants$', 'xbrowse_server.api.views.combine_mendelian_families_variants', name='combine_mendelian_families_variants_api'),

    url(r'^diagnostic-search', 'xbrowse_server.api.views.diagnostic_search', name='diagnostic_search_api'),

    url(r'^family/add-family-search-flag', 'xbrowse_server.api.views.add_family_search_flag', name='add_family_search_flag'),

    url(r'^autocomplete/gene$', 'xbrowse_server.api.views.gene_autocomplete', name='gene_autocomplete'),

)
