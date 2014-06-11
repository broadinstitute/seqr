
// TODO: should probably refactor to share code with SavedVariantView
var SavedFamilyVariantView = Backbone.View.extend({
    template: _.template($('#tpl-saved-family-variant').html()),
    initialize: function(options) {
        this.variant = options.variant;
        this.hbc = options.hbc;
        this.family = options.family;
    },
    render: function(event) {
        $(this.el).html(this.template({
            flags: this.variant.extras.search_flags,
            family_id: this.variant.extras.family_id,
        }));
        var view = new BasicVariantView({
            hbc: this.hbc,
            variant: this.variant,
            show_genotypes: true,
            individuals: this.family.individuals_with_variant_data(),
        });
        this.$('.variant-container').html(view.render().el);
        return this;
    },
});


var SavedFamilyVariantsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family = options.family;
        this.variants = options.variants;
    },

    render: function() {
        var that = this;
        if (this.variants.length == 0) {
            $(this.el).html('<p class="noresults">No saved variants</p>');
        } else {
            _.each(this.variants, function(variant) {
                var view = new SavedFamilyVariantView({
                    variant: variant,
                    hbc: that.hbc,
                    family: that.family,
                });
                that.$el.append(view.render().el);
            });
        }
        return this;
    },
});


var SavedFamilyVariantsHBC = HeadBallCoach.extend({

    initialize: function(options) {

        // caller must provide these
        this.variants = options.variants;
        this.family = options.family;
        this.project_options = options.project_options;

        this.saved_variants_view = new SavedFamilyVariantsView({
            hbc: this,
            family: this.family,
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

        var flag_view = new AddFamilySearchFlagView({
            family: this.family,
            search_hash: "",
            variant: variant,
            suggested_inheritance: "",
            after_finished: after_finished,
        });
        this.pushModal("Flag Variant", flag_view);
    },

});


$(document).ready(function() {

    var hbc = new SavedFamilyVariantsHBC({
        project_options: PROJECT_OPTIONS,
        family: new Family(FAMILY),
        variants: VARIANTS,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});







