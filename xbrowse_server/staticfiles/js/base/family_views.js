window.FamiliesView = Backbone.View.extend({
    template: _.template($('#tpl-families').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.families = options.families;
        this.selectable = options.selectable == true;
        this.show_edit_links = options.show_edit_links == true;
        this.family_id_link = options.family_id_link != false;
        this.analysis_statuses = options.analysis_statuses;
    },
    events: {
        "click #select-all-families": "select_all",
        "click .family-checkbox": "select_one",
    },
    render: function() {
        $(this.el).html(this.template({
            families: this.families,
            analysis_statuses: this.analysis_statuses,
            selectable: this.selectable,
            family_id_link: this.family_id_link,
            project_spec: this.project_spec,
            show_edit_links: this.show_edit_links,
            show_case_review_status: this.show_case_review_status,
        }));
        this.$('.tablesorter').tablesorter();
        
        return this;
    },

    get_selected_family_ids: function() {
        var ret = [];
        this.$('.family-checkbox:checked').each(function(){ret.push($(this).data('family_id'))});
        return ret;
    },

    set_id_selected: function(family_id) {
        this.$('.family-checkbox[data-family_id="' + family_id + '"]').prop('checked', true);
        this.$('tr.family-row[data-family_id="' + family_id + '"]').addClass('row-checked');
    },

    set_id_deselected: function(family_id) {
        this.$('.family-checkbox[data-family_id="' + family_id + '"]').prop('checked', false);
        this.$('tr.family-row[data-family_id="' + family_id + '"]').removeClass('row-checked');
    },

    select_one: function(e) {
        var checked = $(e.target).is(':checked');
        var family_id = $(e.target).data('family_id');
        if (checked) {
            this.set_id_selected(family_id);
        } else {
            this.set_id_deselected(family_id);
        }
    },

    select_all: function(e) {
        var checked = $(e.target).is(':checked');
        for (var i=0; i<this.families.length; i++) {
            if (checked) this.set_id_selected(this.families[i].family_id);
            else this.set_id_deselected(this.families[i].family_id);
        }
    },

    select_with_phenotype: function(pheno_filter) {
        var that = this;
        if (pheno_filter.bool_val != true) {
            alert("You've encountered an annoying error - you can only select binary phenotypes of Yes, not No or Unknown. Sorry about that, will be fixed soon...");
            return;
        }
        var slug = pheno_filter.slug;
        _.each(this.families, function(family) {
            if (_.find(family.phenotypes, function(x){return x==slug})) {
                that.set_id_selected(family.family_id);
            }
        });
    },
});


// TODO: shouldn't be in family_views.js
var IndividualGeneCoverageView = Backbone.View.extend({

    template: _.template($('#tpl-indiv-gene-coverage').html()),

    className: 'indiv-gene-coverage',

    initialize: function(options) {
        this.individual = options.individual;
        this.coverage = options.coverage;
    },

    render: function() {
        $(this.el).html(this.template({
            coverage: this.coverage,
            individual: this.individual,
            utils: utils,
        }));
        return this;
    }

});


var GeneDiagnosticView = Backbone.View.extend({

    template: _.template($('#tpl-gene-diagnostic-info').html()),

    className: 'gene-diagnostic-view',

    initialize: function(options) {
        this.hbc = options.hbc;
        this.gene_diagnostic_info = options.gene_diagnostic_info;
        this.gene_list_info_item = options.gene_list_info_item || null; // todo: ugh rename this
        this.family = options.family;
        this.data_summary = options.data_summary;
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            gene_phenotype_summary: this.gene_diagnostic_info.gene_phenotype_summary,
            gene_sequencing_summary: this.gene_diagnostic_info.gene_sequencing_summary,
            variants: this.gene_diagnostic_info.variants,
            cnvs: this.gene_diagnostic_info.cnvs,
            family: this.family,
            gene_list_info_item: this.gene_list_info_item,
            data_summary: that.data_summary,
        }));
        if (this.gene_diagnostic_info.variants.length > 0) {
            this.$('.variants-container').html('<div class="basic-variants-list"></div>')
            _.each(this.gene_diagnostic_info.variants, function(variant) {
                var view = new BasicVariantView({
                    hbc: that.hbc,
                    variant: variant,
                    show_genotypes: true,
                    individuals: that.family.individuals_with_variant_data(),
                    show_gene: false,
                    allow_saving: true,
                    context_obj: that.family,
                    context: 'family',
                });
                that.$('.basic-variants-list').append(view.render().el);
            });
        } else {
            this.$('.variants-container').html('-');
        }
        return this;
    },
});

