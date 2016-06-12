

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

});


$(document).ready(function() {

    var hbc = new FamilyGroupGeneHBC({
        dictionary: DICTIONARY,
        gene: GENE,
        family_group: FAMILY_GROUP,
        variants_by_family: VARIANTS_BY_FAMILY,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});







