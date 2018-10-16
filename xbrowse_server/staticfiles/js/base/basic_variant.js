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
        this.show_gene = options.show_gene || false;
        this.genotype_family_id = options.genotype_family_id || false;
        this.allow_saving = options.allow_saving || false;
        this.show_gene_search_link = options.show_gene_search_link || false;
        this.show_variant_notes = options.show_variant_notes;
        this.family_read_data_is_available = options.family_read_data_is_available;
        this.show_tag_details = options.show_tag_details; // whether to show who added the tag and when

        this.individual_map = {};
        for (var i=0; i<this.individuals.length; i++) {
            this.individual_map[this.individuals[i].indiv_id] = this.individuals[i];
        }

        this.reference_populations = this.hbc.project_options.reference_populations;

        this.highlight_background = false;
        if (this.show_variant_notes && this.variant.extras.clinvar_clinsig) {
	        if(this.variant.extras.clinvar_clinsig.indexOf("pathogenic") != -1) {
		        this.highlight_background = true;
	        }
        }
    },

    render: function() {
        $(this.el).html(this.template({
            utils: utils,
            dictionary: this.hbc.dictionary,
            show_gene: this.show_gene,
            leftview: this.leftview,
            variant: this.variant,
            individuals: this.individuals,
            individual_map: this.individual_map,
            reference_populations: this.reference_populations,
            show_genotypes: this.show_genotypes,
            actions: this.allowed_actions(),
            genotype_family_id: this.genotype_family_id,
            allow_saving: this.allow_saving,
            show_gene_search_link: this.show_gene_search_link,
            project_id: this.individuals && this.individuals.length > 0? this.individuals[0].project_id : "",
            family_read_data_is_available: this.family_read_data_is_available,
            show_tag_details: this.show_tag_details,
            allow_functional: this.allow_functional(),
        }));

        if (this.highlight_background) {
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
        "click a.gene-link": "gene_info",
        "click a.annotation-link": "annotation_link",
        "click a.view-reads": "view_reads",
        "click a.delete-variant-note": "delete_variant_note",
        "click a.edit-variant-note": "edit_variant_note",
    },

    template: _.template($('#tpl-basic-variant').html()),

    action: function(event) {
        var that = this;
        var a = $(event.target).data('action');

        if (a == 'add_note') {
            if (this.context == 'family') {
                this.hbc.add_or_edit_family_variant_note(that.variant, that.context_obj, function(data) {
                    that.variant.extras.family_notes = data.notes;
                    that.render();
                }, null);
            }
        }
        else if (a == 'edit_tags') {
            if (this.context == 'family') {
                this.hbc.edit_family_variant_tags(that.variant, that.context_obj, function(data) {
                    that.variant.extras.family_tags = data.tags;
                    that.render();
                });
            }
        }
        else if (a == 'edit_functional_data') {
            if (this.context == 'family') {
                this.hbc.edit_family_functional_data(that.variant, that.context_obj, function(data) {
                    that.variant.extras.family_functional_data = data.functional_data;
                    that.render();
                });
            }
        }
    },

    allow_functional: function() {
        return this.hbc.project_options.functional_data && this.variant.extras.family_tags && this.variant.extras.family_tags.find((el) => el.is_discovery_tag)
    },

    allowed_actions: function() {
      if (this.allow_saving) {
        var actions = [{action: 'add_note', name: 'Note'}, {action: 'edit_tags', name: 'Tags'}]
        if (this.allow_functional()) {
          actions.push({action: 'edit_functional_data', name: 'Fxnl'});
        }
        return actions;
      } else {
          return [];
      }
    }
    ,

    gene_info: function(event) {
        var gene_id = $(event.target).data('gene_id');
        this.hbc.gene_info(gene_id);
    },

    annotation_link: function(event) {
        this.hbc.variant_info(this.variant);
    },

    view_reads: function(event) {
        var locus = this.variant.chr+':' + (this.variant.pos - 100) + "-" + (this.variant.pos + 100);

        if(!this.hbc.igv_view) {
            this.hbc.igv_view = new IgvView({
              individuals: this.individuals,
              locus: locus,
              genome_version: this.variant.extras.genome_version || "37",
            });
        }

        var igv_view = this.hbc.igv_view;
        if(igv_view.$el.is(':visible')) {
            if(this.el.contains(igv_view.el)) {
                igv_view.$el.hide();
            } else {
                this.$el.append(igv_view.el);
                $("html, body").animate({ scrollTop: $('.igv-container').offset().top }, 1000);
		igv_view.jump_to_locus(locus);		
            }
        } else {
            if(!this.el.contains(igv_view.el)) {
              this.$el.append(igv_view.el);
            }
            igv_view.$el.show();
            $("html, body").animate({ scrollTop: $('.igv-container').offset().top }, 1000);
	    igv_view.jump_to_locus(locus);
        }
    },

    edit_variant_note: function(event) {
        var note_id = $(event.currentTarget).attr('data-target');
        var that = this;
        this.hbc.add_or_edit_family_variant_note(that.variant, that.context_obj, function(data) {
            that.variant.extras.family_notes = data.notes;
            that.render();
        }, note_id);
    },

    delete_variant_note: function(event) {
        var that = this;
        var note_id = $(event.currentTarget).attr('data-target');
        this.hbc.delete_note(note_id, 'variant', this.variant.extras.family_notes, function(notes) {
            that.variant.extras.family_notes = notes;
            that.render();
        });
    }
});
