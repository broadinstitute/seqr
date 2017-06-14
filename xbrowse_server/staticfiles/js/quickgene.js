$(document).ready(function() {
    var geneView = new GeneDetailsView({gene: GENE});
    var parent = $('#gene-view-container');
    parent.html(geneView.render(parent.width()).el);
});









