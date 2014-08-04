window.VariantFlagsView = Backbone.View.extend({

    initialize: function(options) {
        this.flags = options.flags;
    },

    render: function(event) {
        $(this.el).html(this.template({
            flags: this.flags,
        }));
        return this;
    },

    template: _.template($('#tpl-variant-notes').html()),

});