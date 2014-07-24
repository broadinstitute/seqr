window.EditVariantTagsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family = options.family;
        this.variant = options.variant;
        this.after_finished = options.after_finished;
    },

    template: _.template(
        $('#tpl-edit-variant-tags').html()
    ),

    events: {
        'click #edit-tags-save': 'save',
    },

    render: function(event) {
        var that = this;
        $(this.el).html(this.template({
            variant: that.variant,
            tags: that.hbc.project_options.tags,
        }));
        return this;
    },

    save: function() {
        var that = this;
        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
            tag_slugs: "",
        };
        this.$('.variant-tag-checkbox:checked').each(function(t, i) {
            postData.tag_slugs += $(i).data('tag') + '|';
        });

        $.get(URL_PREFIX + 'api/edit-variant-tags', postData,
            function(data) {
                if (data.is_error) {
                    alert('error; please refresh the page')
                } else {
                    that.after_finished(data.variant);
                }
            }
        );
    },
});
