var CohortVariantSearchForm = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.cohort = options.cohort;
        this.dictionary = this.hbc.dictionary;

        this.select_method_view = new SelectCohortSearchMethodView({
            hbc: this.hbc,
            cohort: this.cohort,
        });

        this.select_variants_view = new SelectVariantsView({
            hbc: this.hbc,
            variantFilter: this.variantFilter,
            qualityFilter: this.qualityFilter,
        });

        this.select_quality_filter_view = new SelectQualityFilterView({
            qualityFilter: this.quality_filter,
            default_quality_filters: this.dictionary.default_quality_filters,
        });
    },

    template: _.template($('#tpl-cohort-variant-search-form').html()),

    render: function(event) {
        var that = this;
        $(this.el).html(this.template());

        this.$('#tplholder-select-inheritance').html(that.select_method_view.render().el);
        this.$('#tplholder-select-variants').html(that.select_variants_view.render().el);
        this.$('#select-quality-filter-container').html(that.select_quality_filter_view.render().el);

        return this;
    },

    get_search_spec: function() {
        var spec = {
            inheritance_mode: this.select_method_view.getInheritanceMode(),
            variant_filter: this.select_variants_view.getVariantFilter(),
            quality_filter: this.select_quality_filter_view.getQualityFilter(),
        };
        return spec;
    },

    // fill out form fields from the search spec
    load_search_spec: function(search_spec) {

        this.select_variants_view.loadFromVariantFilter(search_spec.variant_filter);
        this.select_quality_filter_view.loadFromQualityFilter(search_spec.quality_filter);
        this.select_method_view.setInheritanceMode(search_spec.inheritance_mode);
    },

});


var CohortVariantSearchResultsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.variants = options.variants;
        this.cohort = options.cohort;
    },

    template: _.template($('#tpl-cohort-variant-search-results').html()),

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            num_variants: that.variants.length,
        }));

        if (that.variants.length > 0) {
            _.each(that.variants, function(variant) {
                var individuals = _.filter(that.cohort.individuals, function(i) { return variant.genotypes[i.indiv_id].num_alt != 0; });
                var view = new BasicVariantView({
                    hbc: that.hbc,
                    variant: variant,
                    show_genotypes: true,
                    individuals: individuals,
                });
                that.$('.basic-variants-list').append(view.render().el);
            });
        }
        return this;
    },

});

var CohortVariantSearchHBC = HeadBallCoach.extend({

    initialize: function(options) {
        var that = this;

        // caller must provide these
        this.dictionary = options.dictionary;
        this.project_options = options.project_options;
        this.cohort = options.cohort;

        this.search_form_view = new CohortVariantSearchForm({
            hbc: that,
            cohort: that.cohort,
        });

    },

    routes: {
        "": "base",
        "search/:search_hash/results": "searchResults", // load search then fetch results
    },

    // route - clean page
    base: function() {
        this.resetModal();
        this.search_form_view.load_search_spec({});
    },

    // route - show search results for search_hash (a string hash)
    searchResults: function(search_hash) {
        var that = this;
        that.resetModal();
        that.set_loading();

        // API call to get original search and results
        var postData = {
            project_id: this.cohort['project_id'],
            cohort_id: this.cohort['cohort_id'],
            search_hash: search_hash,
        };

        $.get('/api/cohort-variant-search-spec', postData, function(data) {
            if (!data.is_error) {
                that.search_form_view.load_search_spec(data.search_spec);  // form controls
                that.setResults(search_hash, data.search_spec, data.variants);  // and results
            } else {
                alert('error 1983409');
            }
        });
    },

    showResults: function(type) {
		$("#search-go").show();
		$('#search-go-loading').hide();
	},

	showNoSearch: function() {
		$('#search-results').hide();
	},

    set_loading: function() {
        $("#search-go").hide();
        $('#search-go-loading').show();
        $('#search-results').hide();
        this.clearResults();
    },

    clearResults: function() {
        $('#resultsContainer').html("");
    },

    // we just got results - set them
    setResults: function(search_hash, search_spec, variants) {
        var that = this;
        that.search_spec = search_spec;
        that.search_hash = search_hash;
        that.variants = variants;
        that.variants_view = new CohortVariantSearchResultsView({
            hbc: that,
            variants: that.variants,
            cohort: that.cohort,
        });

        that.redisplay_results();

        $.scrollTo($('#results-container'), 300);
        that.showResults();
    },

    /*
     Collect state info and call the appropriate search function (which will determine request params)
     Each inheritance datatype has a separate search func
     */
    run_search: function() {
        var that = this;
        var search_spec = that.search_form_view.get_search_spec();
        that.set_loading();

        var postData = {
            project_id: that.cohort['project_id'],
            cohort_id: that.cohort['cohort_id'],
            variant_filter: JSON.stringify(search_spec.variant_filter.toJSON()),
            quality_filter: JSON.stringify(search_spec.quality_filter.toJSON()),
        };

        var url = '/api/cohort-variant-search';
        postData.inheritance_mode = search_spec.inheritance_mode;
        postData.search_mode = search_spec.inheritance_mode ? 'standard_inheritance' : 'all_variants';


        $.get(url, postData, function(data) {
            if (data.is_error) {
                alert('There was an error with your search: ' + data.error);
                $('#search-go-loading').hide();
                that.clearResults();
            } else {
                that.setResults(data.search_hash, search_spec, data.variants);
                that.navigate('search/'+data.search_hash+'/results');
            }
        });
    },

    bind_to_dom: function() {
        var that = this;
        $('#search-form-container').html(this.search_form_view.render().el);
        $('#run-search').on('click', function() {
            that.run_search();
        });
    },

    redisplay_results: function() {
        $('#results-container').html(this.variants_view.render().el);
    },

});


$(document).ready(function() {

    var hbc = new CohortVariantSearchHBC({
        dictionary: DICTIONARY,
        project_options: PROJECT_OPTIONS,
        cohort: COHORT,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});




