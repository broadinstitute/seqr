window.SelectQualityFilterView = Backbone.View.extend({

    initialize: function(options) {
        this.default_quality_filters = options.default_quality_filters;
        this.gqSlider = new SliderWidgetView({min: 0, max: 100});
        this.abSlider = new SliderWidgetView({min: 0, max: 50});
        this.hetRatioSlider = new SliderWidgetView({min: 0, max: 100});
    },

    template: _.template($('#tpl-select-quality-filter').html()),

    events: {
        "change #quality-defaults-select": "qualityDefaultChange",
    },

    render: function(event) {
        $(this.el).html(this.template({
            defaultQualityFilters: this.default_quality_filters,
        }));

        this.gqSlider.setElement(this.$('#gq-quality-container')).render();
        this.abSlider.setElement(this.$('#ab-quality-container')).render();
        this.hetRatioSlider.setElement(this.$('#het-ratio-slider-container')).render();
	utils.initializeHovers(this);
        return this;
    },

    getQualityFilter: function() {
        var qualityFilter = new QualityFilter();
        if (this.$('#filter-select').val() == 'pass') {
            qualityFilter.set('vcf_filter', 'pass');
        }
        qualityFilter.set('min_gq', this.gqSlider.getVal());
        qualityFilter.set('min_ab', this.abSlider.getVal());
        return qualityFilter;
    },

    loadFromQualityFilter: function(qualityFilter) {

        this.render();

        if (qualityFilter == undefined) return;

        // filter
        if (qualityFilter.vcf_filter != undefined) {
            if (qualityFilter.vcf_filter == 'pass') {
                this.$('#filter-select').val('pass');
            } else {
                alert("Error 394811 - invalid qual filter");
            }
        } else {
            this.$('#filter-select').val('');
        }

        // GQ
        if (qualityFilter.min_gq != undefined) {
            this.gqSlider.setVal(qualityFilter.min_gq);
        } else {
            this.gqSlider.setVal(0);
        }

        // AB
        if (qualityFilter.min_ab != undefined) {
            this.abSlider.setVal(qualityFilter.min_ab);
        } else {
            this.abSlider.setVal(0);
        }
    },

    qualityDefaultChange: function(event) {
        var slug = $(event.target).val();
        var qualityDefault = _.find(this.default_quality_filters, function(x) { return x.slug == slug });
        if (qualityDefault != undefined) {
            this.loadFromQualityFilter(qualityDefault.quality_filter);
        } else {
            this.loadFromQualityFilter();
        }
        this.$('#quality-defaults-select').val(slug);
    },
});
