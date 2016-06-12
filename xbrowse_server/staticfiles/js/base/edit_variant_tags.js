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
        'keyup': 'save',
    },

    render: function(event) {
        var that = this;
        $(this.el).html(this.template({
            variant: that.variant,
            tags: that.hbc.project_options.tags,
        }));
        return this;
    },

    save: function(event) {
        if(event.keyCode && event.keyCode != 13){
            //only save when 'Enter' is pressed
            return;
        }

        var that = this;
        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
            tag_slugs: "",
        };

        if(window.location.href.indexOf("/variants/") < 0 && window.location.href.indexOf("/saved-variants") < 0) {
            postData["search_url"] = window.location.href;  //if this isn't the tags page, save the search url
        } else {
            postData["search_url"] = "";  //if this isn't the tags page, save the search url
        }

        this.$('.variant-tag-checkbox:checked').each(function(t, i) {
            postData.tag_slugs += $(i).data('tag') + '|';
        });

        $.get(URL_PREFIX + 'api/add-or-edit-variant-tags', postData,
            function(data) {
                if (data.is_error) {
                    alert('Error: ' + data.error);
                } else {
                    that.after_finished(data.variant);
                }
            }
        );
    },
});
