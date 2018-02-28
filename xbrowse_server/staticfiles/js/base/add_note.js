window.AddOrEditNoteView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        this.note_type = options.note_type,
        this.family = options.family;
        this.variant = options.variant;
        this.allow_clinvar_submission = options.allow_clinvar_submission;
        this.after_finished = options.after_finished;
        this.init_submit_to_clinvar_checked = false;
        this.init_note_text = "";
        if(options.note_id) {
            this.note_id = options.note_id;
            for(var i = 0; i < options.all_notes.length; i+=1 ) {
                var note = options.all_notes[i];
                if(note.note_id == this.note_id) {
                    this.init_note_text = note.note;
		            this.init_submit_to_clinvar_checked = note.submit_to_clinvar;
                    break;
                }
            }
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
        var that = this;
        $(this.el).html(this.template({
            note_type: this.note_type,
            note_text: this.init_note_text,
            allow_clinvar_submission: this.allow_clinvar_submission,
            submit_to_clinvar_checked: this.init_submit_to_clinvar_checked,
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
	var submit_to_clinvar_checkbox = this.$('#submit_to_clinvar').is(':checked');

        var postData = {
            project_id: this.family.get('project_id'),
            family_id: this.family.get('family_id'),
            xpos: this.options.variant.xpos,
            ref: this.options.variant.ref,
            alt: this.options.variant.alt,
            note_text: note_text,
            note_id: this.note_id,
	    submit_to_clinvar: submit_to_clinvar_checkbox,
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
