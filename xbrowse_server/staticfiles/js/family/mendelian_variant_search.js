

/*
Subview for selecting a custom genotype inheritance view
TODO: need to refactor this to only show the genotype form; prefill box should be a separate view
 */
window.SelectAlleleCountFilterView = Backbone.View.extend({

    initialize: function(options) {
        this.individuals = options.individuals;
    },

    template: _.template($('#tpl-choose-allele-count-filter').html()),

    render: function() {
        $(this.el).html(this.template({
            individuals: this.options.individuals,
        }));
        return this;
    },

    set_filter: function(filter) {
        this.render();
        if (filter.affected_gte != undefined) this.$('#affected_gte').val(filter.affected_gte);
        if (filter.affected_lte != undefined) this.$('#affected_lte').val(filter.affected_lte);
        if (filter.unaffected_gte != undefined) this.$('#unaffected_gte').val(filter.unaffected_gte);
        if (filter.unaffected_lte != undefined) this.$('#unaffected_lte').val(filter.unaffected_lte);
    },

    get_filter: function() {
        var filter = {};
        var affected_gte = parseInt(this.$('#affected_gte').val());
        if (!isNaN(affected_gte)) filter.affected_gte = affected_gte;
        var affected_lte = parseInt(this.$('#affected_lte').val());
        if (!isNaN(affected_lte)) filter.affected_lte = affected_lte;
        var unaffected_gte = parseInt(this.$('#unaffected_gte').val());
        if (!isNaN(unaffected_gte)) filter.unaffected_gte = unaffected_gte;
        var unaffected_lte = parseInt(this.$('#unaffected_lte').val());
        if (!isNaN(unaffected_lte)) filter.unaffected_lte = unaffected_lte;
        return filter;
    },
});


/*
Parent view that encapsulates the whole search form - everything down to the search button
Provides HBC with a search_spec, or can be loaded with one
A search_spec is just a dict with keys:
- search_mode
- inheritance_filter (if custom inheritance)
- inheritance_mode (if standard inheritacne)
- variant_filter
- quality_filter

 */
var MendelianVariantSearchForm = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family = options.family;
        this.dictionary = this.hbc.dictionary;
        this.family_genotype_filters = options.family_genotype_filters;

        this.choose_standard_inheritance_view = new ChooseStandardInheritanceView({
            inheritance_methods: this.dictionary.standard_inheritances,
        });

        this.chooseGenotypeFilterView = new ChooseGenotypeFilterView({
            family: this.family.toJSON(),
            genotypeOptions: this.dictionary.genotype_options,
            burdenFilterOptions: this.dictionary.burden_filter_options,
            familyGenotypeFilters: this.family_genotype_filters,
        });

        this.select_allele_count_filter = new SelectAlleleCountFilterView({
            individuals: this.family.get('individuals'),
        });

        this.select_variants_view = new SelectVariantsView({
            hbc: this.hbc,
        });

        this.select_quality_filter_view = new SelectQualityFilterView({
            qualityFilter: this.quality_filter,
            default_quality_filters: this.dictionary.default_quality_filters,
        });
    },

    template: _.template($('#tpl-mendelian-variant-search-form').html()),

    render: function() {
        $(this.el).html(this.template());

        this.choose_standard_inheritance_view.setElement(this.$('#standard_inheritance-inner')).render();
        this.chooseGenotypeFilterView.setElement(this.$('#custom_inheritance-inner')).render();
        this.select_allele_count_filter.setElement(this.$('#allele_count-inner')).render();
        this.select_variants_view.setElement(this.$('#tplholder-select-variants')).render();
        this.select_quality_filter_view.setElement(this.$('#select-quality-filter-container')).render();

        this.set_search_mode('standard_inheritance');
        utils.initializeHovers(this);

        return this;
    },

    events: {
        "click a.inheritance-pill-a": "inheritance_pill_clicked",
    },

    inheritance_pill_clicked: function(event) {
        var search_mode = $(event.target).parent().data('search_mode');
        this.set_search_mode(search_mode);
    },

    get_search_mode: function() {
        return this.search_mode;
    },

    set_search_mode: function(search_mode) {
        this.$('.search-type-container').hide();
        this.$('#'+search_mode+'-container').show();
        this.$('.inheritance-pill-li').removeClass('active');
        this.$('.inheritance-pill-li[data-search_mode="'+search_mode+'"]').addClass('active');
        this.search_mode = search_mode;
    },

    get_search_spec: function() {
        var spec = {
            search_mode: this.get_search_mode(),
            variant_filter: this.select_variants_view.getVariantFilter(),
            quality_filter: this.select_quality_filter_view.getQualityFilter(),
        };
        if (spec.search_mode == 'standard_inheritance') {
            spec.inheritance_mode = this.choose_standard_inheritance_view.get_standard_inheritance();
        } else if (spec.search_mode == 'custom_inheritance') {
            spec.inheritance_filter = this.chooseGenotypeFilterView.getGenotypes();
        } else if (spec.search_mode == 'allele_count') {
            spec.allele_count_filter = this.select_allele_count_filter.get_filter();
        } else if (spec.search_mode == 'all_variants') {

        }
        else {
            alert('Error 81925')
        }
        return spec;
    },

    // fill out form fields from the search spec
    load_search_spec: function(search_spec) {

        // clear everything first
        this.render();

        if (search_spec.search_mode == 'standard_inheritance') {
            this.choose_standard_inheritance_view.set_standard_inheritance(search_spec.inheritance_mode);
        } else if (search_spec.search_mode == 'custom_inheritance') {
            this.chooseGenotypeFilterView.drawFromFilter(search_spec.genotype_inheritance_filter);
        } else if (search_spec.search_mode == 'gene_burden') {
            this.chooseGenotypeFilterView.drawFromFilter(search_spec.burden_filter);
        } else if (search_spec.search_mode == 'allele_count') {
            this.select_allele_count_filter.set_filter(search_spec.allele_count_filter);
        }

        // don't need to do anything for all_variants
        this.set_search_mode(search_spec.search_mode);

        if (search_spec.variant_filter != undefined) {
            this.select_variants_view.loadFromVariantFilter(search_spec.variant_filter);
        } else {
            this.select_variants_view.loadFromVariantFilter({});
        }

        if (search_spec.quality_filter != undefined) {
            this.select_quality_filter_view.loadFromQualityFilter(search_spec.quality_filter);
        }
    },

    get_suggested_inheritance: function() {
        return this.choose_standard_inheritance_view.get_standard_inheritance();
    }

});


var MendelianVariantSearchResultsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.variants = options.variants;
        this.family = options.family;
        this.show_gene_search_link = options.show_gene_search_link;
    },

    template: _.template($('#tpl-mendelian-variant-search-results').html()),

    events: {
        'click .download-csv': 'download_csv',
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            num_variants: that.variants.length,
        }));

        if (that.variants.length > 0) {
            var variants_view = new BasicVariantsTable({
                hbc: that.hbc,
                context: 'family',
                context_obj: that.family,
                variants: that.variants,
                show_genotypes: true,
                individuals: that.family.individuals_with_variant_data(),
                allow_saving: true,
                reference_populations: that.hbc.project_options.reference_populations,
                show_gene_search_link: that.show_gene_search_link,
                show_variant_notes: true,
            });
            this.$('#variants-table-container').html(variants_view.render().el);
        }
        return this;
    },

    download_csv: function() {
        this.hbc.download_csv();
    },
});


var MendelianVariantSearchHBC = HeadBallCoach.extend({

    initialize: function(options) {

        this.family = options.family;

        // should we show IGV links in results displays?
        // true if any indivs in have BAM files
        // TODO: should be something like any() to use here...offline now

        this.show_gene_search_link = options.show_gene_search_link || false;
        this.family_has_bam_file_paths = false;

        var that = this;
        _.each(this.family.individuals_with_variant_data(), function(indiv) {
            if (indiv.has_bam_file_path) {
                that.family_has_bam_file_paths = true;
            }
        });

        this.search_form_view = new MendelianVariantSearchForm({
            hbc: this,
            family: this.family,
            family_genotype_filters: options.family_genotype_filters,
        });
    },

    routes: {
        "": "base",
        "search/:search_hash/results": "searchResults", // load search then fetch results
    },

    // route - clean page
    base: function() {
        this.resetModal();
        //if search spec has been saved using cookies, load it
        var search_spec = Cookies.getJSON('search_spec');
        if(search_spec) {
            this.search_form_view.load_search_spec(search_spec);
        }
    },

    // route - show search results for search_hash (a string hash)
    searchResults: function(search_hash) {
        var that = this;
        that.resetModal();
        that.set_loading();

        // API call to get original search and results
        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            search_hash: search_hash,
        };

        $.get(URL_PREFIX + 'api/mendelian-variant-search-spec', postData, function(data) {
            if (!data.is_error) {
                that.search_form_view.load_search_spec(data.search_spec);  // form controls
                that.setResults(search_hash, data.search_spec, data.variants);  // and results
            } else {
                alert('error 1983409');
            }
        });
    },

    showResults: function() {
		$("#run-search").show();
		$('#search-loading').hide();
	},

	showNoSearch: function() {
		$('#search-results').hide();
	},

    set_loading: function() {
        $("#run-search").hide();
        $('#search-loading').show();
        $('#results-container').html("");
    },

    // we just got results - set them
    setResults: function(search_hash, search_spec, variants) {
        var that = this;
        that.search_spec = search_spec;
        Cookies.set('search_spec', search_spec);
        //if search spec has been saved, load it
        that.search_hash = search_hash;
        that.variants = variants;
        that.variants_view = new MendelianVariantSearchResultsView({
            hbc: that,
            variants: that.variants,
            family: that.family,
            show_gene_search_link: that.show_gene_search_link,
        });

        that.redisplay_results();

        $.scrollTo($('#results-container'), 300);
        that.showResults();
    },

    /*
    Search button was clicked - initiate a new search
     */

    /*
    TODO: We already create a search_spec dict on the client - ideally we’d just send that to server
    But right now we have to submit each param individually - that’s awkward
    We need a method on the server that just parses search_spec dict - and throws informative errors
    I suspect this should be combined with a MendelianVariantSearchSpec class

    A bigger problem is that search_spec doesn't mean the same thing on server + client - see "gene_burden"
    Specifically, there are 4 options on the client, but 5 options on the server
     */
    run_search: function() {
        var that = this;

        var search_spec = that.search_form_view.get_search_spec();
        that.set_loading();

        // these things are the same regardless of search mode
        var url = URL_PREFIX + 'api/mendelian-variant-search';
        var post_data = {
            project_id: that.family.get('project_id'),
            family_id: that.family.get('family_id'),
            variant_filter: JSON.stringify(search_spec.variant_filter.toJSON()),
            quality_filter: JSON.stringify(search_spec.quality_filter.toJSON()),
        };

        if (search_spec.search_mode == 'standard_inheritance') {
            post_data.search_mode = 'standard_inheritance';
            post_data.inheritance_mode = search_spec.inheritance_mode;
        }

        else if (search_spec.search_mode == 'custom_inheritance') {

            // make sure doesn't combine genotype and burden
            var has_genotype = false;
            var has_burden = false;
            for (var indiv_id in search_spec.inheritance_filter) {
                var slug = search_spec.inheritance_filter[indiv_id];
                if (_.find(that.dictionary.genotype_options, function(x) { return x.slug == slug }) != undefined) has_genotype = true;
                if (_.find(that.dictionary.burden_filter_options, function(x) { return x.slug == slug }) != undefined) has_burden = true;
            }
            if (has_genotype && has_burden) {
                alert("Please do not combine genotype and gene-based options in the search filter. We have not decided how to process this.");
                that.showResults();
                return;
            }

            if (has_genotype) {
                post_data.search_mode = 'custom_inheritance';
                post_data.genotype_filter = JSON.stringify(search_spec.inheritance_filter);
            } else {
                post_data.search_mode = 'gene_burden';
                post_data.burden_filter = JSON.stringify(search_spec.inheritance_filter);
            }
        }

        else if (search_spec.search_mode == 'allele_count') {
            post_data.search_mode = 'allele_count';
            post_data.allele_count_filter = JSON.stringify(search_spec.allele_count_filter);
        }

        else if (search_spec.search_mode == 'all_variants') {
            post_data.search_mode = 'all_variants';
        }

        $.get(url, post_data, function(data) {
            if (data.is_error) {
                alert('There was an error with your search: ' + data.error);
                that.showResults();
            } else {
                that.setResults(data.search_hash, search_spec, data.variants);
                that.navigate('search/'+data.search_hash+'/results');
            }
        });
    },

    bind_to_dom: function() {
        var that = this;
        $('#search-form-container').html(this.search_form_view.render().el);
        $('#search-loading').hide();
        $('#run-search').on('click', function() {
            that.run_search();
        });
    },

    variant_info: function(variant) {
        var that = this;
        var view = new AnnotationDetailsView({
            variant: variant
        });
        that.pushModal("title", view);
    },

    get_suggested_inheritance: function() {
        return this.search_form_view.ge
    },

    redisplay_results: function() {
        $('#results-container').html(this.variants_view.render().el);
    },

    download_csv: function() {
        var params = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            search_hash: this.search_hash,
            return_type: 'csv',
        };
        window.location.href = URL_PREFIX + 'api/mendelian-variant-search-spec?' + $.param(params);
    },

});


$(document).ready(function() {

    var hbc = new MendelianVariantSearchHBC({
        family: new Family(FAMILY),
        family_genotype_filters: FAMILY_GENOTYPE_FILTERS,
        show_gene_search_link: SHOW_GENE_SEARCH_LINK,
    });


    hbc.bind_to_dom();
    window.hbc = hbc;  // remove
    Backbone.history.start();
});







