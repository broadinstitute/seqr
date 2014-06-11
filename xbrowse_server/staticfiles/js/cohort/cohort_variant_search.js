var CohortVariantSearchForm = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.cohort = options.cohort;
        this.dictionary = this.hbc.dictionary;

    	this.select_inheritance_view = new CohortSelectGenotypesView({
            hbc: this.hbc,
            cohort: this.cohort,
            dictionary: this.dictionary,
            standardInheritances: this.dictionary.standard_inheritances,
            genotypeOptions: this.dictionary.genotype_options,
            burdenFilterOptions: this.dictionary.burden_filter_options,
	    });

        this.select_variants_view = new SelectVariantsView({
            hbc: this.hbc,
            project_options: this.hbc.project_options,
            variantFilter: this.variantFilter,
            qualityFilter: this.qualityFilter,
            familyStats: options.family_variant_stats,
            show_variant_stats: true,
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

        this.$('#tplholder-select-inheritance').html(that.select_inheritance_view.render().el);
        this.$('#tplholder-select-variants').html(that.select_variants_view.render().el);
        this.$('#select-quality-filter-container').html(that.select_quality_filter_view.render().el);

        return this;
    },

    get_search_spec: function() {
        var spec = {
            inheritance_filter: this.select_inheritance_view.getGenotypeFilter(),
            variant_filter: this.select_variants_view.getVariantFilter(),
            quality_filter: this.select_quality_filter_view.getQualityFilter(),
        };
        return spec;
    },

    // fill out form fields from the search spec
    load_search_spec: function(search_spec) {

        this.select_variants_view.loadFromVariantFilter(search_spec.variant_filter);
        this.select_quality_filter_view.loadFromQualityFilter(search_spec.quality_filter);

        if (search_spec.search_mode == 'custom_inheritance') {
            this.select_inheritance_view.setGenotypeFilter(search_spec.genotype_filter);
        } else if (search_spec.search_mode == 'gene_burden') {
            this.select_inheritance_view.setGenotypeFilter(search_spec.burden_filter);
        }
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
            family_variant_stats: options.family_variant_stats,
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

        $.get(URL_PREFIX + 'api/cohort-variant-search-spec', postData, function(data) {
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

        var filter = search_spec.inheritance_filter;

        // make sure doesn't combine genotype and burden
        var has_genotype = false;
        var has_burden = false;
        for (var indiv_id in filter) {
            var slug = filter[indiv_id];
            if (_.find(that.dictionary.genotype_options, function(x) { return x.slug == slug }) != undefined) has_genotype = true;
            if (_.find(that.dictionary.burden_filter_options, function(x) { return x.slug == slug }) != undefined) has_burden = true;
        }
        if (has_genotype && has_burden) {
            alert("Please do not combine genotype and gene-based options in the search filter. We have not decided how to process this.");
            that.showResults();
            return;
        }

        var postData = {
            project_id: that.cohort['project_id'],
            cohort_id: that.cohort['cohort_id'],
            variant_filter: JSON.stringify(search_spec.variant_filter.toJSON()),
            quality_filter: JSON.stringify(search_spec.quality_filter.toJSON()),
        };

        var url = URL_PREFIX + 'api/cohort-variant-search';
        if (has_genotype) {
            postData.search_mode = 'custom_inheritance';
            postData.genotype_filter = JSON.stringify(search_spec.inheritance_filter);
        } else {
            postData.search_mode = 'gene_burden';
            postData.burden_filter = JSON.stringify(search_spec.inheritance_filter);
        }

        $.get(url, postData, function(data) {
            if (data.is_error) {
                alert('There was an error with your search: ' + data.error);
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

    variant_info: function(variant) {
        var that = this;
        var view = new AnnotationDetailsView({
            variant: variant
        });
        that.pushModal("", view);
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
        family_variant_stats: COHORT_VARIANT_STATS,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});




