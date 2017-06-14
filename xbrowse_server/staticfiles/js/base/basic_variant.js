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
        this.family_has_bam_file_paths = options.family_has_bam_file_paths;
        this.show_tag_details = options.show_tag_details; // whether to show who added the tag and when

        this.individual_map = {};
        for (var i=0; i<this.individuals.length; i++) {
            this.individual_map[this.individuals[i].indiv_id] = this.individuals[i];
        }

        this.reference_populations = this.hbc.project_options.reference_populations;

        this.actions = [];
        if (this.allow_saving) {
            this.actions.push({action: 'add_note',  name: 'Note'});
            this.actions.push({action: 'edit_tags', name: 'Tags'});
        }

        this.highlight_background = false;
        if (this.show_variant_notes && this.variant.extras.in_clinvar) {
	        if(this.variant.extras.in_clinvar[1].indexOf("pathogenic") != -1) {
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
            actions: this.actions,
            genotype_family_id: this.genotype_family_id,
            allow_saving: this.allow_saving,
            show_gene_search_link: this.show_gene_search_link,
            project_id: this.individuals && this.individuals.length > 0? this.individuals[0].project_id : "",
            family_has_bam_file_paths: this.family_has_bam_file_paths,
            show_tag_details: this.show_tag_details,
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
                this.hbc.add_or_edit_family_variant_note(that.variant, that.context_obj, function(variant) {
                    that.variant = variant;
                    that.render();
                }, null);
            }
        }
        else if (a == 'edit_tags') {
            if (this.context == 'family') {
                this.hbc.edit_family_variant_tags(that.variant, that.context_obj, function(variant) {
                    that.variant = variant;
                    that.render();
                });
            }
        }
    },

    gene_info: function(event) {
        var gene_id = $(event.target).data('gene_id');
        this.hbc.gene_info(gene_id);
    },

    annotation_link: function(event) {
        this.hbc.variant_info(this.variant);
    },

    view_reads: function(event) {
        if(!this.hbc.igv_view) {
            this.hbc.igv_view = new IgvView({
                individuals: this.individuals
            });
        }

        var igv_view = this.hbc.igv_view;
        var locus = this.variant.chr+':'+(this.variant.pos - 300) + "-"+(this.variant.pos + 300);
        if(igv_view.$el.is(':visible')) {
            if(this.el.contains(igv_view.el)) {
                igv_view.$el.hide();
            } else {
                this.$el.append(igv_view.el);
                igv_view.jump_to_locus(locus);
                $("html, body").animate({ scrollTop: $('.igv-container').offset().top }, 1000);
            }
        } else {
            if(!this.el.contains(igv_view.el)) {
              this.$el.append(igv_view.el);
            }
            igv_view.$el.show();
            igv_view.jump_to_locus(locus);
            $("html, body").animate({ scrollTop: $('.igv-container').offset().top }, 1000);
        }
    },

    edit_variant_note: function(event) {
        var note_id = $(event.currentTarget).attr('data-target');
        var that = this;
        this.hbc.add_or_edit_family_variant_note(that.variant, that.context_obj, function(variant) {
            that.variant = variant;
            that.render();
        }, note_id);
    },

    delete_variant_note: function(event) {
        if( confirm("Are you sure you want to delete this note? ") != true ) {
            event.preventDefault();
            if(event.stopPropagation){
                event.stopPropagation();
            }
            event.cancelBubble=true;
            return;
        } else {
            var that = this;
            var note_id = $(event.currentTarget).attr('data-target');
            $.get("/api/delete-variant-note/"+note_id,
                function(data) {
                    if (data.is_error) {
                        alert('Error: ' + data.error);
                    } else {
                        for(var i = 0; i < that.variant.extras.family_notes.length; i+=1) {
                            var n = that.variant.extras.family_notes[i];
                            if(n.note_id == note_id) {
                                that.variant.extras.family_notes.splice(i, 1);
                                break;
                            }
                        };
                        that.render();
                    }
                }
            );
        }
    }
});
