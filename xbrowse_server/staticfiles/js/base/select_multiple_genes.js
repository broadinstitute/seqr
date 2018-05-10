window.SelectMultipleGenesView = Backbone.View.extend({
    template: _.template($('#tpl-select-multiple-genes').html()),
    initialize: function(options) {
        this.engine = {
          compile: function(template) {
            var compiled = _.template(template);
            return {
              render: function(context) { return compiled(context); }
            }
          }
        };
    },
    render: function() {
        var that = this;
        $(this.el).html(this.template({}));
        var geneidmap = {};
        this.$('.select-gene-input').typeahead({
            source: function(query, process) {
                $.get('/api/autocomplete/gene?q='+query,
                    function(data) {
                        var gene_names = [];
                        _.each(data, function(d) {
                            gene_names.push(d.label);
                            geneidmap[d.label] = d.value;
                        });
                        process(gene_names);
                    },
                    'json'
                )
            },
            property: "label",
            updater: function(item) {
                that.trigger('gene-selected', geneidmap[item]);
            }
        });
        return this;
    },
    events: {

    },
});