window.SliderWidgetView = Backbone.View.extend({

    className: 'basic-slider',

    template: _.template($('#tpl-slider-widget').html()),

    initialize: function() {
        this.min = this.options.min;
        this.max = this.options.max;
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({

        }));

        this.$('.basic-slider-slider').slider({
            min: that.min,
            max: that.max,
            change: function(event, ui) {
                //that.updateSlider(ui.value);
            },
            slide: function(event, ui) {
                that.setLabel(ui.value);
            },
        });

        if (this.options.initial != undefined) {
            that.setVal(this.options.initial);
        } else {
            that.setVal(0);
        }

        return this;
    },

    setVal: function(val) {
        this.$('.basic-slider-slider').slider('value', val);
        this.setLabel(val);
    },

    setLabel: function(val) {
        this.$( ".basic-slider-label" ).text( val );
        this.$( ".basic-slider-label" ).css("margin-left",( ((val-this.min) / (this.max-this.min)).toPrecision(3) * 100 +"%"));
    },

    getVal: function() {
        return this.$('.basic-slider-slider').slider('value');
    }

});

/*
View that provides the basic checkbox variant filters
Pass in a list of "choices" - each with a slug and a title
Will be displayed in order
Also provide "field_name", analagous to name attribute of html form
*/
window.OrdinalFilterView = Backbone.View.extend({

    initialize: function(options) {
        this.field_name = options.field_name;
        this.choices = options.choices;
    },

    render: function() {
        $(this.el).html(this.template( {
            utils: utils,
            field_name: this.field_name,
            choices: this.choices,
        }));
        return this;
    },

    template: _.template($('#tpl-ordinal-filter').html()),

    events: {
        "change input.enable": "redisplay",
    },

    redisplay: function(event) {
        if (this.$('input.enable[value="all"]').prop('checked')) {
            this.$('input.choice').prop('disabled', true);
            this.$('input.choice').prop('checked', false);
        } else {
            this.$('input.choice').prop('disabled', false);
            this.$('input.choice').prop('checked', true);
        }
    },

    // is this filter active? (or is "include all variants" selected)
    isActive: function() {
        return this.$('input.enable[value="some"]').is(':checked');
    },

    setActive: function() {
        this.$('input.enable[value="some"]').prop('checked', true);
        this.$('input.choice').prop('disabled', false);
    },

    getSelections: function() {
        var items = [];
        this.$('input.choice:checked').each(function() {
            items.push($(this).attr('value'));
        })
        return items;
    },

    set_selections: function(selection_list) {
        this.render();
        if (selection_list.length > 0) {
            this.setActive();
        }
        for (var i=0; i<selection_list.length; i++) {
            this.$('input[value="'+selection_list[i]+'"]').prop('checked', true);
        }
    },

});

