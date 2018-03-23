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
        'click #edit-functional-data': 'edit_functional_data',
        'keyup': 'save',
        'change .variant-tag-checkbox': 'set_allow_edit_functional'
    },

    render: function(event, selected_tags) {
        var that = this;
        $(this.el).html(this.template({
            selected_tags: selected_tags || that.variant.extras.family_tags.map(tag => tag.tag),
            tags: that.hbc.project_options.tags,
        }));

        this.set_allow_edit_functional();

        this.$('.icon-popover').popover({
          trigger: 'hover',
        });

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

    set_allow_edit_functional: function() {
        if ($('.variant-tag-checkbox:checked[data-category="CMG Discovery Tags"]').length > 0) {
            $('#edit-functional-data').attr('disabled', false);
        } else {
            $('#edit-functional-data').attr('disabled', true);
        }
    },

    edit_functional_data: function () {
        var that = this;
        var selected_tags = $('.variant-tag-checkbox:checked').map((t, i) => $(i).data('tag')).get()
        this.hbc.edit_family_functional_data(this.variant, this.family, function(variant) {
            that.variant = variant;
            that.render(_, selected_tags);
        });
    }
});
