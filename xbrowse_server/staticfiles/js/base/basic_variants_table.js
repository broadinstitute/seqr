window.BasicVariantsTable = Backbone.View.extend({

    initialize: function(options) {

        // required
        this.hbc = options.hbc;
        this.variants = options.variants;

        // optional
        this.context = options.context || null;  // generic link to the context of this table - family, project, individual
        this.context_obj = options.context_obj || null;
        this.show_header = options.show_header || false;
        this.show_genotypes = options.show_genotypes || false;
        this.individuals = options.individuals || [];
        this.allow_saving = options.allow_saving || false;
        this.show_variant_notes = options.show_variant_notes || false;
        this.show_igv_links = options.show_igv_links || false;
        this.show_gene_search_link = options.show_gene_search_link || false;
        this.bam_file_urls = options.bam_file_urls || {};

        this.indiv_id_list = [];
        this.indiv_id_to_family_id = {};
        for (var i=0; i<this.individuals.length; i++) {
            this.indiv_id_list.push(this.individuals[i].indiv_id);
            this.indiv_id_to_family_id[this.individuals[i].indiv_id] = this.individuals[i].family_id;
        }

        if (this.show_igv_links) {
            this.bam_file_urls_list = [];
            for (var i=0; i<this.indiv_id_list.length; i++) {
                var indiv_id = this.indiv_id_list[i];
                if (indiv_id in this.bam_file_urls) {
                    this.bam_file_urls_list.push(this.bam_file_urls[indiv_id]);
                }
            }
        }

    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({}));
        _.each(this.variants, function(variant) {
            var view = new BasicVariantView({
                hbc: that.hbc,
                variant: variant,
                context: that.context,
                context_obj: that.context_obj,
                show_genotypes: that.show_genotypes,
                show_gene_search_link: that.show_gene_search_link,
                individuals: that.individuals,
                allow_saving: that.allow_saving,
                show_variant_notes: that.show_variant_notes,
            });
            that.$('.basic-variants-list').append(view.render().el);
        });
        return this;
    },

    template: _.template($('#tpl-basic-variants-table').html()),

    hide_flags_hover: function(event) {
        $(event.target).popover('hide');
    },

    show_variant_in_igv: function(variant) {
        var file_spec = 'file=';
        for (var i=0; i<this.bam_file_urls_list.length; i++) {
            file_spec += this.bam_file_urls_list[i] + ','
        }
        file_spec += '&merge=true';
        file_spec += '&locus=' + variant.chr + ':' + variant.pos;
        igv.igvRequest(60151, 'load', file_spec);
    },

});