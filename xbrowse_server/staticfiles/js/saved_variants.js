var SavedVariantView = Backbone.View.extend({
    template: _.template($('#tpl-saved-variant').html()),
    initialize: function(options) {
        this.variant = options.variant;
        this.family = options.family;
        this.hbc = options.hbc;

        this.family_has_bam_file_paths = false;

        var that = this;
        _.each(this.family.individuals_with_variant_data(), function(indiv) {
            if (indiv.has_bam_file_path) {
                that.family_has_bam_file_paths = true;
            }
        });
    },
    render: function(event) {
        var that = this;

        $(this.el).html(this.template({
            flags: that.variant.extras.family_notes,
            tags: that.variant.extras.family_tags,
            variant: that.variant,
            family_id: that.variant.extras.family_id,
            project_id: that.family.attributes.project_id,
        }));



        var view = new BasicVariantView({
            hbc: that.hbc,
            variant: this.variant,
            allow_saving: true,
            context: 'family',
            context_obj: that.family,
	        individuals: that.family.attributes.individuals,
	        show_genotypes: true,
            family_has_bam_file_paths: this.family_has_bam_file_paths,
        });

        view.on('updated', function(variant) {
            that.variant = variant;
            that.render();
        });

        this.$('.variant-container').html(view.render().el);

        return this;
    },

});


var SavedVariantsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.families = options.families;
        this.variants = options.variants;
    },

    render: function() {
        var that = this;
        if (!this.variants || this.variants.length == 0) {
            $(this.el).html('<p class="noresults">No saved variants</p>');
        } else {
            _.each(this.variants, function(variant) {
                var family = new Family(_.find(that.families, function(f) { return f.family_id==variant.extras.family_id}));
                var view = new SavedVariantView({
                    variant: variant,
                    hbc: that.hbc,
                    family: family,
                });
                that.$el.append(view.render().el);
            });
        }
        return this;
    },
});


var SavedVariantsHBC = HeadBallCoach.extend({

    initialize: function(options) {

        // caller must provide these
        this.variants = options.variants;
        this.families = options.families;

        this.saved_variants_view = new SavedVariantsView({
            hbc: this,
            families: this.families,
            variants: this.variants,
        });

    },

    bind_to_dom: function() {
        $('#variants-container').html(this.saved_variants_view.render().el);
    },

    add_variant_flag: function(variant) {
        var that = this;
        function after_finished(variant) {
            var variant_i = -1;
            for (var i=0; i<that.variants.length; i++) {
                var v = that.variants[i];
                if (v.xpos == variant.xpos && v.ref == variant.ref && v.alt == variant.alt) {
                    variant_i = i;
                    break;
                }
            }
            that.variants[variant_i] = variant;
            that.resetModal();
            that.saved_variants_view.render();
        }

        var family = that.families[variant.extras.family_id];
        var flag_view = new AddFamilySearchFlagView({
            family: new Family(family),
            search_hash: "",
            variant: variant,
            suggested_inheritance: "",
            after_finished: after_finished,
        });
        this.pushModal("Flag Variant", flag_view);
    },

});


$(document).ready(function() {
    var hbc = new SavedVariantsHBC({
        families: FAMILIES,
        variants: VARIANTS,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});
