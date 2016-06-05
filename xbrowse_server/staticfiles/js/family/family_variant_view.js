

$(document).ready(function() {

    window.hbc = new HeadBallCoach();
    window.family = new Family(FAMILY);

    var variant_view = new BasicVariantView({
        hbc: hbc,
        variant: VARIANT,
        family: family,
        show_genotypes: true,
        individuals: family.individuals_with_variant_data(),
	show_variant_notes: true,
    });

    $('#variant-container').html(variant_view.render().el);

    Backbone.history.start();

});