
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
	    show_gene: true,
            individuals: this.family.individuals_with_variant_data(),
            show_tag_details: true,
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
        if (!this.variants || this.variants.length == 0) {
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

        this.saved_variants_view = new SavedFamilyVariantsView({
            hbc: this,
            family: this.family,
            variants: this.variants,
        });

    },

    bind_to_dom: function() {
        $('#variants-container').html(this.saved_variants_view.render().el);
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







