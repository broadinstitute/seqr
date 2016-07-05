window.IndividualsView = Backbone.View.extend({
    template: _.template($('#tpl-individuals').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.individuals = options.individuals;
        this.selectable = options.selectable == true;
        this.show_edit_links = options.show_edit_links == true;
        this.show_resource_links = options.show_resource_links == true;
        this.indiv_id_link = options.indiv_id_link != false;
    },
    events: {
        "click #select-all-individuals": "select_all",
        "click .indiv-checkbox": "select_one",
    },
    render: function() {
        $(this.el).html(this.template({
            individuals: this.individuals,
            selectable: this.selectable,
            indiv_id_link: this.indiv_id_link,
            project_spec: this.project_spec,
            show_edit_links: this.show_edit_links,
            show_resource_links: this.show_resource_links,
        }));
	if(!this.selectable) {
            this.$('.tablesorter').tablesorter();
        }
        return this;
    },

    get_selected_indiv_ids: function() {
        var ret = [];
        this.$('.indiv-checkbox:checked').each(function(){ret.push($(this).data('indiv_id'))});
        return ret;
    },

    set_id_selected: function(indiv_id) {
        this.$('.indiv-checkbox[data-indiv_id="' + indiv_id + '"]').prop('checked', true);
        this.$('tr.indiv-row[data-indiv_id="' + indiv_id + '"]').addClass('row-checked');
    },

    set_id_deselected: function(indiv_id) {
        this.$('.indiv-checkbox[data-indiv_id="' + indiv_id + '"]').prop('checked', false);
        this.$('tr.indiv-row[data-indiv_id="' + indiv_id + '"]').removeClass('row-checked');
    },

    select_one: function(e) {
        var checked = $(e.target).is(':checked');
        var indiv_id = $(e.target).data('indiv_id');
        if (checked) {
            this.set_id_selected(indiv_id);
        } else {
            this.set_id_deselected(indiv_id);
        }
    },

    select_all: function(e) {
        var checked = $(e.target).is(':checked');
        for (var i=0; i<this.individuals.length; i++) {
            if (checked) this.set_id_selected(this.individuals[i].indiv_id);
            else this.set_id_deselected(this.individuals[i].indiv_id);
        }
    },
});