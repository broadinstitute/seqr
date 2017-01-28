window.IndividualsView = Backbone.View.extend({
    template: _.template($('#tpl-individuals').html()),
    initialize: function(options) {
        this.project_spec = options.project_spec;
        this.individuals = options.individuals;
	
	this.phenotips_id_to_individuals = {}
	var that = this;
	$.each(this.individuals, function(i, indiv) { 
		if(indiv.phenotips_id) {
		    that.phenotips_id_to_individuals[indiv.phenotips_id] = indiv;
		}
	}); 

        this.selectable = options.selectable == true;
        this.show_edit_links = options.show_edit_links == true;
        this.show_resource_links = options.show_resource_links == true;
        this.indiv_id_link = options.indiv_id_link != false;
    },
    events: {
        "click #select-all-individuals": "select_all",
        "click .indiv-checkbox": "select_one",
	"click .phenotipsViewModalBtn": "show_phenotips_modal",
	"click .editStatusBtn": "show_edit_status_modal",
    },
    render: function() {
        $(this.el).html(this.template({
            individuals: this.individuals,
            selectable: this.selectable,
            indiv_id_link: this.indiv_id_link,
            project_spec: this.project_spec,
            show_edit_links: this.show_edit_links,
            show_resource_links: this.show_resource_links,
        }));
	if(!this.selectable) {
            this.$('.tablesorter').tablesorter();
        }

        return this;
    },
    
    show_phenotips_modal: function(e) {
	    var phenotips_id = e.target.id;
	    var uri = '/api/phenotips/proxy/view/' + phenotips_id + '?' + 'project=' + this.project_spec.project_id;
	    var indiv = indiv = this.phenotips_id_to_individuals[phenotips_id];
	    $('#phenotipsEditPatientFrame').attr('src', 'about:blank');
            $('#phenotipsEditPatientFrame').attr('src', uri);
	    uri = '/xadmin/base/family/'+indiv['family.id']+'/change/#id_internal_case_review_brief_summary';
	    console.log("Loading xadmin url: ", uri);
            $('.modal-title').html('Notes & PhenoTips')
            $('.modal-body').show()
            $('.modal-body2').hide()
	    if(indiv.pedigree_image_url) {
		$('#family-pedigree').attr("src", indiv.pedigree_image_url);
		$('#family-pedigree').show()
	    } else {
		$('#family-pedigree').hide()
	    }	   
	    $('#caseReviewNotes').attr('src', 'about:blank');
            $('#phenotipsModal').modal('show');
	    $('#caseReviewNotes').attr('src', uri);
	    $('#family_about_family_notes').html(indiv.family_about_family_notes ? indiv.family_about_family_notes : "None");
	    //$('#family_analysis_summary_notes').html(indiv.family_analysis_summary_notes);
    },

    show_edit_status_modal: function(e) {
	    var indiv_id = e.target.id;
	    var uri = 'https://seqr.broadinstitute.org/xadmin/base/individual/'+indiv_id+'/change/#id_in_case_review';
            $('.modal-title').html('Edit Status')
	    $('#editStatusIFrame').attr('src', 'about:blank');
	    $('#editStatusIFrame').attr('src', uri);
	    $('#phenotipsModal').modal('show');

            $('.modal-body').hide()
            $('.modal-body2').show()
    },

    get_selected_indiv_ids: function() {
        var ret = [];
        this.$('.indiv-checkbox:checked').each(function(){ret.push($(this).data('indiv_id'))});
        return ret;
    },

    set_id_selected: function(indiv_id) {
        this.$('.indiv-checkbox[data-indiv_id="' + indiv_id + '"]').prop('checked', true);
        this.$('tr.indiv-row[data-indiv_id="' + indiv_id + '"]').addClass('row-checked');
    },

    set_id_deselected: function(indiv_id) {
        this.$('.indiv-checkbox[data-indiv_id="' + indiv_id + '"]').prop('checked', false);
        this.$('tr.indiv-row[data-indiv_id="' + indiv_id + '"]').removeClass('row-checked');
    },

    select_one: function(e) {
        var checked = $(e.target).is(':checked');
        var indiv_id = $(e.target).data('indiv_id');
        if (checked) {
            this.set_id_selected(indiv_id);
        } else {
            this.set_id_deselected(indiv_id);
        }
    },

    select_all: function(e) {
        var checked = $(e.target).is(':checked');
        for (var i=0; i<this.individuals.length; i++) {
            if (checked) this.set_id_selected(this.individuals[i].indiv_id);
            else this.set_id_deselected(this.individuals[i].indiv_id);
        }
    },
});