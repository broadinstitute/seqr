window.Variant = Backbone.Model.extend({
    url: function() {
        return `/api/family/variant-annotation?project_id=${this.get('extras').project_id}&family_id=${this.get('extras').family_id}&alt=${this.get('alt')}&ref=${this.get('ref')}&xpos=${this.get('xpos')}`
    },

    parse: function(response) {
        return response.variant
    }
});

window.VariantSet = Backbone.Collection.extend({

    model: Variant,

});

window.Gene = Backbone.Model.extend({

    idAttribute: 'gene_id',
    urlRoot: '/api/gene-info',

});

window.GeneSet = Backbone.Collection.extend({

    model: Gene,

});

window.SearchProfile = Backbone.Model.extend({

    defaults: {

        "type": "variants",

        "variantQuery": {},
        "qualFilters": {},

        "variantGenotypes": {},
        "geneGenotypes": {},

        "indivsToInclude": [],
        "population": 'AF',
        'returnType': 'json',
        "min_gq": 20,
        "min_ab": 0,
        "min_vcf_filter": "pass",

        "region_genes": "",
        "region_coords": "",

    },

    // TODO
    initialize: function() { if (this.attributes.query != undefined) { this.attributes.variantQuery = this.attributes.query;}  },


    getVariantSearch: function() {
        return this.toJSON().variantQuery;
    },

    getVariantFilter: function() {
        return {
            indivs_to_filter: this.get('indivsToInclude'),
            min_gq: this.get('min_gq'),
            min_ab: this.get('min_ab'),
            min_vcf_filter: this.get('min_vcf_filter'),
            region_genes: this.get('region_genes'),
            region_coords: this.get('region_coords'),
        }
    },

});

// get rid of this
window.VariantQuery = Backbone.Model.extend({

    defaults: {

    },

});

window.Family = Backbone.Model.extend({

    defaults: {

        about_family_content: "",
        family_id: "",
        family_name: "",
        individuals: [],

    },

    individuals_with_variant_data: function() {
        var ret = [];
        _.each(this.get('individuals'), function(indiv) {
            if (indiv.has_variant_data) {
                ret.push(indiv);
            }
        });
        return ret;
    },

});

window.FamilySet = Backbone.Collection.extend({

    model: Family,

    groupByProject: function() {
        return _.groupBy(this.toJSON(), 'project_id');
    },

});

window.Inheritance = Backbone.Model.extend({

    defaults: {

        name: '',
        description: '',
        slug: '',

        mode: '',
        datatype: 'variants', // one of variants, compound_het, ...
        genotypes: {},
        haplos: {},

    },

    numGranularities: function() {
        i = 0;
        if (!_.isEmpty(this.get('genotypes'))) {
            i += 1;
        }
        if (!_.isEmpty(this.get('haplos'))) {
            i += 1;
        }
        return i;
    },

});

window.InheritanceSet = Backbone.Collection.extend({

    model: Inheritance,

});

window.VariantFilter = Backbone.Model.extend({

    defaults: {



    },

});

window.QualityFilter = Backbone.Model.extend({

    defaults: {

        min_gq: 20,
        min_ab: 35,

    },

});

window.FamilySearchFlag = Backbone.Model.extend({

    defaults: {

    },

});

