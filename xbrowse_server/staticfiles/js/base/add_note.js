var AddOrEditNoteView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.after_finished = options.after_finished;
        if(options.note_id) {
            this.note_id = options.note_id;
            this.init_note = this.init_note();
        }
    },

    template: _.template(
        $('#tpl-add-note').html()
    ),

    events: {
        'keyup #flag_inheritance_notes' : 'save',
        'click #add-flag-save': 'save',
    },

    render: function(event) {
        $(this.el).html(this.template({
            note_type: this.note_type,
            note_text: this.init_note.note || "",
            allow_clinvar_submission: this.allow_clinvar_submission,
            submit_to_clinvar_checked: this.init_note.submit_to_clinvar || false,
        }));

        var preventDefault = function(event) {
          if (event.keyCode == 13) {
            //event.preventDefault();
            return false;
          }
        };

        //this.$('#flag_inheritance_notes').keydown(preventDefault);
        //this.$('#flag_inheritance_notes').keypress(preventDefault);
        this.$('#flag_inheritance_notes').keyup(preventDefault);

        return this;
    },

    save: function(event) {
        if(event.keyCode && event.keyCode != 13){
            //only save when 'Enter' is pressed
            return;
        }

        var that = this;
	
        var note_text = this.$('#flag_inheritance_notes').val();

        var postData = _.extend({
            note_text: note_text,
            note_id: this.note_id,
        }, this.note_metadata());

        $.get(URL_PREFIX + 'api/add-or-edit-' + this.note_type.toLowerCase() + '-note', postData,
            function(data) {
                if (data.is_error) {
                    alert(data.error);
                } else {
                    that.after_finished(data);
                }
            }
        );
    },

    init_note: function () {
        return this.options.note;
    },

    note_metadata: function () {
        return {};
    }
});

window.AddOrEditVariantNoteView = AddOrEditNoteView.extend({

    note_type: 'Variant',
    allow_clinvar_submission: true,

    init_note: function (note_id) {
        for(var i = 0; i < this.options.variant.extras.family_notes.length; i+=1 ) {
            var note = this.options.variant.extras.family_notes[i];
            if (note.note_id == this.note_id) {
                return note;
            }
        }
    },

    note_metadata: function () {
        return {
            project_id: this.options.family.get('project_id'),
            family_id: this.options.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
	        submit_to_clinvar: this.$('#submit_to_clinvar').is(':checked'),
            tags: '',
        };
    }
});

window.AddOrEditGeneNoteView = AddOrEditNoteView.extend({

    note_type: 'Gene',
    allow_clinvar_submission: false,

    note_metadata: function () {
        return {
            gene_id: this.options.gene_id,
        };
    }
});

