var AddFamilyGroupView = Backbone.View.extend({
    template: _.template($('#tpl-add-family-group').html()),
    form_template: _.template($('#tpl-add-family-group-dialog').html()),
    select_with_phenotype_template: _.template($('#tpl-select-families-with-phenotype').html()),
    select_from_list_template: _.template($('#tpl-select-from-family-id-list').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.families = options.families;
    },
    events: {
        "click #add-family-group-submit": "add_family_group_submit",
        "click #select-with-phenotype": "select_with_phenotype",
        "click #select-from-list": "select_from_list",
    },
    render: function() {
        $(this.el).html(this.template({
            families: this.families,
            project_spec: this.project_spec,
        }));

        this.families_view = new FamiliesView({
            families: this.families,
            project_spec: this.project_spec,
            selectable: true,
            family_id_link: false,
            show_case_review_status: false,
        });
        this.$('#families-table-container').html(this.families_view.render().el);
        return this;
    },

    add_family_group_submit: function() {
        var that = this;
        var selected_fams = this.families_view.get_selected_family_ids();
        if (selected_fams.length == 0) {
            alert('No families are selected');
            return;
        }
        this.$('#modal-inner').html(this.form_template({
            family_ids: selected_fams,
            project_id: this.project_spec.project_id
        }));
        this.$('#add-family-group-submit2').click(function() {
            var postdata = {
                family_ids: selected_fams.join('|'),
                name: that.$('#id_name').val(),
                description: that.$('#id_description').val(),
            };
            $.post('/project/'+that.project_spec.project_id+'/add-family-group-submit',
                postdata,
                function(data) {
                    if (data.is_error == false) {
                        window.location.href = data.new_url;
                    } else {
                        alert("There was an error: " + data.error);
                    }
                }
            );
        });
        this.$('#base-modal-container').modal();
    },

    select_with_phenotype: function() {
        var that = this;
        var phenotype_view = new SelectPhenotypeView({
            project_spec: that.project_spec,
        });
        this.$('#modal-inner').html(this.select_with_phenotype_template());
        this.$('.select-phenotype-container').html(phenotype_view.render().el)
        this.$('#base-modal-container').modal();
        this.$('#select-with-phenotype-submit').click(function() {
            var pheno_filter = phenotype_view.get_filter();
            that.families_view.select_with_phenotype(pheno_filter);
            that.close_modal();
        });
    },


    select_from_list: function() {
        var that = this;
        this.$('#modal-inner').html(that.select_from_list_template({}));
        this.$('#base-modal-container').modal();
        this.$('#select-from-family-id-list-submit').click(function() {
            var family_id_list = $('#select-from-family-id-list-textarea').val().split('\n');
            _.each(family_id_list, function(family_id) {
                var fam = _.find(that.families, function(x){return x.family_id==family_id;});
                if (fam == undefined) {
                    alert('ID ' + family_id + ' is not in this project');
                    return;
                }
            });
            _.each(family_id_list, function(family_id) {
                that.families_view.set_id_selected(family_id);
            });
            that.close_modal();
        });
    },

    close_modal: function() {
        this.$('#modal-inner').html('');
        this.$('#base-modal-container').modal('hide');
    },

});


var VariantsInSingleFamilyView = Backbone.View.extend({

    initialize: function(options) {
        this.o = options.o;
        this.family_group = options.family_group;
        this.hbc = options.hbc;
    },

    template: _.template($('#tpl-variants-in-single-family').html()),

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            o: this.o,
        }));

        var family = new Family(that.family_group.families[that.o.family_id]);
        if (this.o.variants.length > 0) {
            var view = new BasicVariantsTable({
                hbc: that.hbc,
                variants: that.o.variants,
                show_genotypes: true,
                individuals: family.individuals_with_variant_data(),
            });
            this.$('.vartablecontainer').append(view.render().el);
        }
        return this;
    },

});

var VariantsByFamilyView = Backbone.View.extend({
    initialize: function(options) {
        this.hbc = options.hbc;
        this.variants_by_family = options.variants_by_family;
        this.family_group = options.family_group;
    },

    template: _.template($('#tpl-variants-by-family').html()),

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            variants_by_family: this.variants_by_family,
        }));
        _.each(this.variants_by_family, function(o) {
            var view = new VariantsInSingleFamilyView({
                hbc: that.hbc,
                o: o,
                family_group: that.family_group,
            });
            that.$('.multiple-variant-tables-container').append(view.render().el);
        });
        return this;
    },
});

