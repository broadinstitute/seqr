/*
Subview for selecting only standard inheritances
 */
window.ChooseStandardInheritanceView = Backbone.View.extend({
    initialize: function(options) {
        this.inheritance_methods = options.inheritance_methods;
    },
    template: _.template($('#tpl-choose-standard-inheritance').html()),
    render: function() {
        $(this.el).html(this.template({
            inheritance_methods: this.inheritance_methods
        }));
        return this;
    },
    get_standard_inheritance: function() {
        var val = this.$('input[name="standard_inheritance"]:checked').val();
        if (val == undefined) val = null;
        return val;
    },
    set_standard_inheritance: function(inheritance_mode) {
	this.$('input[name="standard_inheritance"]').prop('checked', false);
	this.$('input[name="standard_inheritance"][value="' + inheritance_mode + '"]').prop('checked', true);
    },
});