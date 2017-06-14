window.SearchControlsView = Backbone.View.extend({

    initialize: function(options) {
        this.show_button = options.show_button !== false;
    },

    template: _.template($('#tpl-search-controls').html()),

    events: {
        "click #run-search": "run_search",
    },

    render: function(event) {
        var that = this;
        $(this.el).html(this.template({
            show_button: that.show_button,
        }));
        return this;
    },

    set_loading: function() {
        this.$("#run-search").hide();
        this.$('#search-loading').show();
    },

    set_enabled: function() {
        this.$("#run-search").show();
        this.$('#search-loading').hide();
    },

    run_search: function(event) {
        this.trigger('search');
    },

});