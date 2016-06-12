from django.conf.urls import patterns, url

from django.contrib import admin
import xbrowse_server.api.views
import xbrowse_server.phenotips.views
import xbrowse_server.reports.views


admin.autodiscover()

urlpatterns = [

    #
    # lookup methods
    #
    url(r'^projects$', xbrowse_server.api.views.projects, name='projects_api'),


    # reference info
    url(r'^gene-info/(?P<gene_id>[\w|-]+)$', xbrowse_server.api.views.gene_info, name='gene_info_api'),
    url(r'^variant$', xbrowse_server.api.views.variant_info, name='variant_info_api'),

    # family
    url(r'^mendelian-variant-search$', xbrowse_server.api.views.mendelian_variant_search, name='mendelian_variant_search_api'),
    url(r'^mendelian-variant-search-spec$', xbrowse_server.api.views.mendelian_variant_search_spec, name='mendelian_variant_search_spec_api'),
    url(r'^family-gene-lookup$', xbrowse_server.api.views.family_gene_lookup, name='family_gene_lookup_api'),

    url(r'^family/variant-annotation$', xbrowse_server.api.views.family_variant_annotation, name='family_variant_annotation_api'),

    # cohort
    url(r'^cohort-variant-search$', xbrowse_server.api.views.cohort_variant_search, name='cohort_variant_search_api'),
    url(r'^cohort-variant-search-spec$', xbrowse_server.api.views.cohort_variant_search_spec, name='cohort_variant_search_spec_api'),

    url(r'^cohort-gene-search$', xbrowse_server.api.views.cohort_gene_search, name='cohort_gene_search_api'),
    url(r'^cohort-gene-search-spec$', xbrowse_server.api.views.cohort_gene_search_spec, name='cohort_gene_search_spec_api'),
    url(r'^cohort-gene-search-variants$', xbrowse_server.api.views.cohort_gene_search_variants, name='cohort_gene_search_variants_api'),

    # family group
    url(r'^combine-mendelian-families$', xbrowse_server.api.views.combine_mendelian_families, name='combine_mendelian_families_api'),
    url(r'^combine-mendelian-families-spec', xbrowse_server.api.views.combine_mendelian_families_spec, name='combine_mendelian_families_spec_api'),
    url(r'^combine-mendelian-families-variants$', xbrowse_server.api.views.combine_mendelian_families_variants, name='combine_mendelian_families_variants_api'),

    url(r'^diagnostic-search', xbrowse_server.api.views.diagnostic_search, name='diagnostic_search_api'),
 
    url(r'^family/add-family-search-flag', xbrowse_server.api.views.add_family_search_flag, name='add_family_search_flag'),

    url(r'^autocomplete/gene$', xbrowse_server.api.views.gene_autocomplete, name='gene_autocomplete'),

    url(r'^add-or-edit-variant-note', xbrowse_server.api.views.add_or_edit_variant_note, name='add_or_edit_variant_note'),
    url(r'^delete-variant-note/(?P<note_id>[\d]+)$', xbrowse_server.api.views.delete_variant_note, name='delete_variant_note'),
    url(r'^add-or-edit-variant-tags', xbrowse_server.api.views.add_or_edit_variant_tags, name='add_or_edit_variant_tags'),
    
    #phenotips related
    url(r'^phenotips/proxy/edit/(?P<eid>[\w|-]+)$', xbrowse_server.phenotips.views.fetch_phenotips_edit_page, name='fetch_phenotips_edit_page'),
    url(r'^phenotips/proxy/view/(?P<eid>[\w|-]+)$', xbrowse_server.phenotips.views.fetch_phenotips_pdf_page, name='fetch_phenotips_pdf_page'),
    
    #reporting URLs
    url(r'^reports/individuals/project/(?P<project_id>[\w|-]+)$', xbrowse_server.reports.views.export_project_individuals, name='export_project_individuals'),
]
