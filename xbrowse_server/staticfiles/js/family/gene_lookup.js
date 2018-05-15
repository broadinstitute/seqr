var GeneLookupFormView = Backbone.View.extend({

    initialize: function(options) {
        this.select_gene_view = new SelectGeneView();
    },

    template: _.template($('#tpl-gene-lookup').html()),

    render: function() {
        var that = this;
        $(this.el).html(this.template({}));
        this.$('.searchbox-container').html(that.select_gene_view.render().el);
        that.select_gene_view.on('gene-selected', function(gene_id) {
            that.trigger('gene-selected', gene_id);
        });
        return this;
    },

    set_enabled: function(is_enabled) {
        this.select_gene_view.set_enabled(is_enabled);
    }

});


var FamilyGeneLookupHBC = HeadBallCoach.extend({

    initialize: function(options) {
        this.family = options.family;
        this.search_form = new GeneLookupFormView();
        this.search_controls = new SearchControlsView({
            show_button: false,
        });
    },

    bind_to_dom: function() {
        var that = this;
        $('#form-container').html(this.search_form.render().el);
        that.search_form.on('gene-selected', function(gene_id) {
            that.run_search(gene_id);
        });
        $('#search-controls-container').html(this.search_controls.render().el);
    },

    run_search: function(gene_id) {
        var that = this;
        that.search_controls.set_loading();
        that.search_form.set_enabled(false);

        var url = '/api/family-gene-lookup';
        var post_data = {
            project_id: that.family.get('project_id'),
            family_id: that.family.get('family_id'),
            gene_id: gene_id,
        };

        $.get(url, post_data, function(data) {
            if (data.is_error) {
                alert('There was an error with your search: ' + data.error);
            } else {
                var results_view = new GeneDiagnosticView({
                    gene_diagnostic_info: data.family_gene_data,
                    data_summary: data.data_summary,
                    family: that.family,
                    hbc: that,
                });
                $('#results-container').html(results_view.render().el);
                that.search_controls.set_enabled();
                that.search_form.set_enabled(true);
            }
        });

    },
});


$(document).ready(function() {

    var hbc = new FamilyGeneLookupHBC({
        family: new Family(FAMILY),
    });

    hbc.bind_to_dom();
    Backbone.history.start();
    window.hbc = hbc;

});







