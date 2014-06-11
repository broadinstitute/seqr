var SavedVariantView = Backbone.View.extend({
    template: _.template($('#tpl-saved-variant').html()),
    initialize: function(options) {
        this.variant = options.variant;
        this.hbc = options.hbc;
    },
    render: function(event) {
        $(this.el).html(this.template({
            flags: this.variant.extras.search_flags,
            family_id: this.variant.extras.family_id,
        }));
        var view = new BasicVariantView({
            hbc: this.hbc,
            variant: this.variant,
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
        if (this.variants.length == 0) {
            $(this.el).html('<p class="noresults">No saved variants</p>');
        } else {
            _.each(this.variants, function(variant) {
                var view = new SavedVariantView({
                    variant: variant,
                    hbc: that.hbc,
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
        this.project_options = options.project_options;
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
        project_options: PROJECT_OPTIONS,
        families: FAMILIES,
        variants: VARIANTS,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});







