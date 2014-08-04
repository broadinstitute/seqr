window.AnnotationDetailsView = Backbone.View.extend({

    template: _.template($('#tpl-annotation-details').html()),

    className: 'annotation-view',

    initialize: function(options) {
        this.variant = options.variant;
    },

    render: function(event) {
        var that = this;
        $(this.el).html(this.template({
            variant: this.variant
        }));
        return this;
    },
});