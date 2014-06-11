

var FamilyGroupGeneHBC = HeadBallCoach.extend({

    initialize: function(options) {

        // caller must provide these
        this.dictionary = options.dictionary;
        this.gene = options.gene;
        this.family_group = options.family_group;
        this.variants_by_family = options.variants_by_family;

        this.variants_by_family_view = new VariantsByFamilyView({
            hbc: this,
            family_group: this.family_group,
            variants_by_family: this.variants_by_family,
        });

    },

    bind_to_dom: function() {
        $('#variants-by-family-container').html(this.variants_by_family_view.render().el);
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

    var hbc = new FamilyGroupGeneHBC({
        dictionary: DICTIONARY,
        project_options: PROJECT_OPTIONS,
        gene: GENE,
        family_group: FAMILY_GROUP,
        variants_by_family: VARIANTS_BY_FAMILY,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});







