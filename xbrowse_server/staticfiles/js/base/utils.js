function _formatFrequency(val) {
	return val.toPrecision(3); 
} 

function addCommas(nStr)
{
	nStr += '';
	x = nStr.split('.');
	x1 = x[0];
	x2 = x.length > 1 ? '.' + x[1] : '';
	var rgx = /(\d+)(\d{3})/;
	while (rgx.test(x1)) {
		x1 = x1.replace(rgx, '$1' + ',' + '$2');
	}
	return x1 + x2;
}

window.utils = {
	
	getCoord: function(variant) {
		return variant.chr + ':' + variant.pos;
	},
	
	getCoordDisplay: function(variant) {
		return variant.chr + ':' + addCommas(variant.pos);
	}, 
	
	getCoordWindow10: function(variant) {
		return variant.chr + ':' + (variant.pos-10) + '-' + (variant.pos+10) ;
	},

	getGenoDisplay: function(variant, indiv_id) {
		var num_alt = variant.genotypes[indiv_id].num_alt;
        if (num_alt == null) {
            return 'Missing';
        }
		if (num_alt == 0) {
			return 'Ref/Ref';
		} else if (num_alt == 1) {
			return 'Het';
		} else if (num_alt == 2) {
			return 'Alt/Alt';
		} else {
			return 'Error';
		}
	},

    simpleGenoDisplay: function(variant, indiv_id) {
        var num_alt = variant.genotypes[indiv_id].num_alt;
        if (num_alt == 0) {
            return '-';
        } else if (num_alt == 1) {
            return '1';
        } else if (num_alt == 2) {
            return '2';
        } else if (num_alt == -1) {
            return 'M';
        } else {
            return 'Error';
        }
    },
	
	getGenoMouseover: function(variant, indiv_id) {
		if (variant.genotypes[indiv_id] == undefined) {
			return "Error: genotype does not exist"; 
		}

        var s = "Raw Alt. Alleles: <b><br>" + variant.extras.orig_alt_alleles.join().replace(/,/g, ", ") +
                "</b><br/>Allelic Depth: <b>" + variant.genotypes[indiv_id].extras.ad +
                "</b><br/>Read Depth: <b>" + variant.genotypes[indiv_id].extras.dp +
                "</b><br/>Genotype Quality: <b>" + variant.genotypes[indiv_id].gq +
                "</b><br/>Phred Likelihoods: <b>" + variant.genotypes[indiv_id].extras.pl + "</b>"
            ;


        // TODO: can remove undefined check; always '.' now
		if (variant.genotypes[indiv_id].ab != null) {
			s += "</b><br/>Allele Balance: <b>" + variant.genotypes[indiv_id].ab.toPrecision(2) + "</b>"
		}
		return s; 
	},
	
	freqIndex: function(val) {
		if (val == 0) return 1;
    else if (val == .0001) return 2;
    else if (val == .0005) return 3;
    else if (val == .001) return 4;
		else if (val == .005) return 5;
    else if (val == .01) return 6;
    else if (val == .05) return 7;
		else if (val == .1) return 8;
		else return 11;
	}, 

	freqInverse: function(position) {
    if (position == 1) return 0;
    else if (position == 2) return Number(.0001).toExponential();
    else if (position == 3) return Number(.0005).toExponential();
    else if (position == 4) return Number(.001).toExponential();
		else if (position == 5) return Number(.005).toExponential();
		else if (position == 6) return .01;
		else if (position == 7) return .05;
		else if (position == 8) return .1;
		else return 1;
	}, 

	formatFrequency: _formatFrequency, 

	getGQ: function(variant, indiv_id) {
		if (variant.genotypes[indiv_id] != undefined) {
			return variant.genotypes[indiv_id].gq;			
		} else {
			return undefined; 
		}
	},

	// get CSS class to display this individual's icon in the results table header
	// right now using random font awesome classes
	// TODO: create new icon font for this
	getIconClass: function(indiv) {
		if (indiv.gender == "Female" && indiv.affected == "Affected") return 'icon-circle'; 
		else if (indiv.gender == "Female" && indiv.affected == "Unaffected") return 'icon-circle-blank'; 
		else if (indiv.gender == "Male" && indiv.affected == "Affected") return 'icon-bookmark'; 
		else if (indiv.gender == "Male" && indiv.affected == "Unaffected") return 'icon-check-empty'; 
		else return 'icon-beer'; 
	},


    getControlHitsTooltip: function(gene) {

        var s = "Recessive - <b>" + gene.gene_info.control_hits.recessive +
                "</b><br/>Dominant - <b>" + gene.gene_info.control_hits.dominant +
                "</b><br/>Homozygous Recessive - <b>" + gene.gene_info.control_hits.homozygous_recessive +
                "</b><br/>Compound Het - <b>" + gene.gene_info.control_hits.compound_het +
                "</b><br/>X-Linked Recessive - <b>" + gene.gene_info.control_hits.x_linked_recessive + "</b>"
            ;
        return s;
    },

    // initializes tooltips and popovers in a backbone view
    initializeHovers: function(view) {
        view.$('.icon-popover').popover({
            container: 'body',
            trigger: 'hover',
        });
        view.$('.gopopover').popover({
            container: 'body',
            trigger: 'hover',
        });
        view.$('.gotooltip').tooltip({
            trigger: 'hover',
            container: 'body',
            html: true,
        });
    },

    get_pedigree_icon: function(indiv) {
        if (indiv.gender == "F" && indiv.affected == "A") return 'fa-circle';
        else if (indiv.gender == "F" && indiv.affected == "N") return 'fa-circle-o';
        else if (indiv.gender == "M" && indiv.affected == "A") return 'fa-square';
        else if (indiv.gender == "M" && indiv.affected == "N") return 'fa-square-o';
        else return 'fa-question'
    },

    igv_link_from_bam_files: function(bam_file_list) {

    },
}