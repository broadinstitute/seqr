

var DiagnosticSearchFormView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.gene_lists = options.gene_lists;

        this.select_variants_view = new SelectVariantsView({
            hbc: this.hbc,
        });
        this.select_multiple_genes_container = new SelectMultipleGenesView({
            hbc: this.hbc,
        });
    },

    template: _.template($('#tpl-diagnostic-search-form').html()),

    render: function() {
        $(this.el).html(this.template({
            gene_lists: this.gene_lists,
        }));
        this.$('#select-variants-container').html(this.select_variants_view.render().el);
        this.$('#select-multiple-genes-container').html(this.select_multiple_genes_container.render().el);
        return this;
    },

    get_search_spec: function() {
       return {
           variant_filter: this.select_variants_view.getVariantFilter(),
           gene_list_slug: this.$('input[name=gene_list]:checked').val(),
       }
    },

});


var DiagnosticSearchResultsView = Backbone.View.extend({

    initialize: function(options) {
        this.family = options.family;
        this.hbc = options.hbc;
        this.gene_diagnostic_info_list = options.gene_diagnostic_info_list;
        this.gene_list_info = options.gene_list_info;
        this.data_summary = options.data_summary;
        var gene_list_info_d = {}
        _.each(this.gene_list_info.genes, function(g) {
            gene_list_info_d[g.gene_id] = g
        });
        this.gene_list_info_d = gene_list_info_d;
    },

    template: _.template($('#tpl-diagnostic-search-results').html()),

    render: function() {
        var that = this;
        $(this.el).html(this.template());

        _.each(this.gene_diagnostic_info_list, function(gene_diagnostic_info) {
            var view = new GeneDiagnosticView({
                hbc: that.hbc,
                gene_diagnostic_info: gene_diagnostic_info,
                family: that.family,
                gene_list_info_item: that.gene_list_info_d[gene_diagnostic_info.gene_id],
                data_summary: that.data_summary,
            });
            that.$('#results').append(view.render().el);
        });
        return this;
    }
});


var DiagnosticSearchHBC = HeadBallCoach.extend({

    initialize: function(options) {
        this.gene_lists = options.gene_lists;
        this.family = options.family;
        this.search_form = new DiagnosticSearchFormView({
            hbc: this,
            gene_lists: this.gene_lists,
        });
        this.search_controls = new SearchControlsView({});
    },

    bind_to_dom: function() {
        $('#form-container').html(this.search_form.render().el);
        $('#search-controls-container').html(this.search_controls.render().el);
        this.search_controls.on('search', this.run_search, this);
    },

    run_search: function() {
        var that = this;
        this.search_controls.set_loading();
        var search_spec = that.search_form.get_search_spec();

        var url = '/api/diagnostic-search';
        var post_data = {
            project_id: that.family.get('project_id'),
            family_id: that.family.get('family_id'),
            gene_list_slug: search_spec.gene_list_slug,
            variant_filter: JSON.stringify(search_spec.variant_filter.toJSON()),
        };

        $.get(url, post_data, function(data) {
            if (data.is_error) {
                alert('There was an error with your search: ' + data.error);
            } else {
                var results_view = new DiagnosticSearchResultsView({
                    gene_diagnostic_info_list: data.gene_diagnostic_info_list,
                    gene_list_info: data.gene_list_info,
                    data_summary: data.data_summary,
                    family: that.family,
                    hbc: that,
                });
                $('#results-container').html(results_view.render().el);
            }
            that.search_controls.set_enabled();
        });

    },

});


$(document).ready(function() {

    var hbc = new DiagnosticSearchHBC({
        project_options: PROJECT_OPTIONS,
        gene_lists: GENE_LISTS,
        family: new Family(FAMILY),
    });

    hbc.bind_to_dom();
    Backbone.history.start();
    window.hbc = hbc;

});







