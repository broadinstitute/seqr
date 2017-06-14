window.SelectPhenotypeView = Backbone.View.extend({
    template: _.template($('#tpl-select-phenotype').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.phenotypes = options.project_spec.phenotypes;
    },
    events: {
    },
    render: function() {
        $(this.el).html(this.template({
            phenotypes: this.project_spec.phenotypes,
        }));
        return this;
    },

    get_filter: function() {
        var slug = this.$('#select-phenotype-select').val();
        var phenotype = _.find(this.phenotypes, function(x){return x.slug == slug;});
        var val = this.$('#select-phenotype-bool-value').val();
        var bool_val = null;
        if (val == 'T') bool_val = true;
        if (val == 'F') bool_val = false;
        var ret = {
            slug: slug,
            datatype: phenotype.datatype,
            bool_val: bool_val,
        };
        return ret;
    },
});


