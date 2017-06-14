/*
Subview for selecting a custom genotype inheritance view
TODO: need to refactor this to only show the genotype form; prefill box should be a separate view
 */
window.ChooseGenotypeFilterView = Backbone.View.extend({

    initialize: function(options) {
        this.hide_prefill = options.hide_prefill == true;  // we don't want to show that prefill box
    },

    template: _.template($('#tpl-choose-genotype-filter').html()),

    render: function(event) {
        $(this.el).html(this.template({
            hide_prefill: this.hide_prefill,
            family: this.options.family,
            genotypeOptions: this.options.genotypeOptions,
            burdenFilterOptions: this.options.burdenFilterOptions,
        }));
        return this;
    },

    events: {
        "change #filter-prefill-select": "setToFilter",
    },

    setToFilter: function(event) {
        var val = $(event.target).val();
        this.drawFromFilter(this.options.familyGenotypeFilters[val]);
    },

    drawFromFilter: function(filter) {
        this.clearGenotypes();
        for (var indiv_id in filter) {
            this.setGenotype(indiv_id, filter[indiv_id]);
        }
    },

    clearGenotypes: function() {
        this.$('select.select-genotype').val('');
    },

    setGenotype: function(indiv_id, genotype_key) {
        this.$('select.select-genotype[data-indiv_id="' + indiv_id + '"]').val(genotype_key);
    },

    getGenotypes: function() {
        var genotypes = {};
        this.$('.select-genotype').each(function() {
            if ($(this).val() != "") {
                genotypes[$(this).data('indiv_id')] = $(this).val();
            }
        });
        return genotypes;
    },

});