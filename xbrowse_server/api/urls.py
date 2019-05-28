from django.conf.urls import url

from django.contrib import admin
import xbrowse_server.api.views
import xbrowse_server.phenotips.views
import xbrowse_server.reports.views
import xbrowse_server.matchmaker.views


admin.autodiscover()

urlpatterns = [

    #
    # lookup methods
    #
    url(r'^projects$', xbrowse_server.api.views.projects, name='projects_api'),


    # reference info
    url(r'^gene-info/(?P<gene_id>[\w|-]+)$', xbrowse_server.api.views.gene_info, name='gene_info_api'),
    url(r'^add-or-edit-gene-note', xbrowse_server.api.views.add_or_edit_gene_note, name='add_or_edit_gene_note'),
    url(r'^delete-gene-note/(?P<note_id>[\d]+)$', xbrowse_server.api.views.delete_gene_note, name='delete_gene_note'),
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
    url(r'^family/add-family-analysed-by', xbrowse_server.api.views.add_family_analysed_by, name='add_family_analysed_by'),

    url(r'^autocomplete/gene$', xbrowse_server.api.views.gene_autocomplete, name='gene_autocomplete'),

    url(r'^add-or-edit-variant-note', xbrowse_server.api.views.add_or_edit_variant_note, name='add_or_edit_variant_note'),
    url(r'^delete-variant-note/(?P<note_id>[\d]+)$', xbrowse_server.api.views.delete_variant_note, name='delete_variant_note'),
    url(r'^add-or-edit-variant-tags', xbrowse_server.api.views.add_or_edit_variant_tags, name='add_or_edit_variant_tags'),
    url(r'^add-or-edit-variant-functional-data', xbrowse_server.api.views.add_or_edit_functional_data, name='add_or_edit_functional_data'),
    
    #phenotips related
    url(r'^phenotips/proxy/edit/(?P<eid>[\w.|-]+)$', xbrowse_server.phenotips.views.fetch_phenotips_edit_page, name='fetch_phenotips_edit_page'),
    url(r'^phenotips/proxy/view/(?P<eid>[\w.|-]+)$', xbrowse_server.phenotips.views.fetch_phenotips_pdf_page, name='fetch_phenotips_pdf_page'),
    url(r'^phenotips/proxy/project/(?P<project_id>[\w|-]+)/individual/(?P<eid>[\w.|-]+)$', xbrowse_server.phenotips.views.insert_individual_into_phenotips, name='insert_into_phenotips'),
    
    
    #updated reporting URIs
    url(r'^reports/project/(?P<project_id>[\w|-]+)/individuals', xbrowse_server.api.views.get_project_individuals, name='get_project_individuals'),
    
    url(r'^reports/project/(?P<project_id>[\w|-]+)/family/(?P<family_id>[\w|-]+)/individuals/$', xbrowse_server.api.views.get_family_individuals, name='get_family_individuals'),
    
    url(r'^reports/project/(?P<project_id>[\w|-]+)/phenotypes', xbrowse_server.api.views.export_project_individuals_phenotypes, name='export_project_individuals_phenotypes'),
    url(r'^reports/project/(?P<project_id>[\w|-]+)/families_status', xbrowse_server.api.views.export_project_family_statuses, name='export_project_family_statuses'),
    url(r'^reports/project/(?P<project_id>[\w|-]+)/variants', xbrowse_server.api.views.export_project_variants, name='export_project_variants'),


    #matchmaker related URLs
    url(r'^matchmaker/candidate/project/(?P<project_id>[\w|-]+)/family/(?P<family_id>[\w|-]+)/individual/(?P<indiv_id>[\w\s|-]+)$', xbrowse_server.api.views.get_submission_candidates, name='get_submission_candidates'),
    url(r'^matchmaker/add$', xbrowse_server.api.views.add_individual, name='add_individual'),
    url(r'^matchmaker/last_submission/project/(?P<project_id>[\w|-]+)/family/(?P<family_id>[\w|-]+)$', xbrowse_server.api.views.get_family_submissions, name='get_family_submissions'),
    url(r'^matchmaker/match_internally_and_externally/project/(?P<project_id>[\w|-]+)/individual/(?P<indiv_id>[\w\s|-]+)$', xbrowse_server.api.views.match_internally_and_externally, name='match_internally_and_externally'),
    url(r'^matchmaker/match_in_open_mme_sources/project/(?P<project_id>[\w|-]+)/individual/(?P<indiv_id>[\w|-]+)$', xbrowse_server.api.views.match_in_open_mme_sources, name='match_in_open_mme_sources'),
    url(r'^matchmaker/project/(?P<project_id>[\w|-]+)/individual/(?P<indiv_id>[\w\s|-]+)/delete$', xbrowse_server.api.views.delete_individual, name='delete_individual'),

    url(r'^matchmaker/translate/matchbox_id/(?P<matchbox_id>[\w|-]+)$', xbrowse_server.api.views.get_matchbox_id_details, name='get_matchbox_id_details'),
    url(r'^matchmaker/metrics$', xbrowse_server.api.views.get_matchbox_metrics, name='get_matchbox_metrics'),
    url(r'^matchmaker/metrics/project/(?P<project_id>[\w|-]+)$', xbrowse_server.api.views.get_matchbox_metrics_for_project, name='get_matchbox_metrics_for_project'),
    
    #matchmaker result tracking
    url(r'^matchmaker/result_tracking/comments/project/(?P<project_id>[\w|-]+)/match_id/(?P<match_id>[\w:|-]+)/individual/(?P<indiv_id>[\w|-]+)$', xbrowse_server.api.views.update_match_comment, name='update_match_comment'),
    url(r'^matchmaker/result_tracking/match_state_update/project/(?P<project_id>[\w|-]+)/match_id/(?P<match_id>[\w:|-]+)/individual/(?P<indiv_id>[\w|-]+)$', xbrowse_server.api.views.match_state_update, name='match_state_update'),
    url(r'^matchmaker/result_tracking/current_match_state$', xbrowse_server.api.views.get_current_match_state_of_all_results, name='get_current_match_state_of_all_results'),
    url(r'^matchmaker/result_tracking/current_match_state/project/(?P<project_id>[\w|-]+)/match_id/(?P<match_id>[\w:|-]+)/individual/(?P<indiv_id>[\w|-]+)$', xbrowse_server.api.views.get_current_match_state, name='get_current_match_state'),
]
