
var CombineMendelianFamiliesForm = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family_group = options.family_group;
        this.dictionary = this.hbc.dictionary;

    	this.inheritance_view = new ChooseStandardInheritanceView({
            inheritance_methods: this.dictionary.standard_inheritances,
        });

        this.select_variants_view = new SelectVariantsView({
            hbc: this.hbc,
        });

        this.select_quality_filter_view = new SelectQualityFilterView({
            qualityFilter: this.quality_filter,
            default_quality_filters: this.dictionary.default_quality_filters,
        });
    },

    template: _.template($('#tpl-combine-mendelian-families-form').html()),

    render: function(event) {
        var that = this;

        $(this.el).html(this.template());

        this.$('#select-inheritance-inner').html(that.inheritance_view.render().el);
        this.$('#tplholder-select-variants').html(that.select_variants_view.render().el);
        this.$('#select-quality-filter-container').html(that.select_quality_filter_view.render().el);

        return this;
    },

    get_search_spec: function() {
        var spec = {
            inheritance_mode: this.inheritance_view.get_standard_inheritance(),
            variant_filter: this.select_variants_view.getVariantFilter(),
            quality_filter: this.select_quality_filter_view.getQualityFilter(),
        };
        return spec;
    },

    // fill out form fields from the search spec
    load_search_spec: function(search_spec) {
        this.inheritance_view.set_standard_inheritance(search_spec.inheritance_mode);
        if (search_spec.variant_filter != undefined) {
            this.select_variants_view.loadFromVariantFilter(search_spec.variant_filter);
        } else {
            this.select_variants_view.loadFromVariantFilter({});
        }
        if (search_spec.quality_filter != undefined) {
            this.select_quality_filter_view.loadFromQualityFilter(search_spec.quality_filter);
        } else {
            this.select_quality_filter_view.loadFromQualityFilter({});
        }
    },

    // return string of what is wrong with this search
    // null if no errors
    get_search_error: function() {
        var spec = this.get_search_spec();
        if (!spec.inheritance_mode) {
            return "Inheritance mode is required."
        }
        return null;
    },
});


var CombineMendelianFamiliesResultsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.genes = options.genes;
        this.family_group = options.family_group;
    },

    template: _.template($('#tpl-combine-mendelian-families-results').html()),

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            genes: this.genes,
            family_group: this.family_group,
        }));

        this.$('.variants-table').dataTable({
            bPaginate: false,
            bFilter: false,
            bInfo: false,
            aaSorting: [],
        });

        utils.initializeHovers(this);

        return this;
    },

    events: {
        "click a.gene-link": "gene_info",
        "click a.view-variants": "view_variants",
        'click .download-csv': 'download_csv',
        'click .download-csv-variants': 'download_csv_variants',
    },

    gene_info: function(event) {
        var gene_id = $(event.target).data('gene_id');
        this.hbc.gene_info(gene_id);
    },

    view_variants: function(event) {
        var gene_id = $(event.target).data('gene_id');
        this.hbc.view_variants(gene_id);
    },

    download_csv: function() {
        this.hbc.download_csv(false);
    },

    download_csv_variants: function() {
        this.hbc.download_csv(true);
    },
});


var CombineMendelianFamiliesHBC = HeadBallCoach.extend({

    initialize: function(options) {

        // caller must provide these
        this.family_group = options.family_group;

        this.search_form_view = new CombineMendelianFamiliesForm({
            hbc: this,
            family_group: this.family_group,
        });

    },

    routes: {
        "": "base",
        "search/:search_hash/results": "cached_results", // load search then fetch results
    },

    // route - show search results for search_hash (a string hash)
    cached_results: function(search_hash) {
        var that = this;
        that.resetModal();
        that.set_loading();

        // API call to get original search and results
        var postdata = {
            project_id: this.family_group['project_id'],
            family_group: this.family_group['slug'],
            search_hash: search_hash,
        };

        $.get('/api/combine-mendelian-families-spec', postdata, function(data) {
            if (!data.is_error) {
                that.search_form_view.load_search_spec(data.search_spec);  // form controls
                that.set_results(search_hash, data.search_spec, data.genes);  // and results
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
    set_results: function(search_hash, search_spec, genes) {
        var that = this;
        that.search_spec = search_spec;
        that.search_hash = search_hash;
        that.genes = genes;
        that.variants_view = new CombineMendelianFamiliesResultsView({
            hbc: that,
            genes: that.genes,
            family_group: that.family_group,
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

        var error = that.search_form_view.get_search_error();
        if (error) {
            alert('Form error: '+error);
            return;
        }
        var search_spec = that.search_form_view.get_search_spec();

        that.set_loading();

        var url = '/api/combine-mendelian-families';
        var postData = {
            project_id: that.family_group.project_id,
            family_group: that.family_group.slug,
            inheritance_mode: search_spec.inheritance_mode,
            variant_filter: JSON.stringify(search_spec.variant_filter.toJSON()),
            quality_filter: JSON.stringify(search_spec.quality_filter.toJSON()),
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

    bind_to_dom: function() {
        var that = this;
        $('#search-form-container').html(this.search_form_view.render().el);
        $('#search-loading').hide();
        $('#run-search').on('click', function() {
            that.run_search();
        });
    },

    redisplay_results: function() {
        $('#results-container').html(this.variants_view.render().el);
    },

    view_variants: function(gene_id) {
        var that = this;
        this.push_modal_loading();
        var url = '/api/combine-mendelian-families-variants';
        var gene = _.find(that.genes, function(g) { return g.gene_id == gene_id});
        var postdata = {
            project_id: that.family_group.project_id,
            family_group: that.family_group.slug,
            family_tuple_list: JSON.stringify(gene.family_id_list),
            inheritance_mode: that.search_spec.inheritance_mode,
            variant_filter: JSON.stringify(that.search_spec.variant_filter),
            quality_filter: JSON.stringify(that.search_spec.quality_filter),
            gene_id: gene_id,
        };
        $.get(url, postdata, function(data) {
            if (data.is_error) {
                alert('There was an error with your search: ' + data.error);
            } else {
                var variants_by_family_view = new VariantsByFamilyView({
                    variants_by_family: data.variants_by_family,
                    hbc: that,
                    family_group: that.family_group,
                });
                that.replace_loading_with_view(variants_by_family_view);
            }
        });
    },

    download_csv: function(group_by_variants) {
        var params = {
            project_id: this.family_group.project_id,
            family_group: this.family_group.slug,
            search_hash: this.search_hash,
            return_type: 'csv',
        };

	if(group_by_variants) {
	    params['group_by_variants'] = true;
	}

        window.location.href = '/api/combine-mendelian-families-spec?' + $.param(params);
    },

});


$(document).ready(function() {

    var hbc = new CombineMendelianFamiliesHBC({
        dictionary: DICTIONARY,
        family_group: FAMILY_GROUP,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});







