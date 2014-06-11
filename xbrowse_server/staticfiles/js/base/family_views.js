window.FamiliesView = Backbone.View.extend({
    template: _.template($('#tpl-families').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.families = options.families;
        this.selectable = options.selectable == true;
        this.show_edit_links = options.show_edit_links == true;
        this.family_id_link = options.family_id_link != false;
    },
    events: {
        "click #select-all-families": "select_all",
        "click .family-checkbox": "select_one",
    },
    render: function() {
        $(this.el).html(this.template({
            families: this.families,
            selectable: this.selectable,
            family_id_link: this.family_id_link,
            project_spec: this.project_spec,
            show_edit_links: this.show_edit_links,
        }));
        return this;
    },

    get_selected_family_ids: function() {
        var ret = [];
        this.$('.family-checkbox:checked').each(function(){ret.push($(this).data('family_id'))});
        return ret;
    },

    set_id_selected: function(family_id) {
        this.$('.family-checkbox[data-family_id="' + family_id + '"]').prop('checked', true);
        this.$('tr.family-row[data-family_id="' + family_id + '"]').addClass('row-checked');
    },

    set_id_deselected: function(family_id) {
        this.$('.family-checkbox[data-family_id="' + family_id + '"]').prop('checked', false);
        this.$('tr.family-row[data-family_id="' + family_id + '"]').removeClass('row-checked');
    },

    select_one: function(e) {
        var checked = $(e.target).is(':checked');
        var family_id = $(e.target).data('family_id');
        if (checked) {
            this.set_id_selected(family_id);
        } else {
            this.set_id_deselected(family_id);
        }
    },

    select_all: function(e) {
        var checked = $(e.target).is(':checked');
        for (var i=0; i<this.families.length; i++) {
            if (checked) this.set_id_selected(this.families[i].family_id);
            else this.set_id_deselected(this.families[i].family_id);
        }
    },

    select_with_phenotype: function(pheno_filter) {
        var that = this;
        if (pheno_filter.bool_val != true) {
            alert("You've encountered an annoying error - you can only select binary phenotypes of Yes, not No or Unknown. Sorry about that, will be fixed soon...");
            return;
        }
        var slug = pheno_filter.slug;
        _.each(this.families, function(family) {
            if (_.find(family.phenotypes, function(x){return x==slug})) {
                that.set_id_selected(family.family_id);
            }
        });
    },
});