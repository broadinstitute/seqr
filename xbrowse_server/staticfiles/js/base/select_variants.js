/*
Select variants to include in a search
Goal is to produce a variant filter that maps closely - but not exactly - to an xbrowse VariantFilter
todo: is that the goal?
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
                {slug: 'damaging', title: 'Damaging'},
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
        'change #gene_list_select': 'setGeneList'
    },

    setGeneList: function(event) {
    	if(event.currentTarget.value == '---') {
    		$('#region-genes').text('');
    	} else {
    		_.each(this.hbc.gene_lists, function(gene_list) {
	    		if(gene_list['slug'] == event.currentTarget.value) {
	    			var genes_string = _.map(gene_list['genes'], function(gene) {
	    				return gene['gene_id'];
	    			}).join('\n');
    				$('#region-genes').text(genes_string);
    			}
    		});
    	}
    },

    toggleAnnotDetails: function(event) {
        var annotGroup = $(event.target).data('annot');
        var box = this.$('.annotation-details[data-annot="' + annotGroup + '"]');
        box.toggle();
    },

    inputAnnotParent: function(event) {
        var annotGroup = $(event.target).data('annot');
        if ($(event.target).is(':checked')) {
            this.$('.input-annot-child[data-parent="' + annotGroup + '"]').prop('checked', true);
        } else {
            this.$('.input-annot-child[data-parent="' + annotGroup + '"]').prop('checked', false);
        }
    },

    inputAnnotChild: function(event) {
        var annotGroup = $(event.target).data('parent');
        if (!$(event.target).is(':checked')) {
            this.$('.input-annot-parent[data-annot="' + annotGroup + '"]').prop('checked', false);
        }
    },

    render: function() {
        $(this.el).html(this.template({
        	hbc: this.hbc,
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
	    if(this.ref_freq_sliders[population]) {
		this.$('.freq-slider-label[data-population="' + population + '"]').text( val );
		this.$('.freq-slider-label[data-population="' + population + '"]').css("margin-left",(utils.freqIndex(val)-1)/(5)*100+"%");
		this.ref_freq_sliders[population].slider('value', utils.freqIndex(val));
	    }
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
                    $(this).prop('checked', false);
                } else {
                    $(this).prop('checked', true);
                }
            });

            for (var g in this.annotationReference.groups_map) {
                this.$('.input-annot-parent[data-annot="' + g + '"]').prop('checked', true);
                var children = this.annotationReference.groups_map[g].children;
                _.each(children, function(c) {
                    if (!this.$('.input-annot-child[data-annot="' + c + '"]').is(':checked')) {
                        this.$('.input-annot-parent[data-annot="' + g + '"]').prop('checked', false);
                    }
                });
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

        if (variantFilter.genes != undefined) {
            this.$('#region-genes').html(variantFilter.genes.join('\n'))
        }

        //if (variantFilter.regions != undefined) {
        //    this.$('#region-coords').html(variantFilter.regions)
        //}
    },

    enablePrediction: function(event) {
        var prediction = $(event.target).attr('name');
        var state = $(event.target).val();
        this.setPredictionState(prediction, state);
    },

    setPredictionState: function(prediction, state) {
        if (state == 'all') {
            this.$('.enable-prediction[name="' + prediction + '"]').prop('checked', false);
            this.$('.enable-prediction[name="' + prediction + '"][value="' + state + '"]').prop('checked', true);
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
