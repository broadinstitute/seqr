window.IgvView = Backbone.View.extend({

    className: 'igv-container',

    initialize: function (options) {
        this.individuals = options.individuals;

        var tracks = [];
        for (var i = 0; i < this.individuals.length; i += 1) {
            var indiv = this.individuals[i];
	    console.log(indiv)
            if(indiv.cnv_bed_file) {
                var bedTrack = {
                    url: '/static/igv/' + indiv.cnv_bed_file,
                    indexed: false,
                    name: '<i style="font-family: FontAwesome; font-style: normal; font-weight: normal;" class="' + utils.get_pedigree_icon(indiv) + '"></i> ' + indiv.indiv_id + ' CNVs',
                }

                console.log('Adding bed track: ', bedTrack)
                tracks.push(bedTrack);
            }

            if (indiv.read_data_is_available) {
                var alignmentTrack = null
                if (indiv.read_data_format == 'cram') {
                    options.genome = "hg38"  //this is a temporary hack - TODO add explicit support for grch38
                    alignmentTrack = {
                        url: "/project/" + indiv.project_id + "/igv-track/" + indiv.indiv_id,
                        sourceType: 'pysam',
                        alignmentFile: '/placeholder.cram',
                        referenceFile: '/placeholder.fa',
                        type: "bam",
                        alignmentShading: 'strand',
                        name: '<i style="font-family: FontAwesome; font-style: normal; font-weight: normal;" class="' + utils.get_pedigree_icon(indiv) + '"></i> ' + indiv.indiv_id,
                        //name: 'test'
                    }
                } else {
                    alignmentTrack = {
                        url: "/project/" + indiv.project_id + "/igv-track/" + indiv.indiv_id,
                        type: "bam",
                        indexed: true,
                        alignmentShading: 'strand',
                        name: '<i style="font-family: FontAwesome; font-style: normal; font-weight: normal;" class="' + utils.get_pedigree_icon(indiv) + '"></i> ' + indiv.indiv_id,
                        height: 300,
                        minHeight: 300,
                        autoHeight: false,
                        //samplingDepth: 100,
                    }
                }

                tracks.push(alignmentTrack);
            }
        }

        //initialize IGV.js browser
        if (options.genome == "hg38" || options.genome == "GRCh38") {
            if (!options.gencodeUrl) {
                options.gencodeVersion = "gencode GRCh38v27";
                options.gencodeUrl = 'https://storage.googleapis.com/seqr-reference-data/GRCh38/gencode/gencode.v27.annotation.sorted.gtf.gz';
            }
        } else {
            if (!options.genome) {
                options.genome = "hg19"
            }
            if (!options.gencodeUrl) {
                options.gencodeVersion = "gencode GRCh37v27";
                options.gencodeUrl = 'https://storage.googleapis.com/seqr-reference-data/GRCh37/gencode/gencode.v27lift37.annotation.sorted.gtf.gz';
            }
        }

        tracks.push({
            url: options.gencodeUrl,
            name: options.gencodeVersion,
            //displayMode: "EXPANDED",
            displayMode: "SQUISHED",
        });

        var igvOptions = {
            showCommandBar: true,
            locus: options.locus,
        //reference: {
        // 	id: options.genome,
        //},
        genome: options.genome,
            showKaryo: false,
        showIdeogram: true,
        showNavigation: true,
        showRuler: true,
        tracks: tracks,
            showCenterGuide: true,
            showCursorTrackingGuide: true,
        };

        console.log('IGV options:', igvOptions);

        igv.createBrowser(this.el, igvOptions);
        //igv.CoverageMap.threshold = 0.1;
        //igv.browser.pixelPerBasepairThreshold = function () {
        //    return 28.0;  //allow zooming in further - default is currently 14.0
        //};
    },

    jump_to_locus: function (locus) {
        //locus must be a string like : 'chr1:12345-54321'
        try {
            if(igv.browser.genome) {
                igv.browser.search(locus);
            }
        } catch(e) {
            console.log(e)
        }
    }
});
