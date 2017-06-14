
$(document).ready(function() {
    var individuals = new IndividualSet(INDIVIDUALS);

    var indivsView = new IndividualListTable({
        collection: individuals,
        project_id: PROJECT_ID,
        project_phenotypes: PROJECT_PHENOTYPES,
    });

    $('#edit-indivs-container').html(indivsView.render().el);

    window.bank = {};
    bank.individuals = individuals;
    bank.indivsView = indivsView;

});
