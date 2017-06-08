window.Individual = Backbone.Model.extend({

    defaults: {
        indiv_id: "",
        family_id: "",
        nickname: "",
        gender: 'U',
        affected: 'U',
        maternal_id: "",
        paternal_id: "",
        other_notes: "",
        phenotypes: {},

    },

    get_phenotype: function(slug) {
        if (this.get('phenotypes')[slug] == undefined) {
            return null;
        } else {
            return this.get('phenotypes')[slug];
        }
    },

    set_bool_phenotype: function(slug, value) {
        if (value == 'T') {
            this.get('phenotypes')[slug] = true;
        } else if (value == 'F') {
            this.get('phenotypes')[slug] = false;
        } else {
            this.get('phenotypes')[slug] = null;
        }
    },

});

window.IndividualSet = Backbone.Collection.extend({

    model: Individual,

    comparator: function(indiv) {
        return indiv.get('family_id');
    },

    // remove this indiv from the set, and ensure that no parental relationships remain
    remove_id: function(indiv_id) {

        _.each(this.models, function(model) {
            if (model.get('paternal_id') == indiv_id) {
                model.set('paternal_id', '.');
            }
            if (model.get('maternal_id') == indiv_id) {
                model.set('maternal_id', '.');
            }
        });

        // TODO tried to use collection.where, but need to upgrade to new backbone first
        var indivs = this.find(function(m) { return m.get('indiv_id') == indiv_id; });
        this.remove(indivs);

    },

});


