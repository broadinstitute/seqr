window.ModalQueueView = Backbone.View.extend({

    initialize: function() {
        this.hbc = this.options.hbc;
    },

    template: _.template(
        $('#tpl-modal-queue').html()
    ),

    render: function() {
        var that = this;
    	$(this.el).html(this.template());
        this.$('.modal').modal({
            keyboard: true,
            backdrop: 'static',
        });
        this.$('.modal').on('hidden.bs.modal', function () {
            // So weird to reference app from here without a delegate
            that.hbc.popModal();
        });
        return this;
    },

    show: function() {
    	this.$('.modal').modal('show');
    },

    hide: function() {
        // Only hide if not already hidden
        if (this.$('.modal').hasClass('in')) {
            this.$('.modal').modal('hide');
        }
    },

    setTitle: function(title) {
        if (title == null || title == "") {
            this.$('.modal-header').hide();
        } else {
            this.$('#modal-queue-title').html(title);
            this.$('#modal-queue-title').show();
        }
    },

    setContent: function(el) {
        this.$('#modal-queue-content').html(el);
    },

});

window.XLoadingView = Backbone.View.extend({
    template: _.template($('#tpl-loading-view').html()),
    className: "loading-view",
    render: function() {
        $(this.el).html(this.template());
        return this;
    },
});



/*
This is essentially a dispatcher for all xbrowse javascript.
All pages with xbrowse JS should have a Head Ball Coach [1] that holds page variables and presents modals
Presented views should have a pointer back to the HBC, in case they want to trigger a new view
For example, if a view displays a gene name and wants to link to the modal window: self.hbc.show_gene()

Any page that wants to display xbrowse views should create a HeadBallCoach first.
Extends Backbone.Router, so can optionally use Backbone.Router.routes for url mapping

FYI this follows no javascript MV* conventions - though I imagine it would ease the transition to a framework
this is a purely custom solution that uniquely suits us

[1] http://espn.go.com/blog/sec/post/_/id/68772/the-head-ball-coach-has-still-got-it
 */
window.HeadBallCoach = Backbone.Router.extend();
_.extend(HeadBallCoach.prototype, {

    dictionary: DICTIONARY,
    project_options: PROJECT_OPTIONS,

    _modalView: undefined,
    _modalQueue: [],

    gene_info: function(gene_id) {
        var that = this;
        this.push_modal_loading(gene_id);

        new Gene({
            gene_id: gene_id
        }).fetch({
            success: function(model, response) {
                var view;
                if (response.found_gene == true) {
                    view = new GeneDetailsView({gene: response.gene, hbc: that});
                } else {
                    view = new GeneErrorView();
                }
                that.replace_loading_with_view(view);
            },
            error: function() {
                that.replace_loading_with_view(new GeneErrorView());
            }
        });
    },

    variant_info: function(variant) {
        var that = this;

        if (variant.annotation.vep_annotation) {
            var view = new AnnotationDetailsView({
                variant: variant
            });
            that.pushModal("title", view);
        } else {
            that.push_modal_loading()
            new Variant(variant).fetch({
              success: function(model) {
                that.replace_loading_with_view(new AnnotationDetailsView({variant: model.toJSON()}));
              },
              error: function() {
                that.replace_loading_with_view(new AnnotationDetailsView({variant: variant}));
            }
            })
        }
    },

    variant_infos: function(variant) {
        var view = new AnnotationDetailsView({
            variant: variant
        });
        this.pushModal("title", view);
    },

    pushModal: function(title, view) {
        this._modalQueue.push({
            title: title,
            view: view,
        });
        this.updateModal();
    },

    popModal: function() {
        this._modalQueue.splice(this._modalQueue.length-1,1);
        this.updateModal();
    },

    resetModal: function() {
        this._modalQueue = [];
        this.updateModal();
    },

    // update the modal display, showing the top item in queue if exists
    // can be called no matter state of the queue - empty or whatever
    updateModal: function() {

        var that = this;
        // nothing in queue? delete modal view if it exists
        if (that._modalQueue.length == 0) {
            if (that._modalView) {
                that._modalView.hide();
            }
        }
        else {
            // do we need to create modal view?
            if (that._modalView == undefined) {
                that._modalView = new ModalQueueView({hbc: that});
                $('body').append(that._modalView.render().el);
            }
            that._modalView.show();
            // note that render() is called on each display
            // almost like that's what it was designed for or something
            var nextObj = that._modalQueue[that._modalQueue.length-1];
            that._modalView.setTitle(nextObj.title);
            that._modalView.setContent(nextObj.view.render().el);

        }
    },

    push_modal_loading: function(title) {
        var loadingview = new XLoadingView();
        this.pushModal(title || "title", loadingview);
    },

    replace_loading_with_view: function(view) {
        this._modalQueue[this._modalQueue.length-1].view = view;
        this.updateModal();
    },

    delete_note: function(note_id, note_type, all_notes, after_finished) {
        if( confirm("Are you sure you want to delete this note? ") != true ) {
            event.preventDefault();
            if(event.stopPropagation){
                event.stopPropagation();
            }
            event.cancelBubble=true;
            return;
        } else {
            $.get('/api/delete-' + note_type + '-note/' + note_id,
                function(data) {
                    if (data.is_error) {
                        alert('Error: ' + data.error);
                    } else {
                        for(var i = 0; i < all_notes.length; i+=1) {
                            var n = all_notes[i];
                            if(n.note_id == note_id) {
                                all_notes.splice(i, 1);
                                break;
                            }
                        }
                        after_finished(all_notes);
                    }
                }
            );
        }
    },

    add_or_edit_note: function(after_finished, note_id, view_options, view_class) {
        var that = this;
        var add_note_view = new view_class(_.extend({
            hbc: that,
            after_finished: function(data) {
                after_finished(data);
                that.popModal();
            },
            note_id: note_id,
        }, view_options));

        this.pushModal("title", add_note_view);

        $('.modal').focus(function() {
            $('#flag_inheritance_notes').focus(); //can't focus until it's visible
        });

    },

    add_or_edit_gene_note: function(gene_id, note, after_finished) {
        this.add_or_edit_note(after_finished, note ? note.note_id : null, {
            note: note,
            gene_id: gene_id,
        }, AddOrEditGeneNoteView);
    },

    add_or_edit_family_variant_note: function(variant, family, after_finished, note_id) {
        this.add_or_edit_note(after_finished, note_id, {
            family: family,
            variant: variant,
        }, AddOrEditVariantNoteView);
    },

    edit_family_variant_tags: function(variant, family, after_finished) {
        var that = this;
        var edit_tags_view = new EditVariantTagsView({
            hbc: that,
            family: family,
            variant: variant,
            after_finished: function(data) {
                after_finished(data);
                that.popModal();
            },
        });

        this.pushModal("title", edit_tags_view);
    },

    edit_family_functional_data: function(variant, family, after_finished) {
        var that = this;
        var edit_functional_data_view = new EditVariantFunctionalDataView({
            hbc: that,
            family: family,
            variant: variant,
            after_finished: function(data) {
                after_finished(data);
                that.popModal();
            },
        });

        this.pushModal("title", edit_functional_data_view);
    },
});

