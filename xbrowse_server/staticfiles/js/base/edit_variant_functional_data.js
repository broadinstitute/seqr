window.EditVariantFunctionalDataView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family = options.family;
        this.variant = options.variant;
        this.after_finished = options.after_finished;
    },

    template: _.template(
        $('#tpl-edit-variant-functional-data').html()
    ),

    events: {
        'click #edit-tags-save': 'save',
        'click #edit-tags-cancel': 'cancel',
        'keyup': 'save',
        'change .variant-tag-checkbox': 'select_tag'
    },

    render: function(event) {
        var that = this;
        $(this.el).html(this.template({
            variant: that.variant,
            tags: that.hbc.project_options.functional_data,
        }));

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

        var hasError = false;
        var tags = this.$('.variant-tag-checkbox:checked').map(function(t, i) {
            var tag = $(i).data('tag');
            var metadata = $(`.metadata-input[data-tag="${tag}"]`)
            if (metadata.attr('required') && !metadata.val()) {
                $(`.metadata[data-tag="${tag}"]`).addClass('has-error');
                hasError = true;
            } else {
                $(`.metadata[data-tag="${tag}"]`).removeClass('has-error');
            }
            return { tag: tag, metadata: metadata.val() }
        }).get();

        if (hasError) {
            return
        }

        var that = this;
        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
            tags: tags
        };

        if(window.location.href.indexOf("/variants/") < 0 && window.location.href.indexOf("/saved-variants") < 0) {
            postData.search_url = window.location.href;  //if this isn't the tags page, save the search url
        } else {
            postData.search_url = "";
        }

        $('#edit-tags-save').addClass('disabled')

        $.post('/api/add-or-edit-variant-functional-data', JSON.stringify(postData),
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

    select_tag: function(event) {
        var tag = $(event.target).data('tag')
        $(`.metadata[data-tag="${tag}"]`).toggle($(event.target).checked);
    },
});
