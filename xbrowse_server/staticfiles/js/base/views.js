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
        this.$('input[name="standard_inheritance"]').removeAttr('checked');
        this.$('input[name="standard_inheritance"][value="' + inheritance_mode + '"]').attr('checked', 'checked');
    },
});

/*
Subview for selecting a custom genotype inheritance view
TODO: need to refactor this to only show the genotype form; prefill box should be a separate view
 */
window.ChooseGenotypeFilterView = Backbone.View.extend({

    initialize: function(options) {
        this.hide_prefill = options.hide_prefill == true;  // we don't want to show that prefill box
    },

    template: _.template($('#tpl-choose-genotype-filter').html()),

    render: function(event) {
        $(this.el).html(this.template({
            hide_prefill: this.hide_prefill,
            family: this.options.family,
            genotypeOptions: this.options.genotypeOptions,
            burdenFilterOptions: this.options.burdenFilterOptions,
        }));
        return this;
    },

    events: {
        "change #filter-prefill-select": "setToFilter",
    },

    setToFilter: function(event) {
        var val = $(event.target).val();
        this.drawFromFilter(this.options.familyGenotypeFilters[val]);
    },

    drawFromFilter: function(filter) {
        this.clearGenotypes();
        for (var indiv_id in filter) {
            this.setGenotype(indiv_id, filter[indiv_id]);
        }
    },

    clearGenotypes: function() {
        this.$('select.select-genotype').val('');
    },

    setGenotype: function(indiv_id, genotype_key) {
        this.$('select.select-genotype[data-indiv_id="' + indiv_id + '"]').val(genotype_key);
    },

    getGenotypes: function() {
        var genotypes = {};
        this.$('.select-genotype').each(function() {
            if ($(this).val() != "") {
                genotypes[$(this).data('indiv_id')] = $(this).val();
            }
        });
        return genotypes;
    },

});


/*
Select variants to include in a search
Goal is to produce a variant filter that maps closely - but not exactly - to an xbrowse VariantFilter

Args:
    hbc: a HeadBallCoach that can process modal events
    project_options: contains both project specifications and display options

Options:


 */
window.SelectVariantsView = Backbone.View.extend({

    initialize: function(options) {

        this.hbc = this.options.hbc;
        this.dictionary = this.hbc.dictionary;
        this.project_options = this.hbc.project_options;

        this.annotDefs = this.dictionary.annotation_reference.definitions_grouped;
        this.defaultVariantFilters = this.dictionary.default_variant_filters;
        this.annotationReference = this.dictionary.annotation_reference;
        this.defaultQualityFilters = this.dictionary.default_quality_filters;

        this.reference_populations = this.project_options.reference_populations || [];

        this.vartype_widget = new OrdinalFilterView({
            field_name: 'vartype',
            choices: [
                {slug: 'snp', title: 'SNPs'},
                {slug: 'indel', title: 'In/Dels'},
            ],
        });

        this.polyphen_widget = new OrdinalFilterView({
            field_name: 'polyphen',
            choices: [
                {slug: 'probably_damaging', title: 'Probably damaging'},
                {slug: 'possibly_damaging', title: 'Possibly damaging'},
                {slug: 'benign', title: 'Benign'},
                {slug: 'no_score', title: 'No prediction'},
            ],
        });

        this.sift_widget = new OrdinalFilterView({
            field_name: 'sift',
            choices: [
                {slug: 'deleterious', title: 'Deleterious'},
                {slug: 'tolerated', title: 'Tolerated'},
                {slug: 'no_score', title: 'No prediction'},
            ],
        });

        this.muttaster_widget = new OrdinalFilterView({
            field_name: 'muttaster',
            choices: [
                {slug: 'disease_causing', title: 'Disease Causing'},
                {slug: 'polymorphism', title: 'Polymorphism'},
                {slug: 'no_score', title: 'No Prediction'},
            ],
        });

        this.fathmm_widget = new OrdinalFilterView({
            field_name: 'fathmm',
            choices: [
                {slug: 'damaging', title: 'Damaging'},
                {slug: 'tolerated', title: 'Tolerated'},
                {slug: 'no_score', title: 'No Prediction'},
            ],
        });

    },

    template: _.template($('#tpl-select-variants').html()),

    events: {
        "change #variant-presets-select": "standardSelectChange",
        "click a.toggle-annotation-details": "toggleAnnotDetails",
        "change .input-annot-parent": "inputAnnotParent",
        "change .input-annot-child": "inputAnnotChild",
        'change .enable-prediction': 'enablePrediction',
    },

    toggleAnnotDetails: function(event) {
        var annotGroup = $(event.target).data('annot');
        var box = this.$('.annotation-details[data-annot="' + annotGroup + '"]');
        box.toggle();
    },

    inputAnnotParent: function(event) {
        var annotGroup = $(event.target).data('annot');
        if ($(event.target).is(':checked')) {
            this.$('.input-annot-child[data-parent="' + annotGroup + '"]').attr('checked', 'checked');
        } else {
            this.$('.input-annot-child[data-parent="' + annotGroup + '"]').removeAttr('checked');
        }
    },

    inputAnnotChild: function(event) {
        var annotGroup = $(event.target).data('parent');
        if (!$(event.target).is(':checked')) {
            this.$('.input-annot-parent[data-annot="' + annotGroup + '"]').removeAttr('checked');
        }
    },

    render: function() {
        $(this.el).html(this.template({
            annotDefs: this.annotDefs,
            defaultVariantFilters: this.defaultVariantFilters,
            reference_populations: this.reference_populations,
        }));

        this.create_ref_freq_sliders();
        this.vartype_widget.setElement(this.$('#vartype-widget-container')).render();
        this.polyphen_widget.setElement(this.$('#polyphen-widget-container')).render();
        this.sift_widget.setElement(this.$('#sift-widget-container')).render();
        this.muttaster_widget.setElement(this.$('#muttaster-widget-container')).render();
        this.fathmm_widget.setElement(this.$('#fathmm-widget-container')).render();
        utils.initializeHovers(this);

        return this;
    },

    getVariantFilter: function() {

        var that = this;

        var variantFilter = new VariantFilter();

        // so_annotations
        var annots = [];
        that.$('input.input-annot-child:checked').each(function() {
            annots.push($(this).data('annot'));
        });
        if (annots.length > 0) {
            variantFilter.set('so_annotations', annots);
        }

        // variant types
        if (this.vartype_widget.isActive()) {
            variantFilter.set('variant_types', this.vartype_widget.getSelections());
        }

        // allele frequency
        var frequency_filters = [];
        _.each(this.ref_freq_sliders, function(s, population) {
            var freq = parseFloat(utils.freqInverse(s.slider("value")));
            if (freq < 1) {
                frequency_filters.push([population, freq]);
            }
        });
        variantFilter.set('ref_freqs', frequency_filters);

        // predictions
        var annotations = {};
        if (this.polyphen_widget.isActive()) {
            var str_annots = this.polyphen_widget.getSelections();
            for (var i=0; i<str_annots.length; i++) {
                if (str_annots[i] == 'no_score') {
                    str_annots[i] = null;
                }
            }
            annotations.polyphen = str_annots;
        }
        if (this.sift_widget.isActive()) {
            var str_annots = this.sift_widget.getSelections();
            for (var i=0; i<str_annots.length; i++) {
                if (str_annots[i] == 'no_score') {
                    str_annots[i] = null;
                }
            }
            annotations.sift = str_annots;
        }
        if (this.muttaster_widget.isActive()) {
            var str_annots = this.muttaster_widget.getSelections();
            for (var i=0; i<str_annots.length; i++) {
                if (str_annots[i] == 'no_score') {
                    str_annots[i] = null;
                }
            }
            annotations.muttaster = str_annots;
        }
        if (this.fathmm_widget.isActive()) {
            var str_annots = this.fathmm_widget.getSelections();
            for (var i=0; i<str_annots.length; i++) {
                if (str_annots[i] == 'no_score') {
                    str_annots[i] = null;
                }
            }
            annotations.fathmm = str_annots;
        }
        variantFilter.set('annotations', annotations);

        // regions
        var region_text = $.trim(this.$('#region-coords').val());
        if (region_text != "") {
            variantFilter.set('regions', region_text.split('\n'));
        }

        // genes
        var genes_text = $.trim(this.$('#region-genes').val());
        if (genes_text != "") {
            variantFilter.set('genes_raw', genes_text);
        }

        return variantFilter;
    },

    standardSelectChange: function(event) {
        var filterSlug = $(event.target).val();
        var standardFilter = _.find(this.defaultVariantFilters, function(x) { return x.slug == filterSlug });
        if (standardFilter != undefined) {
            this.loadFromVariantFilter(standardFilter.variant_filter);
        } else {
            this.loadFromVariantFilter();
        }
        this.$('#variant-presets-select').val(filterSlug);
    },

    // TODO: get this out of here!
    create_ref_freq_sliders: function() {
        var that = this;

        this.ref_freq_sliders = {};
        _.each(this.reference_populations, function(pop) {
            var freqSliderInitialVal = 6;
            var newslider = that.$('.freq-slider[data-population="' + pop.slug + '"]').slider({
                min: 1,
                max: 6,
                step: 1,
                value: freqSliderInitialVal,
                slide: function(event, ui) {
                    that.$('.freq-slider-label[data-population="' + pop.slug + '"]').text( sliders.freqInverse(ui.value) );
                    that.$('.freq-slider-label[data-population="' + pop.slug + '"]').css("margin-left",(ui.value-1)/5*100+"%");
                }
            });
            that.ref_freq_sliders[pop.slug] = newslider;
            this.$( "#freqSliderLabel" ).text( sliders.freqInverse(freqSliderInitialVal) );
            this.$( "#freqSliderLabel" ).css("margin-left",(freqSliderInitialVal-1)/(5)*100+"%");
        });
    },

    setSlider: function(population, val) {
        this.$('.freq-slider-label[data-population="' + population + '"]').text( val );
        this.$('.freq-slider-label[data-population="' + population + '"]').css("margin-left",(utils.freqIndex(val)-1)/(5)*100+"%");
        this.ref_freq_sliders[population].slider('value', utils.freqIndex(val));
    },

    /*
    TODO: right now we load from a javascript dict, but the get* methods return
    a backbone model. They should be consistent, but not sure which to use.
    */
    loadFromVariantFilter: function(variantFilter) {

        this.render();

        if (variantFilter == undefined) {
            variantFilter = {};
        }

        if (variantFilter.so_annotations != undefined) {
            var annots = variantFilter.so_annotations;
            this.$('.input-annot-child').each(function() {
                if (annots.indexOf($(this).data('annot')) == -1) {
                    $(this).attr('checked', false);
                } else {
                    $(this).attr('checked', true);
                }
            });

            for (var g in this.annotationReference.groups_map) {
                this.$('.input-annot-parent[data-annot="' + g + '"]').attr('checked', 'checked');
                var children = this.annotationReference.groups_map[g].children;
                for (var c in children) {
                    if (!this.$('.input-annot-child[data-annot="' + children[c] + '"]').is(':checked')) {
                        this.$('.input-annot-parent[data-annot="' + g + '"]').removeAttr('checked');
                    }
                }
            }
        }

        if (variantFilter.variant_types) {
            this.vartype_widget.set_selections(variantFilter.variant_types);
        }

        // update frequency slider
        if (variantFilter.ref_freqs != undefined) {
            var that = this;
            _.each(variantFilter.ref_freqs, function(ref_freq) {
                that.setSlider(ref_freq[0], ref_freq[1]);
            });
        }

        // polyphen
        if (variantFilter.polyphen != undefined) {
            this.polyphen_widget.set_selections(variantFilter.polyphen);
            this.expand_section('predictions');
        }
        if (variantFilter.sift != undefined) {
            this.sift_widget.set_selections(variantFilter.sift);
            this.expand_section('predictions');
        }

        if (variantFilter.genes_raw != undefined) {
            this.$('#region-genes').html(variantFilter.genes_raw)
        }
    },

    enablePrediction: function(event) {
        var prediction = $(event.target).attr('name');
        var state = $(event.target).val();
        this.setPredictionState(prediction, state);
    },

    setPredictionState: function(prediction, state) {
        if (state == 'all') {
            this.$('.enable-prediction[name="' + prediction + '"]').removeAttr('checked');
            this.$('.enable-prediction[name="' + prediction + '"][value="' + state + '"]').attr('checked', 'checked');
            this.$('.input-' + prediction).attr('disabled', 'disabled');
            this.$('.input-' + prediction).removeAttr('checked');
        } else {
            this.$('.input-' + prediction).removeAttr('disabled');
            this.$('.input-' + prediction).attr('checked', 'checked');
        }
    },

    // ensure a particular collapse is expanded
    expand_section: function(section_key) {
        this.$('#collapse-'+section_key).collapse('show');
    },

    // opposite of above
    collapse_section: function(section_key) {
        this.$('#collapse-'+section_key).collapse('show');
    },
});

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


window.GeneDetailsView = Backbone.View.extend({

    initialize: function() {
        this.gene = this.options.gene;
    },

    template: _.template($('#tpl-gene-modal-content').html()),

    render: function(width) {
        var that = this;
        $(this.el).html(this.template({
            gene: that.gene,
        }));
        this.drawExpressionDisplay(width-40);
        return this;
    },

    resize: function() {
    },

    drawExpressionDisplay: function(width) {

        var that = this;

        if (this.gene.expression == null) {
            this.$('#expression_plot').hide();
            this.$('#no-gene-expression').show();
            return;
        } else {
            this.$('#expression_plot').show();
            this.$('#no-gene-expression').hide();
        }

        // rename to tissue_names
        var expression_names = [];
        var expression_slugs = [];
        for (var i=0; i<DICTIONARY.tissue_types.length; i++) {
            expression_slugs.push(DICTIONARY.tissue_types[i].slug);
            expression_names.push(DICTIONARY.tissue_types[i].name);
        }

        //var width = that.$('#expression_plot').width();

        var row_height = 25;
        var scatter_offset = 200;
        var scatter_horizontal_padding = 10;

        var scatter_width = width-scatter_offset-2*scatter_horizontal_padding;
        var min_exponent = -10;
        var max_exponent = 12;

        var x = d3.scale.linear().domain([min_exponent, max_exponent]).range([0, scatter_width]);
        var row_offset = function(i) { return i*row_height + 30 }

        var xcoord = function(d) {
            var e = min_exponent;
            if (d>0) {
                e = Math.log(d)/Math.log(2); // convert to base 2
            }
            // don't allow outside bounds
            if (e < min_exponent) e = min_exponent;
            if (e > max_exponent) e = max_exponent;

            return scatter_offset + scatter_horizontal_padding + x(e);

        }

        var vis = d3.selectAll(that.$("#expression_plot"))
            .append("svg")
            .attr("width", width)
            .attr("height", row_height*expression_slugs.length + 50);

        var labels = vis.selectAll('text')
            .data(expression_names)
            .enter()
            .append('text')
            .attr("text-anchor", "end")
            .attr('x', scatter_offset-25) // 12 px margin between text and scatter
            .attr('y', function(d,i) { return row_offset(i) + 15 } )
            .style('font-weight', 'bold')
            .text(function(d) { return d; });

        var colors = d3.scale.category10();

        var axis = d3.svg.axis()
            .scale(x)
            .tickSize(0)
            .tickPadding(6)
            .orient("bottom");

        vis.append("g")
            .attr("class", "axis axis-label")
            .attr("transform", "translate(" + scatter_offset + "," + 3 + ")")
            .call(axis);

        vis.append("g")
            .append("text")
            .attr("class", "axis axis-title")
            .text("LOG 2 EXPRESSION")
            .attr("text-anchor", "end")
            .attr("transform", "translate(" + (scatter_offset - 25) + "," + 17 + ")");

        var colorLabels = vis.selectAll('rect.color-label')
            .data(expression_names)
            .enter()
            .append('rect')
            .attr('class', 'color-label')
            .attr('x', scatter_offset-15 )
            .attr('y', function(d,i) { return row_offset(i) + 4 } )
            .attr('width', 6)
            .attr('height', 16)
            .attr('fill', function(d, i) { return colors(i); } )
            .attr('fill-opacity', .7);

        for (var i=0; i<expression_slugs.length; i++) {
            var slug = expression_slugs[i];
            window.expr = this.gene.expression;
            vis.selectAll('circle[data-expression="' + slug + '"]')
                .data(this.gene.expression[slug]).enter()
                .append('circle')
                .attr('data-expression', slug)
                .attr('r', 10)
                .attr('fill-opacity', .12)
                .attr('fill', function(d, j) { return colors(i); } )
                .attr('transform', function(d,j) { return "translate(" + xcoord(d) + "," + (row_offset(i) + 13) + ")"; })
                ;
        }
    }
});

window.GeneModalView = Backbone.View.extend({

    initialize: function() {
        this.gene = {};
    },

    content_template: _.template($('#tpl-gene-modal-content').html()),

    template: _.template(
        $('#tpl-gene-modal').html()
    ),

    render: function(eventName) {

        var that = this;

        $(this.el).html(this.template({
            gene_id: this.options.gene_id,
        }));

        this.setLoading();

        $.get(URL_PREFIX + 'api/gene-info/' + this.options.gene_id, {},
            function(data) {
                if (data.found_gene == true) {
                    that.gene = data.gene;
                    that.setLoaded();
                } else {
                    that.gene = null;
                    that.setNotFound();
                }
            }
        );

        return this;
    },

    setLoading: function() {
        this.$('#modal-content-container').hide();
        this.$('#modal-loading').show();
    },

    setNotFound: function() {
        this.$('#modal-content-container').html("<em>Gene not found</em>");
        this.$('#modal-content-container').show();
        this.$('#modal-loading').hide();
    },

    setLoaded: function() {
        var that = this;
        //this.$('#modal-content-container').html(this.content_template({ gene: this.gene }));
        var detailsView = new GeneDetailsView({gene: this.gene});

        this.$('#modal-content-container').html(detailsView.render($(that.el).width()).el);
        detailsView.resize();

        this.$('#modal-content-container').show();
        this.$('#modal-loading').hide();
    },

});

window.AddFamilySearchFlagView = Backbone.View.extend({

    initialize: function(options) {
        this.family = options.family;
        this.variant = options.variant;
        this.search_hash = options.search_hash;
        this.suggested_inheritance = options.suggested_inheritance;
        this.after_finished = options.after_finished;
    },

    template: _.template(
        $('#tpl-add-family-search-flag').html()
    ),

    events: {
        'click #add-flag-save': 'save',
    },

    render: function(event) {
        var that = this;
        $(this.el).html(this.template({
            variant: that.variant,
            suggested_inheritance: that.suggested_inheritance,
        }));
        var flags_view = new VariantFlagsView({flags: that.variant.extras.search_flags});
        this.$('.flags-display').html(flags_view.render().el);
        return this;
    },

    setLoading: function() {
        this.$('#modal-content-container').hide();
        this.$('#modal-loading').show();
    },

    setLoaded: function() {
        this.$('#modal-content-container').html(this.content_template({ gene: this.gene }));
        this.$('#modal-content-container').show();
        this.$('#modal-loading').hide();
    },

    save: function() {
        var that = this;

        var flag_type = this.$('input[name="flag_reason"]:checked').val();
        if (flag_type == undefined) {
            alert('Flag type required');
            return;
        }
        var flag_inheritance_mode = this.$('input[name="flag_inheritance_mode"]:checked').val();
        if (flag_inheritance_mode == undefined) {
            alert('Inheritance mode required');
            return;
        }

        var note = this.$('#flag_inheritance_notes').val();
        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
            search_hash: this.search_hash,
            note: note,
            flag_type: flag_type,
            flag_inheritance_mode: flag_inheritance_mode,
        }

        that.$('#add-flag-save').attr('disabled', 'disabled');

        $.get(URL_PREFIX + 'api/family/add-family-search-flag', postData,
            function(data) {
                if (data.is_error) {
                    // TODO: global error() function
                    alert('error; please refresh the page')
                } else {
                    that.after_finished(data.variant);
                }
            }
        );
    },
});


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

    template: _.template($('#tpl-variant-flags').html()),

});


window.BasicVariantView = Backbone.View.extend({

    className: 'basicvariant-container',

    initialize: function(options) {

        // required
        this.hbc = options.hbc;
        this.variant = options.variant;

        // optional
        this.show_genotypes = options.show_genotypes || false;
        this.individuals = options.individuals || [];
        this.actions = options.actions || null;
        this.highlight = options.highlight || null;
        this.leftview = options.leftview || null;
        this.show_gene = options.show_gene != false;
        this.genotype_family_id = options.genotype_family_id || false;

        this.individual_map = {};
        for (var i=0; i<this.individuals.length; i++) {
            this.individual_map[this.individuals[i].indiv_id] = this.individuals[i];
        }

        this.reference_populations = this.hbc.project_options.reference_populations;

    },

    render: function() {
        $(this.el).html(this.template( {
            utils: utils,
            dictionary: this.hbc.dictionary,
            show_gene: this.show_gene,
            leftview: this.leftview,
            variant: this.variant,
            individuals: this.individuals,
            individual_map: this.individual_map,
            reference_populations: this.reference_populations,
            show_genotypes: this.show_genotypes,
            actions: this.actions,
            highlight: this.highlight,
            genotype_family_id: this.genotype_family_id,
        }));
        if (this.highlight) {
            this.$el.addClass('highlighted');
        }
        utils.initializeHovers(this);
        if (this.leftview) {
            this.$('.leftview').html(this.leftview.render().el);
        }
        return this;
    },

    events: {
        "click a.action": "action",
        "click a.highlight-more": "highlight_more",
        "click a.gene-link": "gene_info",
        "click a.annotation-link": "annotation_link",
    },

    template: _.template($('#tpl-basic-variant').html()),

    action: function(event) {
        var a = $(event.target).data('action');
        this.trigger(a, this.variant);
    },

    highlight_more: function(event) {
        this.trigger('highlight', this.variant);
    },

    gene_info: function(event) {
        var gene_id = $(event.target).data('gene_id');
        this.hbc.gene_info(gene_id);
    },

    annotation_link: function(event) {
        this.hbc.variant_info(this.variant);
    },

});


window.BasicVariantsTable = Backbone.View.extend({

    initialize: function(options) {

        // required
        this.hbc = options.hbc;
        this.variants = options.variants;

        // optional
        this.show_header = options.show_header || false;
        this.show_genotypes = options.show_genotypes || false;
        this.individuals = options.individuals || [];
        this.allow_saving = options.allow_saving || false;
        this.show_variant_flags = options.show_variant_flags || false;
        this.show_igv_links = options.show_igv_links || false;
        this.bam_file_urls = options.bam_file_urls || {};

        this.indiv_id_list = [];
        this.indiv_id_to_family_id = {};
        for (var i=0; i<this.individuals.length; i++) {
            this.indiv_id_list.push(this.individuals[i].indiv_id);
            this.indiv_id_to_family_id[this.individuals[i].indiv_id] = this.individuals[i].family_id;
        }

        if (this.show_igv_links) {
            this.bam_file_urls_list = [];
            for (var i=0; i<this.indiv_id_list.length; i++) {
                var indiv_id = this.indiv_id_list[i];
                if (indiv_id in this.bam_file_urls) {
                    this.bam_file_urls_list.push(this.bam_file_urls[indiv_id]);
                }
            }
        }

        this.actions = [];
        if (this.allow_saving) {
            this.actions.push({
                action: 'save',
                name: 'Save',
            });
        }
        if (this.show_igv_links) {
            this.actions.push({
                action: 'igv',
                name: 'IGV',
            });
        }

    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({}));
        _.each(this.variants, function(variant) {
            var highlight = null;
            if (that.show_variant_flags) {
                highlight = variant.extras.search_flags.length > 0 ? 'This variant has been saved in this project' : null;
            }
            var view = new BasicVariantView({
                hbc: that.hbc,
                variant: variant,
                individuals: that.individuals,
                reference_populations: that.hbc.project_options.reference_populations,
                show_genotypes: that.show_genotypes,
                actions: that.actions,
                highlight: highlight,

            });
            view.on('igv', that.show_variant_in_igv, that);
            view.on('save', that.save_variant, that);
            view.on('highlight', that.show_saved_variants, that);
            that.$('.basic-variants-list').append(view.render().el);
        });
        return this;
    },

    template: _.template($('#tpl-basic-variant-list').html()),

    save_variant: function(variant) {
        this.hbc.add_variant_flag(variant);
    },

    show_saved_variants: function(variant) {
        var view = new VariantFlagsView({flags: variant.extras.search_flags});
        this.hbc.pushModal('', view);
    },

    hide_flags_hover: function(event) {
        $(event.target).popover('hide');
    },

    show_variant_in_igv: function(variant) {
        var file_spec = 'file=';
        for (var i=0; i<this.bam_file_urls_list.length; i++) {
            file_spec += this.bam_file_urls_list[i] + ','
        }
        file_spec += '&merge=true';
        file_spec += '&locus=' + variant.chr + ':' + variant.pos;
        igv.igvRequest(60151, 'load', file_spec);
    },

});


window.SelectPhenotypeView = Backbone.View.extend({
    template: _.template($('#tpl-select-phenotype').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.phenotypes = options.project_spec.phenotypes;
    },
    events: {
    },
    render: function() {
        $(this.el).html(this.template({
            phenotypes: this.project_spec.phenotypes,
        }));
        return this;
    },

    get_filter: function() {
        var slug = this.$('#select-phenotype-select').val();
        var phenotype = _.find(this.phenotypes, function(x){return x.slug == slug;});
        var val = this.$('#select-phenotype-bool-value').val();
        var bool_val = null;
        if (val == 'T') bool_val = true;
        if (val == 'F') bool_val = false;
        var ret = {
            slug: slug,
            datatype: phenotype.datatype, 
            bool_val: bool_val,
        };
        return ret;
    },
});


window.SelectGeneView = Backbone.View.extend({
    template: _.template($('#tpl-choose-gene').html()),
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
                $.get(URL_PREFIX + 'api/autocomplete/gene?q='+query,
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
    set_enabled: function(is_enabled) {
        if (is_enabled) {
            this.$('.select-gene-input').prop('disabled', false);
        } else {
            this.$('.select-gene-input').prop('disabled', true);
        }
    }
});


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
                $.get(URL_PREFIX + 'api/autocomplete/gene?q='+query,
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