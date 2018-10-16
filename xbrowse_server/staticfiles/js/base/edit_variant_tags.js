window.EditVariantTagsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family = options.family;
        this.variant = options.variant;
        this.after_finished = options.after_finished;
        this.selected_tags = this.variant.extras.family_tags.map(tag => tag.tag)
    },

    template: _.template(
        $('#tpl-edit-variant-tags').html()
    ),

    events: {
        'click #edit-tags-save': 'save',
        'click #edit-tags-cancel': 'cancel',
        'click #edit-functional-data': 'edit_functional_data',
        'keyup': 'save',
        'change .variant-tag-checkbox': 'tag_selection_changed'
    },

    render: function() {
        var that = this;
        $(this.el).html(this.template({
            selected_tags: this.selected_tags,
            tags: that.hbc.project_options.tags,
            allow_functional: that.hbc.project_options.functional_data,
        }));

        this.tag_selection_changed();

        this.$('.icon-popover').popover({
          trigger: 'hover',
        });

        this.delegateEvents();

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

        $('#edit-tags-save').addClass('disabled')

        $.get('/api/add-or-edit-variant-tags', postData,
            function(data) {
                $('#edit-tags-save').removeClass('disabled')
                if (data.is_error) {
                    alert('Error: ' + data.error);
                } else {
                    that.after_finished(data);
                }
            }
        );
    },

    cancel: function() {
      this.hbc.popModal();
    },

    tag_selection_changed: function() {
        this.selected_tags =  this.$('.variant-tag-checkbox:checked').map((t, i) => $(i).data('tag')).get()
        if (this.$('.variant-tag-checkbox:checked[data-category="CMG Discovery Tags"]').length > 0) {
            $('#edit-functional-data').attr('disabled', false);
        } else {
            this.$('#edit-functional-data').attr('disabled', true);
        }
    },

    edit_functional_data: function () {
        var that = this;
        this.hbc.edit_family_functional_data(this.variant, this.family, function(variant) {
            that.variant = variant;
        });
    },
});
