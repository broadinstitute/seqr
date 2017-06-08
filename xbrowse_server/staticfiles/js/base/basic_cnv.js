window.BasicCNVView = Backbone.View.extend({

    template: _.template($('#tpl-basic-cnv').html()),

    initialize: function(options) {
        this.cnv = options.cnv;
    },

    events: {
    },

    render: function() {
        $(this.el).html(this.template({
        }));
        return this;
    },
});