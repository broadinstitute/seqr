window.AddOrEditVariantNoteView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.family = options.family;
        this.variant = options.variant;
        this.after_finished = options.after_finished;
        if(options.note_id) {
            this.note_id = options.note_id;
            this.init_note_text = "";
            for(var i = 0; i < this.variant.extras.family_notes.length; i+=1 ) {
                var note = this.variant.extras.family_notes[i];
                if(note.note_id == this.note_id) {
                    this.init_note_text = note.note;
                    break;
                }
            }
        }
    },

    template: _.template(
        $('#tpl-add-variant-note').html()
    ),

    events: {
        'keyup #flag_inheritance_notes' : 'save',
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

        this.$('#flag_inheritance_notes').val(this.init_note_text);

        return this;
    },

    save: function(event) {
        if(event.keyCode && event.keyCode != 13){
            //only save when 'Enter' is pressed
            return;
        }

        var that = this;

        var note_text = this.$('#flag_inheritance_notes').val();
        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
            note_text: note_text,
            note_id: this.note_id,
            tags: '',
        };

        $.get(URL_PREFIX + 'api/add-or-edit-variant-note', postData,
            function(data) {
                if (data.is_error) {
                    alert(data.error);
                } else {
                    that.after_finished(data.variant);
                }
            }
        );
    },
});
