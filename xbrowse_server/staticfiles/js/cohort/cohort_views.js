var AddCohortView = Backbone.View.extend({
    template: _.template($('#tpl-add-cohort').html()),
    form_template: _.template($('#tpl-add-cohort-form').html()),
    select_with_phenotype_template: _.template($('#tpl-select-individuals-with-phenotype').html()),
    select_from_list_template: _.template($('#tpl-select-from-indiv-id-list').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.individuals = options.individuals;
    },
    events: {
        "click #add-cohort-submit": "add_cohort_submit",
        "click #select-with-phenotype": "select_with_phenotype",
        "click #select-from-list": "select_from_list",
    },
    render: function() {
        $(this.el).html(this.template({
            individuals: this.individuals,
            project_spec: this.project_spec,
        }));
        this.indivs_view = new IndividualsView({
            individuals: this.individuals,
            project_spec: this.project_spec,
            selectable: true,
            indiv_id_link: false,
        });
        this.$('#individuals-table-container').html(this.indivs_view.render().el);
        return this;
    },

    add_cohort_submit: function() {
        var that = this;
        var selected_indivs = this.indivs_view.get_selected_indiv_ids();
        if (selected_indivs.length == 0) {
            alert('No individuals are selected');
            return;
        }
        this.$('#modal-inner').html(this.form_template({
            indiv_ids: selected_indivs,
            project_id: this.project_spec.project_id
        }));
        this.$('#add-cohort-submit2').click(function() {
            var postdata = {
                indiv_ids: selected_indivs.join('|'),
                name: that.$('#id_name').val(),
                description: that.$('#id_description').val(),
            };
            $.post('#',
                postdata,
                function(data) {
                    if (data.is_error == false) {
                        window.location.href = data.next_page;
                    } else {
                        alert("There was an error: " + data.error);
                    }
                }
            );
        });
        this.$('#modal-base').modal();
    },

    select_with_phenotype: function() {
        var that = this;
        var phenotype_view = new SelectPhenotypeView({
            project_spec: that.project_spec,
        });
        this.$('#base-modal-container').html(this.select_with_phenotype_template());
        this.$('.select-phenotype-container').html(phenotype_view.render().el)
        this.$('#base-modal-container').modal();
        this.$('#select-with-phenotype-submit').click(function() {
            var pheno_filter = phenotype_view.get_filter();
            that.indivs_view.select_with_phenotype(pheno_filter);
            that.close_modal();
        });
    },


    select_from_list: function() {
        var that = this;
        this.$('#base-modal-container').html(that.select_from_list_template({}));
        this.$('#base-modal-container').modal();
        this.$('#select-from-family-id-list-submit').click(function() {
            var indiv_id_list = $('#select-from-indiv-id-list-textarea').val().split('\n');
            _.each(indiv_id_list, function(indiv_id) {
                var indiv = _.find(that.individuals, function(x){return x.indiv_id==indiv_id;});
                if (indiv == undefined) {
                    alert('ID ' + indiv_id + ' is not in this project');
                    return;
                }
            });
            _.each(indiv_id_list, function(indiv_id) {
                that.indivs_view.set_id_selected(indiv_id);
            });
            that.close_modal();
        });
    },

    close_modal: function() {
        this.$('#base-modal-container').html('');
        this.$('#base-modal-container').modal('hide');
    },

});

/*
Select at top of Cohort Variant Search
 */
window.CohortSelectGenotypesView = Backbone.View.extend({

    initialize: function(options) {
        this.cohort = options.cohort;
        this.hbc = options.hbc;
    },

    template: _.template($('#tpl-cohort-select-genotypes').html()),

    render: function(event) {

        $(this.el).html(this.template());

        this.chooseGenotypeFilterView = new ChooseGenotypeFilterView({
            hide_prefill: true,
            family: this.cohort,
            genotypeOptions: this.options.genotypeOptions,
            burdenFilterOptions: this.options.burdenFilterOptions,
            familyGenotypeFilters: this.options.familyGenotypeFilters,
        });

        this.$('#cohort-inheritance-section-container').html(this.chooseGenotypeFilterView.render().el);

        utils.initializeHovers(this);

        return this;
    },

    getGenotypeFilter: function() {
        return this.chooseGenotypeFilterView.getGenotypes();
    },

    setGenotypeFilter: function(genotype_filter) {
        this.chooseGenotypeFilterView.drawFromFilter(genotype_filter);
    },

});


window.SelectCohortSearchMethodView = Backbone.View.extend({

    template: _.template($('#tpl-select-cohort-search-method').html()),

    render: function(event) {
        $(this.el).html(this.template({
            cohort: this.cohort
        }));
        return this;
    },

    getInheritanceMode: function() {
        return this.$('input[name="cohort_inheritance"]:checked').val();
    },

    setInheritanceMode: function(inheritance_mode) {
        if (inheritance_mode == undefined) {
            inheritance_mode = "";
        }
        this.$('input[name="cohort_inheritance"]').prop('checked', false);
        this.$('input[name="cohort_inheritance"][value="' + inheritance_mode + '"]').prop('checked', true);
    },

    setDetailsView: function(inheritanceMode) {
        this.$('label.inheritance-mode').removeClass('active');
        this.$('label.inheritance-mode').hide();
        var target = this.$('input[name="cohort_inheritance"][value="' + inheritanceMode + '"]').parent();
        target.show()
        target.addClass('active');
    },


});

window.CohortResultsView = Backbone.View.extend({

    className: 'row',

    initialize: function(options) {
        this.hbc = options.hbc;
    },

    render: function(event) {

        var that = this;

        $(this.el).html(this.template({
            utils: utils,
            genes: this.options.genes
        }));

        _.each(this.options.genes, function(gene) {
            var view = new CohortSingleGeneView({
                hbc: that.hbc,
                gene: gene,
            });
            that.$('#resultsTableBody').append(view.render().el);
        });

        jQuery.fn.dataTableExt.oSort['intComparer-asc'] = function (a, b) {
            var value1 = parseInt($(a).text());
            var value2 = parseInt($(b).text());
            return ((value1 < value2) ? -1 : ((value1 > value2) ? 1 : 0));
        };

        jQuery.fn.dataTableExt.oSort['intComparer-desc'] = function (a, b) {
            var value1 = parseInt($(a).text());
            var value2 = parseInt($(b).text());
            return ((value1 < value2) ? 1 : ((value1 > value2) ? -1 : 0));
        };

        $.fn.dataTableExt.oSort['scientific-desc'] = function(a,b) {
                x = parseFloat(a);
                y = parseFloat(b);
                return ((x < y) ? 1 : ((x > y) ? -1 : 0));
        };

        $.fn.dataTableExt.oSort['scientific-asc'] = function(a,b) {
                x = parseFloat(a);
                y = parseFloat(b);
                return ((x < y) ? -1 : ((x > y) ? 1 : 0));
        }

        this.$('#resultsTable').dataTable({
            "bPaginate": false,
            "aoColumnDefs": [
                { 'sType': "intComparer", 'aTargets': [2] },
                { 'sType': "scientific", 'aTargets': [3] },

            ],
            "bFilter": false,
            "bInfo": false,
        });

        utils.initializeHovers(this);

        return this;
    },

    template: _.template($('#tpl-cohort-results').html())

});

window.CohortSingleGeneView = Backbone.View.extend({

    events: {
        "click .variants-link": "variantsLink",
        "click .gene-info-link": "geneLink",
    },

    tagName: 'tr',

    initialize: function(options) {
        this.hbc = options.hbc;
    },

    render: function(event) {

        $(this.el).html(this.template( {
            gene: this.options.gene,
            utils: utils,
        }));

        return this;
    },

    template: _.template($('#tpl-cohort-single-gene-view').html()),

    geneLink: function(event) {
        var target = $(event.target).closest('a');
        var gene_id = target.data('gene_id');
        hbc.gene_info(gene_id);
    },

    variantsLink: function(event) {
        var target = $(event.target).closest('a');
        var gene_id = target.data('gene_id');
        hbc.gene_variants(gene_id);
    },

});


window.CohortVariantsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.gene_id = options.gene_id;
        this.cohort = options.cohort;
        this.search_spec = options.search_spec;
    },

    render: function(event) {
        var that = this;

        $(this.el).html(this.template());

        // start by setting content to loading
        that.$('.variants-container').html(this.loading_template());

        var postdata = {
            gene_id: this.gene_id,
            project_id: this.cohort.project_id,
            cohort_id: this.cohort.cohort_id,
            inheritance_mode: this.search_spec.inheritance_mode,
            variant_filter: JSON.stringify(this.search_spec.variant_filter),
            quality_filter: JSON.stringify(this.search_spec.quality_filter),
        };

        $.get('/api/cohort-gene-search-variants', postdata,
            function(data) {
                that.$('.variants-container').html('');
                if (!data.is_error) {
                    _.each(data.variants, function(variant) {
                        var individuals = _.filter(that.cohort.individuals, function(i) { return variant.genotypes[i.indiv_id].num_alt != 0; });
                        var view = new BasicVariantView({
                            hbc: that.hbc,
                            variant: variant,
                            show_genotypes: true,
                            individuals: individuals,
                            show_gene: false,
                        });
                        that.$('.variants-container').append(view.render().el);
                    });
                }
            }
        );
        return this;
    },

    template: _.template($('#tpl-cohort-variants').html()),
    loading_template: _.template($('#tpl-modal-loading').html()),
});


window.CohortQualityFilterView = Backbone.View.extend({

    template: _.template($('#tpl-cohort-quality-filter').html()),

    events: {
        "change #quality-defaults-select": "qualityDefaultChange",
    },

    initialize: function(options) {
        this.hbc = this.options.hbc;
    },

    render: function(event) {

        $(this.el).html(this.template({
            defaultQualityFilters: this.options.defaultQualityFilters,
        }));

        this.gqSlider = new SliderWidgetView({min: 0, max: 100});
        this.$('#gq-quality-container').html(this.gqSlider.render().el);

        this.abSlider = new SliderWidgetView({min: 0, max: 50});
        this.$('#ab-quality-container').html(this.abSlider.render().el);

        this.hetSlider = new SliderWidgetView({min: 0, max: 100});
        this.hetSlider.setVal(100);
        this.$('#het-ratio-container').html(this.hetSlider.render().el);

        this.homAltSlider = new SliderWidgetView({min: 0, max: 100});
        this.homAltSlider.setVal(100);
        this.$('#hom-alt-ratio-container').html(this.homAltSlider.render().el);

        this.passSlider = new SliderWidgetView({min: 0, max: 100});
        this.$('#pass-ratio-container').html(this.passSlider.render().el);

        utils.initializeHovers(this);

        return this;
    },

    getQualityFilter: function() {

        var qualityFilter = {};

        if (this.$('#filter-select').val() == 'pass') {
            qualityFilter['vcf_filter'] = 'pass';
        }

        qualityFilter['min_gq'] = this.gqSlider.getVal();
        qualityFilter['min_ab'] = this.abSlider.getVal();

        var hetVal = this.hetSlider.getVal();
        if (hetVal < 100) {
            qualityFilter['het_ratio'] = hetVal;
        }
        var homAltVal = this.homAltSlider.getVal();
        if (homAltVal < 100) {
            qualityFilter['hom_alt_ratio'] = homAltVal;
        }
        var passVal = this.passSlider.getVal();
        if (passVal > 0) {
            qualityFilter['pass_ratio'] = passVal;
        }

        return qualityFilter;

    },

    loadFromQualityFilter: function(qualityFilter) {

        if (qualityFilter == undefined) {
            qualityFilter = {};
        }

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
            // TODO: should have a disable() method that sets to null instead of 0
            this.gqSlider.setVal(0);
        }

        // AB
        if (qualityFilter.min_ab != undefined) {
            this.abSlider.setVal(qualityFilter.min_ab);
        } else {
            this.abSlider.setVal(0);
        }

        // het ratio
        if (qualityFilter.het_ratio != undefined) {
            this.hetSlider.setVal(qualityFilter.het_ratio);
        } else {
            this.hetSlider.setVal(100);
        }

        // hom ratio
        if (qualityFilter.hom_alt_ratio != undefined) {
            this.homAltSlider.setVal(qualityFilter.hom_alt_ratio);
        } else {
            this.homAltSlider.setVal(100);
        }

        // pass ratio
        // hom ratio
        if (qualityFilter.pass_ratio != undefined) {
            this.passSlider.setVal(qualityFilter.pass_ratio);
        } else {
            this.passSlider.setVal(0);
        }
    },

    qualityDefaultChange: function(event) {
        var slug = $(event.target).val();
        var qualityDefault = _.find(this.options.defaultQualityFilters, function(x) { return x.slug == slug });
        if (qualityDefault != undefined) {
            this.loadFromQualityFilter(qualityDefault.quality_filter);
        }
    }

});
