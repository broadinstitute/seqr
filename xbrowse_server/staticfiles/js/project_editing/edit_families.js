
$(document).ready(function() {
    var families = FAMILIES;

    var familiesView = new FamilyListTable({
        families: families,
        project_id: PROJECT_ID,
        project_phenotypes: PROJECT_PHENOTYPES,
    });

    $('#edit-families-container').html(familiesView.render().el);

    window.bank = {};
    bank.families = families;
    bank.familiesView = familiesView;

});
