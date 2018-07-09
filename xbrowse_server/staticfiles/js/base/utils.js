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

_CLINSIG_COLOR = {
    'benign': 'green',
	'likely benign': 'green',
    'pathogenic': 'red',
	'likely pathogenic': 'red',
    'protective': 'green',
    'risk factor': 'orange',
}

_HGMD_CLASS_COLOR = {
    'DM': 'red',
    'DM?': 'orange',
    'FPV': 'orange',
    'FP': 'orange',
    'DFP': 'orange',
    'DP': 'orange',
}

_HGMD_CLASS_NAME = {
	'DM': 'Disease Causing (DM)',
    'DM?': 'Disease Causing? (DM?)',
	'FPV': 'Frameshift or truncating variant (FTV)',
    'FP': 'In vitro/laboratory or in vivo functional polymorphism (FP)',
    'DFP': 'Disease-associated polymorphism with additional supporting functional evidence (DFP)',
    'DP': 'Disease-associated polymorphism (DP)',
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
      var g = variant.genotypes[indiv_id];
	    if (g == null) {
        return "Error: genotype not found";
      }

      var s = "";
      if (variant.extras.orig_alt_alleles) {
          s += "Raw Alt. Alleles: <b>" + variant.extras.orig_alt_alleles.join().replace(/,/g, ", ") + "</b><br />";
      }

      if (g.extras.ad != null) {
          s += "Allelic Depth: <b>" + g.extras.ad + "</b><br />";
      }

      if (g.extras.dp != null) {
          s += "Read Depth: <b>" + (g.extras.dp === null ? "" : g.extras.dp) + "</b><br />";
      }

      if (g.extras.gq != null) {
          s += "Genotype Quality: <b>" + g.extras.gq + "</b><br />";
      }

      if (g.extras.pl != null) {
          s += "Phred Likelihoods: <b>" + g.extras.pl + "</b><br />";
      }

      if (g.ab != null) {
          s += "Allele Balance: <b>" + g.ab.toPrecision(2) + "</b><br />";
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
    else if (val == .02) return 7;
    else if (val == .03) return 8;
		else if (val == .05) return 9;
		else if (val == .1) return 10;
		else return 11;
	}, 

	freqInverse: function(position) {
		if (position == 1) return 0;
		else if (position == 2) return Number(.0001).toExponential();
		else if (position == 3) return Number(.0005).toExponential();
		else if (position == 4) return Number(.001).toExponential();
		else if (position == 5) return Number(.005).toExponential();
		else if (position == 6) return .01;
    else if (position == 7) return .02;
    else if (position == 8) return .03;
		else if (position == 9) return .05;
		else if (position == 10) return .1;
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

    getPedigreeIcon: function(indiv) {
        if (indiv.gender == "F" && indiv.affected == "A") return 'fa-circle';
        else if (indiv.gender == "F" && indiv.affected == "N") return 'fa-circle-o';
        else if (indiv.gender == "M" && indiv.affected == "A") return 'fa-square';
        else if (indiv.gender == "M" && indiv.affected == "N") return 'fa-square-o';
        else return 'fa-question'
    },

	getClinvarClinsigColor: function(clinsig) {
        if (clinsig in _CLINSIG_COLOR) {
        	return _CLINSIG_COLOR[clinsig];
		} else {
            return 'gray';
		}
	},

    getHGMDClassColor: function(hgmdClass) {
        if (hgmdClass in _HGMD_CLASS_COLOR) {
            return _HGMD_CLASS_COLOR[hgmdClass];
        } else {
            return 'gray';
        }
    },

    getHGMDClassName: function(hgmdClass) {
        if (hgmdClass in _HGMD_CLASS_NAME) {
            return _HGMD_CLASS_NAME[hgmdClass];
        } else {
            return hgmdClass;
        }
    },

	getVariantSearchLinks: function(variant) {
        var worst_vep_annotation = variant.annotation.main_transcript || variant.annotation.vep_annotation[variant.annotation.worst_vep_annotation_index];

        var symbol = worst_vep_annotation.gene_symbol || worst_vep_annotation.symbol;

        var variations = [];
        if (worst_vep_annotation.hgvsc) {
            var hgvsc = worst_vep_annotation.hgvsc.split(":")[1].replace("c.","");

            variations.push(
                symbol+":c."+hgvsc,              //TTN:c.78674T>C
                'c.'+hgvsc,                      //c.1282C>T
                hgvsc, 					         //1282C>T
                hgvsc.replace(">","->"),         //1282C->T
                hgvsc.replace(">","-->"),        //1282C-->T
                ('c.'+hgvsc).replace(">","/"), 	 //c.1282C/T
                hgvsc.replace(">","/"),  	     //1282C/T
                symbol+':'+hgvsc                 //TTN:78674T>C
            );
        }

        if (worst_vep_annotation.hgvsp) {
            var hgvsp = worst_vep_annotation.hgvsp.split(":")[1].replace("p.", "");
            variations.push(
                symbol+":p."+hgvsp,         //TTN:p.Ile26225Thr
                symbol+":"+hgvsp            //TTN:Ile26225Thr
            );
        }

        if (worst_vep_annotation.amino_acids && worst_vep_annotation.protein_position) {
            var aminoAcids = worst_vep_annotation.amino_acids.split('/');
            var aa1 = aminoAcids[0] || "";
            var aa2 = aminoAcids[1] || "";

            variations.push(
                aa1 + worst_vep_annotation.protein_position + aa2,          //A625V
                worst_vep_annotation.protein_position + aa1 + '/' + aa2    //625A/V
            );
        }

        if (variant.alt && variant.ref && variant.pos) {
            variations.push(
                variant.pos + variant.ref + "->" + variant.alt,         //179432185A->G
                variant.pos + variant.ref + "-->" + variant.alt,        //179432185A-->G
                variant.pos + variant.ref + "/" + variant.alt,          //179432185A/G
                variant.pos + variant.ref + ">" + variant.alt,			//179432185A>G
                "g." + variant.pos + variant.ref + ">" + variant.alt   //g.179432185A>G
            );
        }

        var googleHref = "https://www.google.com/search?q="+symbol+" + " + variations.join('+');
        var pubmedHref = "https://www.ncbi.nlm.nih.gov/pubmed?term="+symbol+" AND ( "+variations.join(' OR ')+")";

        return { 'google': googleHref, 'pubmed': pubmedHref };
	},

    getVariantUCSCBrowserLink: function(variant, genomeVersion) {
		if (!genomeVersion || genomeVersion == "37") {
            genomeVersion = "19"
		}

		var url = "http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg"+genomeVersion+
			"&highlight=hg"+genomeVersion+
			".chr"+variant.chr.replace("chr", "") +':'+ variant.pos + "-" + (variant.pos+variant.ref.length-1)+
			"&position=chr" + this.getCoordWindow10(variant).replace('chr', '');
		return url;
	},
}
