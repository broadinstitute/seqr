window.AddVariantNoteView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family = options.family;
        this.variant = options.variant;
        this.after_finished = options.after_finished;
    },

    template: _.template(
        $('#tpl-add-variant-note').html()
    ),

    events: {
        'click #add-flag-save': 'save',
    },

    render: function(event) {
        var that = this;
        $(this.el).html(this.template({
            variant: that.variant,
            suggested_inheritance: that.suggested_inheritance,
            tags: that.hbc.project_options.tags,
        }));
        var variant_view = new BasicVariantView({hbc: that.hbc, variant: that.variant});
        this.$('.variant-container').html(variant_view.render().el);
        // TODO: add back
        //var flags_view = new VariantFlagsView({flags: that.variant.extras.search_flags});
        //this.$('.flags-display').html(flags_view.render().el);
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

        var note_text = this.$('#flag_inheritance_notes').val();
        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
            note_text: note_text,
            tags: '',
        };

        //that.$('#add-flag-save').attr('disabled', 'disabled');

        $.get(URL_PREFIX + 'api/add-variant-note', postData,
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
