
var FamiliesForGeneView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.gene = options.gene;
        this.family_matrix = options.family_matrix;
    },

    render: function() {
        $(this.el).html(this.template({
            family_matrix: this.family_matrix,
        }));
        return this;
    },

    template: _.template($('#tpl-families-by-gene').html()),

});


var RareVariantProjectView = Backbone.View.extend({

    template: _.template($('#tpl-rare-variant-project').html()),

    initialize: function(options) {
        this.hbc = options.hbc;
        this.variant = options.variant;
        this.individuals = options.individuals;
    },

    render: function() {
        $(this.el).html(this.template({
            variants: this.variants,
        }));
        var view = new BasicVariantView({
            hbc: this.hbc,
            variant: this.variant,
            show_genotypes: true,
            individuals: this.individuals,
            show_gene: false,
            genotype_family_id: true,
        });
        this.$('.variant-container').html(view.render().el);
        return this;
    },

});


var RareVariantsInProjectView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.gene = options.gene;
        this.variants = options.variants;
        this.individuals = options.individuals;
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template());
        _.each(this.variants, function(variant) {
            var view = new RareVariantProjectView({
                hbc: that.hbc,
                variant: variant,
                individuals: _.filter(that.individuals, function(i) { return i.indiv_id in variant.genotypes && variant.genotypes[i.indiv_id].num_alt > 0; }),
            });
            that.$('.variants-container').append(view.render().el);
        });
        return this;
    },
    template: _.template($('#tpl-project-rare-variants').html()),
});


var ProjectKnockoutView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.variants = options.variants;
        this.individual = options.individual;
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            individual: that.individual,
        }));
        _.each(this.variants, function(variant) {
            var view = new BasicVariantView({
                hbc: that.hbc,
                show_gene: false,
                variant: variant,
                show_genotypes: true,
                individuals: [that.individual,],
                show_variant_flags: true,
            });
            that.$('.variants-container').append(view.render().el);
        });
        return this;
    },
    template: _.template($('#tpl-project-knockout').html()),
});

var ProjectKnockoutsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.gene = options.gene;
        this.knockouts = options.knockouts;
        this.individuals = options.individuals;
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template());
        _.each(this.knockouts, function(ko) {
            var view = new ProjectKnockoutView({
                hbc: that.hbc,
                variants: ko.variants,
                individual: _.find(that.individuals, function(i) { return i.indiv_id == ko.indiv_id; }),
            });
            that.$('.knockouts-container').append(view.render().el);
        });
        if (this.knockouts.length == 0) {
            this.$('.knockouts-container').append('<em>None</em>');
        }
        return this;
    },
    template: _.template($('#tpl-project-knockouts').html()),
});


var GeneQuickLookHBC = HeadBallCoach.extend({

    initialize: function(options) {

        // caller must provide these
        this.project_options = options.project_options;
        this.gene = options.gene;
        this.rare_variants = options.rare_variants;
        this.individuals = options.individuals;
        this.knockouts = options.knockouts;

        this.rare_variants_view = new RareVariantsInProjectView({
            hbc: this,
            gene: this.gene,
            variants: this.rare_variants,
            individuals: this.individuals,
        });

        this.knockouts_view = new ProjectKnockoutsView({
            hbc: this,
            gene: this.gene,
            knockouts: this.knockouts,
            individuals: this.individuals,
        })

    },

    bind_to_dom: function() {
        $('#interesting-variants-container').html(this.rare_variants_view.render().el);
        $('#knockouts-container').html(this.knockouts_view.render().el);
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

    var hbc = new GeneQuickLookHBC({
        project_options: PROJECT_OPTIONS,
        gene: GENE,
        rare_variants: RARE_VARIANTS,
        individuals: INDIVIDUALS,
        knockouts: KNOCKOUTS,
    });

    hbc.bind_to_dom();
    window.hbc = hbc // remove

    Backbone.history.start();

});







