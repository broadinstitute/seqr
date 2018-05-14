window.CohortGeneSearchForm = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.dictionary = options.hbc.dictionary;
        this.cohort = options.cohort;

        this.select_method_view = new SelectCohortSearchMethodView({
            hbc: this.hbc,
            cohort: this.cohort,
        });

        this.select_variants_view = new SelectVariantsView({
            hbc: this.hbc,
            variantFilter: this.variantFilter,
            qualityFilter: this.qualityFilter,
        });

        this.select_quality_view = new CohortQualityFilterView({
            hbc: this.hbc,
            defaultQualityFilters: this.dictionary.default_quality_filters,
        });
    },

    template: _.template($('#tpl-cohort-gene-search-form').html()),

    render: function(event) {
        $(this.el).html(this.template());
        this.$('#tplholder-select-inheritance').html(this.select_method_view.render().el);
        this.$('#tplholder-select-variants').html(this.select_variants_view.render().el);
        this.$('#select-quality-filter-container').html(this.select_quality_view.render().el);
        return this;
    },

    get_search_spec: function() {
        return {
            inheritance_mode: this.select_method_view.getInheritanceMode(),
            variant_filter: this.select_variants_view.getVariantFilter(),
            quality_filter: this.select_quality_view.getQualityFilter(),
        }
    },

    /*
    Initiate all the search controls from spec, which is a dict with the following keys:
    - variant_filter: VariantFilter (backbone model)
    - inheritance_mode: string
    - quality_filter: QualityFilter (backbone model)
     */
    load_search_spec: function(spec) {
        this.select_method_view.setInheritanceMode(spec.inheritance_mode);
        this.select_variants_view.loadFromVariantFilter(spec.variant_filter);
        this.select_quality_view.loadFromQualityFilter(spec.quality_filter);
    },

});

window.CohortGeneSearchHBC = HeadBallCoach.extend({

    routes: {
        "": "base", // clear everything
        "search/:search_hash/results": "search_results", // load search then fetch results
    },

    initialize: function(options) {

        // required args
        this.project_options = options.project_options;
        this.cohort = options.cohort;

        this.search_spec = {};
        this.search_form_view = new CohortGeneSearchForm({
            hbc: this,
            cohort: this.cohort,
        });
    },

    bind_to_dom: function() {
        var that = this;
        $('#search-form-container').html(this.search_form_view.render().el);
        $('#run-search').on('click', function() {
            that.run_search();
        });
    },

    search_loading: function() {
        $('#resultsContainer').html('');
        $("#search-go").hide();
        $('#search-go-loading').show();
    },

    // someone just clicked the search button!
    run_search: function() {
        var that = this;

        var search_spec = this.search_form_view.get_search_spec();
        that.search_loading();

        var url = '/api/cohort-gene-search';
        var postData = {
            project_id: this.cohort.project_id,
            cohort_id: this.cohort.cohort_id,
            inheritance_mode: search_spec.inheritance_mode,
            variant_filter: JSON.stringify(search_spec.variant_filter),
            quality_filter: JSON.stringify(search_spec.quality_filter),
        };

        $.get(url, postData, function(data) {
            if (data.is_error) {
                alert('There was an error with your search: ' + data.error);
            } else {
                that.set_results(data.search_hash, search_spec, data.genes);
                that.navigate('search/'+data.search_hash+'/results');
            }
        });
    },

    // we just got results - set them
    set_results: function(search_hash, search_spec, genes) {
        var that = this;
        that.search_spec = search_spec;
        that.results_view = new CohortResultsView({
            hbc: this.hbc,
            genes: genes,
            search_spec: this.search_spec,
            cohort: this.cohort,
        });
        $('#resultsContainer').html(that.results_view.render().el);
        $("#search-go").show();
        $('#search-go-loading').hide();
    },

    base: function() {
        this.resetModal();
        this.search_form_view.load_search_spec({});
    },

    set_search_spec: function(search_spec) {
        this.search_spec = search_spec;
        this.search_form_view.load_search_spec(search_spec);
    },

    search_results: function(search_hash) {
        var that = this;
        that.resetModal();
        that.search_loading();

        // API call to get original search and results
        var postData = {
            project_id: that.cohort.project_id,
            cohort_id: that.cohort.cohort_id,
            search_hash: search_hash,
        };

        $.get('/api/cohort-gene-search-spec', postData, function(data) {
            if (!data.is_error) {
                that.set_search_spec(data.search_spec);
                that.set_results(search_hash, data.search_spec, data.genes);
            }
        });
    },

    gene_variants: function(gene_id) {
        var view = new CohortVariantsView({
            hbc: this,
            gene_id: gene_id,
            cohort: this.cohort,
            search_spec: this.search_spec,
        });
        this.pushModal("title", view);
    },

});


$(document).ready(function() {

    var hbc = new CohortGeneSearchHBC({
        dictionary: DICTIONARY,
        project_options: PROJECT_OPTIONS,
        cohort: COHORT,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});







