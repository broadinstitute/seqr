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

        this.annotDefs = this.dictionary.annotation_reference.definitions_grouped
        if (this.project_options.db !== "elasticsearch") {
            // only elasticsearch supports the In Clinvar filter
            this.annotDefs = this.annotDefs.filter(function(annotGroup) {
                return annotGroup.slug != "clinvar" && annotGroup.slug != "hgmd"
            });
        }

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
        "change #set-all-freq-filters": "allFreqFilterSelectChange",
        "change #set-all-ac-filters": "allAcFilterSelectChange",
        "change #set-all-hom-hemi-filters": "allHomHemiFilterSelectChange",
        "change .ac-select": "acSelectChange",
        "change .hom-hemi-select": "homHemiSelectChange",

        "click a.toggle-annotation-details": "toggleAnnotDetails",
        "change .input-annot-parent": "inputAnnotParent",
        "change .input-annot-child": "inputAnnotChild",
        'change .enable-prediction': 'enablePrediction',
        'change #gene_list_select': 'setGeneList'
    },

    setGeneList: function(event) {
    	if(event.currentTarget.value == '---') {
    		$('#region-genes').val('');
    	} else {
    		_.each(this.hbc.gene_lists, function(gene_list) {
	    		if(gene_list['slug'] == event.currentTarget.value) {
	    			var genes_string = _.map(gene_list['genes'], function(gene) {
	    				return gene['gene_id'];
	    			}).join('\n');
    				$('#region-genes').val(genes_string);
    			}
    		});
    	}
    },

    toggleAnnotDetails: function(event) {
        var annotGroup = $(event.target).data('annot');
        var box = this.$('.annotation-details[data-annot="' + annotGroup + '"]');
        box.toggle();
    },

    updateAnnotParentCheckbox: function(annotGroup) {
        var children = this.annotationReference.groups_map[annotGroup].children;
        var childrenCheckedCounter = 0;
        _.each(children, function(c) {
            if (this.$('.input-annot-child[data-annot="' + c + '"]').is(':checked')) {
                childrenCheckedCounter += 1;
            }
        });
        this.$('.input-annot-parent[data-annot="' + annotGroup + '"]').prop('indeterminate', false);
        if (childrenCheckedCounter == 0) {
            this.$('.input-annot-parent[data-annot="' + annotGroup + '"]').prop('checked', false);
        } else if (childrenCheckedCounter == children.length) {
            this.$('.input-annot-parent[data-annot="' + annotGroup + '"]').prop('checked', true);
        } else {
            this.$('.input-annot-parent[data-annot="' + annotGroup + '"]').prop('indeterminate', true);
        }
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
        this.updateAnnotParentCheckbox(annotGroup);
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({
        	  hbc: this.hbc,
            annotDefs: this.annotDefs,
            defaultVariantFilters: this.defaultVariantFilters,
            reference_populations: _.filter(this.reference_populations, function(x) {
                return x.slug !== 'AF' && !(
                    that.project_options.project_id.startsWith('project_') && x.slug == "topmed" )
            }),
            thisCallsetFilter: this.project_options.project_id && !this.project_options.project_id.startsWith('project_')
                && _.find(this.reference_populations, function(x) { return x.slug === 'AF' }),
            showPopAcFilter: this.project_options.db === "elasticsearch",
            showVartypeFilter: this.project_options.db !== "elasticsearch",
            showDeleteriousnessPredictorFilters: this.project_options.db !== "elasticsearch",
        }));

        this.createRefFreqSliders();
        if (this.project_options.db !== "elasticsearch") {
            this.vartype_widget.setElement(this.$('#vartype-widget-container')).render();
            this.polyphen_widget.setElement(this.$('#polyphen-widget-container')).render();
            this.sift_widget.setElement(this.$('#sift-widget-container')).render();
            this.muttaster_widget.setElement(this.$('#muttaster-widget-container')).render();
            this.fathmm_widget.setElement(this.$('#fathmm-widget-container')).render();
        }
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
        var ac_filters = [];
        var hom_hemi_filters = [];
        _.each(this.ref_freq_selectors, function(s, population) {
            if (s.ac !== null) {
                ac_filters.push([population, parseInt(s.ac)])
            }
            if (s.hom_hemi !== null) {
                hom_hemi_filters.push([population, parseInt(s.hom_hemi)])
            }
            if (s.ac === null && s.hom_hemi === null) {
              var freq = parseFloat(utils.freqInverse(s.freqSlider.slider("value")));
              if (freq < 1) {
                frequency_filters.push([population, freq]);
              }
            }
        });
        variantFilter.set('ref_freqs', frequency_filters);
        variantFilter.set('ref_acs', ac_filters);
        variantFilter.set('ref_hom_hemi', hom_hemi_filters);

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
	    variantFilter.set('exclude_genes', $("#exclude-gene-list-checkbox").is(':checked'))
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
    createRefFreqSliders: function() {
        var that = this;

        this.ref_freq_selectors = {};
        _.each(this.reference_populations, function(pop) {
            var freqSliderMaxVal = 11;
            var freqSliderInitialVal = freqSliderMaxVal;
            var newslider = that.$('.freq-slider[data-population="' + pop.slug + '"]').slider({
                min: 1,
                max: freqSliderMaxVal,
                step: 1,
                value: freqSliderInitialVal,
                slide: function(event, ui) {
                    that.setSlider(pop.slug, utils.freqInverse(ui.value))
                }
            });
            that.ref_freq_selectors[pop.slug] = {freqSlider: newslider, ac: null, hom_hemi: null};
            this.$( "#freqSliderLabel" ).text( utils.freqInverse(freqSliderInitialVal) );
            this.$( "#freqSliderLabel" ).css("margin-left",(freqSliderInitialVal-1)/(freqSliderMaxVal-1)*100+"%");
        });
    },

    allFreqFilterSelectChange(event) {

        var val = $(event.target).val();
        var that = this;
        if (typeof val === "undefined" || val === "---") {
            return;
        }

        _.each(this.reference_populations, function(pop) {
            if(pop.slug !== 'AF') {
              that.setSlider(pop.slug, val);
            }
        });
        this.$('#set-all-ac-filters').val( '---' );
        this.$('#set-all-hom-hemi-filters').val( '---' );
    },

    allAcFilterSelectChange(event) {

        var val = $(event.target).val();
        var that = this;
        if (typeof val === "undefined" || val === "---") {
            return;
        }

        _.each(this.reference_populations, function(pop) {
            if(pop.slug !== 'AF') {
              that.setAcSelect(pop.slug, val);
            }
        });
        this.$('#set-all-freq-filters').val( '---' );
    },

    allHomHemiFilterSelectChange(event) {

        var val = $(event.target).val();
        var that = this;
        if (typeof val === "undefined" || val === "---") {
            return;
        }

        _.each(this.reference_populations, function(pop) {
            if(pop.has_hom_hemi) {
              that.setHomHemiSelect(pop.slug, val);
            }
        });
        this.$('#set-all-freq-filters').val( '---' );
    },

    acSelectChange(event) {

        var val = $(event.target).val();
        var pop = $(event.target).data('population');
        if (typeof val === "undefined" || val === "---") {
            return;
        }

        this.setAcSelect(pop, val);
    },

    homHemiSelectChange(event) {

        var val = $(event.target).val();
        var pop = $(event.target).data('population');
        if (typeof val === "undefined" || val === "---") {
            return;
        }

        this.setHomHemiSelect(pop, val);
    },

    setSlider: function(population, val) {
	    if(this.ref_freq_selectors[population]) {
            this.$('.freq-slider-label[data-population="' + population + '"]').text( val );
            this.$('.freq-slider-label[data-population="' + population + '"]').css("margin-left", (utils.freqIndex(val)-1)/10*100+"%");
            this.$('.ac-select[data-population="' + population + '"]').val( '---' );
            this.$('.hom-hemi-select[data-population="' + population + '"]').val( '---' );
            this.ref_freq_selectors[population].freqSlider.slider('value', utils.freqIndex(val));
            this.ref_freq_selectors[population].ac = null;
            this.ref_freq_selectors[population].hom_hemi = null;
	    }
    },

    setAcSelect: function(population, val) {
	    if(this.ref_freq_selectors[population]) {
            this.$('.freq-slider-label[data-population="' + population + '"]').text('');
            this.$('.ac-select[data-population="' + population + '"]').val(val);
            this.ref_freq_selectors[population].freqSlider.slider('value', 2);
            this.ref_freq_selectors[population].ac = val;
	    }
    },

    setHomHemiSelect: function(population, val) {
	    if(this.ref_freq_selectors[population]) {
	          this.$('.freq-slider-label[data-population="' + population + '"]').text('');
            this.$('.hom-hemi-select[data-population="' + population + '"]').val(val);
            this.ref_freq_selectors[population].freqSlider.slider('value', 2);
            this.ref_freq_selectors[population].hom_hemi = val;
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
                this.updateAnnotParentCheckbox(g);
            }
        }

        if (variantFilter.variant_types) {
            this.vartype_widget.set_selections(variantFilter.variant_types);
        }

        // update frequency slider
        if (variantFilter.ref_freqs != undefined) {
            var that = this;
            _.each(this.reference_populations, function(pop) {
                var refFilter = _.find(variantFilter.ref_freqs, function(x) { return x[0] === pop.slug });
                that.setSlider(pop.slug, refFilter ? refFilter[1] : (pop.slug == "AF" && that.project_options.num_individuals < 200 ? 1 : 0.01));

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

        if (variantFilter.genes) {
            this.$('#region-genes').html(variantFilter.genes.join('\n'))
	        this.$('#exclude-gene-list-checkbox').prop('checked', variantFilter.exclude_genes)
        }

        if (variantFilter.locations) {
            this.$('#region-coords').html(variantFilter.locations.join('\n'))
        }
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
