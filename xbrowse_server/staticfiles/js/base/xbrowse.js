window.ModalQueueView = Backbone.View.extend({

    initialize: function() {
        this.hbc = this.options.hbc;
    },

    template: _.template(
        $('#tpl-modal-queue').html()
    ),

    events: {
        'click .back-button': 'goBack',
    },

    render: function() {
        $(this.el).html(this.template());
        this.$('.modal').modal({
            keyboard: false,
            backdrop: 'static',
        });
        return this;
    },

    show: function() {
        this.$('.modal').modal('show');
    },

    hide: function() {
        this.$('.modal').modal('hide');
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

    // TODO: does this cause awkward loops or anything?
    // So weird to reference app from here without a delegate
    goBack: function() {
        this.hbc.popModal();
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
        var view = new GeneModalView({
            gene_id: gene_id
        });
        that.pushModal(gene_id, view);
    },

    variant_info: function(variant) {
        var that = this;
        var view = new AnnotationDetailsView({
            variant: variant
        });
        that.pushModal("", view);
    },

    variant_infos: function(variant) {
        var that = this;
        var view = new AnnotationDetailsView({
            variant: variant
        });
        that.pushModal("", view);
    },

    pushModal: function(title, view) {
        var that = this;
        that._modalQueue.push({
            title: title,
            view: view,
        });
        that.updateModal();
    },

    popModal: function() {
        var that = this;
        that._modalQueue.splice(that._modalQueue.length-1,1);
        that.updateModal();
    },

    resetModal: function() {
        var that = this;
        that._modalQueue = [];
        that.updateModal();
    },

    // update the modal display, showing the top item in queue if exists
    // can be called no matter state of the queue - empty or whatever
    updateModal: function() {

        var that = this;
        // TODO: do we really need to delete it if it exists? Somebody check on this
        // nothing in queue? delete modal view if it exists
        if (that._modalQueue.length == 0) {
            if (that._modalView) {
                that._modalView.hide();
                delete that._modalView;
            }
        }
        else {
            // do we need to create modal view?
            if (that._modalView == undefined) {
                that._modalView = new ModalQueueView({hbc: that});
                $('body').append(that._modalView.render().el);
            }
            // note that render() is called on each display
            // almost like that's what it was designed for or something
            var nextObj = that._modalQueue[that._modalQueue.length-1];
            that._modalView.setTitle(nextObj.title);
            that._modalView.setContent(nextObj.view.render().el);
        }
    },

    push_modal_loading: function() {
        var loadingview = new XLoadingView();
        this.pushModal("", loadingview);
    },

    replace_loading_with_view: function(view) {
        this.popModal();
        this.pushModal("", view);
    },

    add_family_variant_note: function(variant, family, after_finished) {
        var that = this;
        var after_finished_outer = function(variant) {
            after_finished(variant);
            that.popModal();
        };
        var flag_view = new AddVariantNoteView({
            hbc: that,
            family: family,
            variant: variant,
            after_finished: after_finished_outer,
        });
        this.pushModal("asdf", flag_view);
    },

    edit_family_variant_tags: function(variant, family, after_finished) {
        var that = this;
        var after_finished_outer = function(variant) {
            after_finished(variant);
            that.popModal();
        };
        var flag_view = new EditVariantTagsView({
            hbc: that,
            family: family,
            variant: variant,
            after_finished: after_finished_outer,
        });
        this.pushModal("asdf", flag_view);  // todo: remove first arg from pushModal
    },

});

var SimpleTestView = Backbone.View.extend({
    render: function() {
        $(this.el).html("<h1>bt</h1>");
        return this;
    }
});