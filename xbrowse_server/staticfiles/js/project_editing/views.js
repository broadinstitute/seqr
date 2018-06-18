
//
// Initialize with {collection: IndividualSet}
//
window.IndividualListTable = Backbone.View.extend({

    template: _.template($('#tpl-individual-list').html()),

    // templates for the different modal views
    delete_samples_template: _.template($('#tpl-delete-samples').html()),
    add_phenotype_template: _.template($('#tpl-add-phenotype').html()),
    add_individuals_template: _.template($('#tpl-add-individuals').html()),
    select_from_list_template: _.template($('#tpl-select-from-list').html()),
    apply_phenotype_template: _.template($('#tpl-apply-phenotype').html()),
    select_with_phenotype_template: _.template($('#tpl-select-with-phenotype').html()),

    events: {
        "click #select-all-individuals": "select_all",
        "click .indiv-checkbox": "select_one",
        "click #save-all-individuals": "save_all_individuals",
        "click .save-one-individual": "save_one_individual",
        "click #import-from-fam": "import_from_fam",
        "click #delete-selected-samples": "delete_selected_samples",
        "click #add-phenotype": "add_phenotype",
        "click #add-individuals": "add_individuals",
        "click #select-from-list": "select_from_list",
        "click #apply-phenotype": "apply_phenotype",
        "click #select-with-phenotype": "select_with_phenotype",
    },

    render: function() {

        $(this.el).html(this.template({
            project_id: this.options.project_id,
            individuals: this.collection.toJSON(),
            project_phenotypes: this.options.project_phenotypes,
        }));

        return this;

    },

    close_modal: function() {
        this.$('#modal-inner').html('');
        this.$('#base-modal-container').modal('hide');
    },

    saveCurrentForm: function() {
        var that = this;
        _.each(this.collection.models, function(m) {
            that.update_individual_from_html(m);
        });
    },

    update_individual_from_html: function(m) {
        var that = this;

        var form_fields = that.$('[data-indiv="' + m.get('indiv_id') + '"]');

        // family ID
        m.set('family_id', form_fields.filter('[data-key="family_id"]').val() );

        // nickname
        m.set('nickname', form_fields.filter('[data-key="nickname"]').val() );

        // paternal_id
        m.set('paternal_id', form_fields.filter('[data-key="paternal_id"]').val() );

        // maternal_id
        m.set('maternal_id', form_fields.filter('[data-key="maternal_id"]').val() );

        // gender
        m.set('gender', form_fields.filter('[data-key="gender"]').val() );

        // affected
        m.set('affected', form_fields.filter('[data-key="affected"]').val());

        // review status
        m.set('case_review_status', form_fields.filter('[data-key="case_review_status"]').val());

        // phenotypes
        _.each(that.options.project_phenotypes, function(p) {
            var el = form_fields.filter('[data-key="' + p.slug + '"]');
            if (p.datatype == 'bool') {
                m.set_bool_phenotype(p.slug, $(el).val());
            }
        });
    },

    get_selected_samples: function() {
        var ret = [];
        this.$('.indiv-checkbox:checked').each(function(i, el) {
            ret.push($(el).data('indiv_id'));
        });
        return ret;
    },

    import_from_fam: function() {
        $('#import-from-fam-modal').modal();
    },

    delete_selected_samples: function() {
        var that = this;

        this.$('#modal-inner').html(that.delete_samples_template({
            to_delete: that.get_selected_samples(),
            project_id: that.options.project_id,
        }));
        this.$('#base-modal-container').modal();
    },

    add_phenotype: function() {
        var that = this;
        this.$('#modal-inner').html(that.add_phenotype_template({
            project_id: that.options.project_id,
        }));
        this.$('#base-modal-container').modal();
        this.$('#add-phenotype-submit').click(function() {
            var postdata = {};
            var formdata = $('#add-phenotype-form').serializeArray();
            for (var i=0; i<formdata.length; i++) {
                postdata[formdata[i].name] = formdata[i].value;
            }
            $.post('/project/' + that.options.project_id + '/add-phenotype',
                postdata,
                function(data) {
                    if (data.is_error) {
                        alert('Error: ' + data.error);
                    } else {
                        window.location.reload();
                    }
                }
            );
        });
    },

//    create_cohort: function() {
//        var that = this;
//        this.$('#base-modal-container').html(that.add_cohort_template({
//            project_id: that.options.project_id,
//            cohort_samples: that.get_selected_samples(),
//        }));
//        this.$('#base-modal-container').modal();
//    },

    save_all_individuals: function(e) {
        var that = this;
        if ($(e.target).hasClass('disabled')) return;
        $(e.target).addClass('disabled');
        that.saveCurrentForm();
        $.post('/project/' + that.options.project_id + '/save-all-individuals',
            { individuals_json: JSON.stringify(that.collection.toJSON()) },
            function(data) {
                $(e.target).removeClass('disabled');
                if (data.is_error) {
                    alert('error 931413');
                } else {
                    location.reload();
                }
            }
        );
    },

    save_one_individual: function(e) {
        var that = this;
        var indiv_id = $(e.target).data('indiv');
        var indiv = that.collection.find(function(x) { return x.indiv_id = indiv_id; });
        that.update_individual_from_html(indiv);
        $.post('/project/' + that.options.project_id + '/save-one-individual',
            { individual_json: JSON.stringify(indiv.toJSON()) },
            function(data) {
                if (data.is_error) {
                    alert('error 783413');
                } else {

                }
            }
        );
    },

    add_individuals: function(e) {
        var that = this;
        this.$('#modal-inner').html(that.add_individuals_template({
            project_id: that.options.project_id,
        }));
        this.$('#base-modal-container').modal();
        this.$('#add-individuals-submit').click(function() {
            var indiv_id_list = $('#add-individuals-textarea').val().split('\n');
            $.post('/project/' + that.options.project_id + '/add-individuals',
                { indiv_id_list: JSON.stringify(indiv_id_list) },
                function(data) {
                    if (data.is_error) {
                        alert('Error: ' + data.error);
                    } else {
                        window.location.reload();
                    }
                }
            );
        });
    },

    set_all_selected: function() {
        this.$('.indiv-checkbox').attr('checked', 'checked');
        this.$('tr.indiv-row').addClass('row-checked');
    },

    set_all_deselected: function() {
        this.$('.indiv-checkbox').removeAttr('checked');
        this.$('tr.indiv-row').removeClass('row-checked');
    },

    set_id_selected: function(indiv_id) {
        this.$('.indiv-checkbox[data-indiv_id="' + indiv_id + '"]').attr('checked', 'checked');
        this.$('tr.indiv-row[data-indiv_id="' + indiv_id + '"]').addClass('row-checked');
    },

    set_id_deselected: function(indiv_id) {
        this.$('.indiv-checkbox[data-indiv_id="' + indiv_id + '"]').removeAttr('checked');
        this.$('tr.indiv-row[data-indiv_id="' + indiv_id + '"]').removeClass('row-checked');
        this.$('#select-all-individuals').removeAttr('checked');
    },

    select_from_list: function() {
        var that = this;
        this.$('#modal-inner').html(that.select_from_list_template({}));
        this.$('#base-modal-container').modal();
        this.$('#select-from-list-submit').click(function() {
            var indiv_id_list = $('#select-from-list-textarea').val().split('\n');
            for (var i=0; i<indiv_id_list.length; i++) {
                var indiv_id = indiv_id_list[i];
                if (!that.collection.find(function(x) { return x.get('indiv_id') == indiv_id; })) {
                    alert('ID ' + indiv_id + ' is not in this project');
                    return;
                }
            }
            _.each(indiv_id_list, function(indiv_id) {
                that.set_id_selected(indiv_id);
            });
            that.close_modal();
        });
    },

    apply_phenotype: function() {
        var that = this;
        var selected_samples = that.get_selected_samples();
        this.$('#modal-inner').html(that.apply_phenotype_template({
            project_phenotypes: that.options.project_phenotypes,
            selected_samples: selected_samples,
        }));
        this.$('#base-modal-container').modal();
        this.$('#apply-phenotype-submit').click(function() {
            var slug = $('#apply-phenotype-select').val();
            var val = $('#apply-phenotype-bool-value').val();
            _.each(selected_samples, function(indiv_id) {
                var indiv = that.collection.find(function(x) { return x.get('indiv_id') == indiv_id; })
                indiv.set_bool_phenotype(slug, val);
            });
            that.close_modal();
            that.render();
        });
    },

    select_with_phenotype: function() {
        var that = this;
        this.$('#modal-inner').html(that.select_with_phenotype_template({
            project_phenotypes: that.options.project_phenotypes,
        }));
        this.$('#base-modal-container').modal();
        this.$('#select-with-phenotype-submit').click(function() {
            var slug = $('#select-with-phenotype-select').val();
            var val = $('#select-with-phenotype-bool-value').val();
            var bool_val = null;
            if (val == 'T') bool_val = true;
            if (val == 'F') bool_val = false;
            that.collection.each(function(indiv) {
                if (indiv.get_phenotype(slug) == bool_val) {
                    that.set_id_selected(indiv.get('indiv_id'));
                }
            });
            that.close_modal();
        });
    },

    select_all: function(e) {
        var checked = $(e.target).is(':checked');
        if (checked) {
            this.set_all_selected();
        } else {
            this.set_all_deselected();
        }
    },

    select_one: function(e) {
        var checked = $(e.target).is(':checked');
        var indiv_id = $(e.target).data('indiv_id');
        if (checked) {
            this.set_id_selected(indiv_id);
        } else {
            this.set_id_deselected(indiv_id);
        }
    },

});

