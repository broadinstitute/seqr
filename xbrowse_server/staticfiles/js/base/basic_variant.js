window.BasicVariantView = Backbone.View.extend({

    className: 'basicvariant-container',

    initialize: function(options) {

        // required
        this.hbc = options.hbc;
        this.variant = options.variant;

        // optional
        this.context = options.context || null;  // generic link to the context of this table - family, project, individual
        this.context_obj = options.context_obj || null;
        this.show_genotypes = options.show_genotypes || false;
        this.individuals = options.individuals || [];
        this.leftview = options.leftview || null;
        this.show_gene = options.show_gene != false;
        this.genotype_family_id = options.genotype_family_id || false;
        this.allow_saving = options.allow_saving || false;
        this.show_igv_links = options.show_igv_links || false;
        this.show_gene_search_link = options.show_gene_search_link || false;
        this.actions = options.actions || [];  // options.actions should actually be 'other_actions'
        this.show_variant_notes = options.show_variant_notes;

        this.individual_map = {};
        for (var i=0; i<this.individuals.length; i++) {
            this.individual_map[this.individuals[i].indiv_id] = this.individuals[i];
        }

        this.reference_populations = this.hbc.project_options.reference_populations;

        if (this.allow_saving) {
            this.actions.push({
                action: 'add_note',
                name: 'Note',
            });
            this.actions.push({
                action: 'edit_tags',
                name: 'Tags',
            });
            this.actions.push({
                action: 'mark_causal',
                name: 'Mark Causal',
            });
        }
        this.has_tags = false;
        if (this.show_variant_notes && this.variant.extras.family_tags && this.variant.extras.family_tags.length > 0) {
            this.has_tags = true;
        }

        this.highlight = false;
        if (this.show_variant_notes && this.variant.extras.family_notes && this.variant.extras.family_notes.length > 0) {
            this.highlight = true;
        }
        if (this.show_variant_notes && this.variant.extras.is_causal) {
            this.highlight = true;
        }
        if (this.show_variant_notes && this.variant.extras.in_clinvar) {
            this.highlight = true;
        }

    },

    render: function() {
        $(this.el).html(this.template( {
            utils: utils,
            dictionary: this.hbc.dictionary,
            show_gene: this.show_gene,
            leftview: this.leftview,
            variant: this.variant,
            individuals: this.individuals,
            individual_map: this.individual_map,
            reference_populations: this.reference_populations,
            show_genotypes: this.show_genotypes,
            actions: this.actions,
            highlight: this.highlight,
            genotype_family_id: this.genotype_family_id,
            allow_saving: this.allow_saving,
            has_tags: this.has_tags,
            show_gene_search_link: this.show_gene_search_link,
            project_id: this.individuals[0].project_id, 
        }));
        if (this.highlight) {
            this.$el.addClass('highlighted');
        }
        utils.initializeHovers(this);
        if (this.leftview) {
            this.$('.leftview').html(this.leftview.render().el);
        }
        return this;
    },

    events: {
        "click a.action": "action",
        "click a.highlight-more": "highlight_more",
        "click a.gene-link": "gene_info",
        "click a.annotation-link": "annotation_link",
    },

    template: _.template($('#tpl-basic-variant').html()),

    action: function(event) {
        var that = this;
        var a = $(event.target).data('action');

        var after_finished = function(variant) {
            that.variant = variant;
            that.render();
            that.trigger('updated', variant);
        };
        if (a == 'add_note') {
            if (this.context == 'family') {
                this.hbc.add_family_variant_note(that.variant, that.context_obj, after_finished);
            }
        }
        else if (a == 'edit_tags') {
            if (this.context == 'family') {
                this.hbc.edit_family_variant_tags(that.variant, that.context_obj, after_finished);
            }
        } else if (a == 'mark_causal') {
            var url = URL_PREFIX + 'project/' + that.context_obj.get('project_id');
            url += '/family/' + that.context_obj.get('family_id');
            url += '/cause?variant=' + that.variant.xpos;
            url += '|' + that.variant.ref;
            url += '|' + that.variant.alt;
            window.open(url);
        }
        this.trigger(a, this.variant);
    },

    highlight_more: function(event) {
        var view = new VariantFlagsView({flags: this.variant.extras.family_notes});
        this.hbc.pushModal('', view);
    },

    gene_info: function(event) {
        var gene_id = $(event.target).data('gene_id');
        this.hbc.gene_info(gene_id);
    },

    annotation_link: function(event) {
        this.hbc.variant_info(this.variant);
    },

});