window.IgvView = Backbone.View.extend({

    className: 'igv-container',

    initialize: function (options) {
        this.individuals = options.individuals;

        var tracks = [];

        var has_cram_files = false
        for (var i = 0; i < this.individuals.length; i += 1) {
            var indiv = this.individuals[i];
            if (!indiv.read_data_is_available) {
                continue;
            }

            var alignmentTrack = {
                url: "/project/" + indiv.project_id + "/igv-track/" + indiv.indiv_id,
                type: 'bam',
                indexed: true,
                alignmentShading: 'strand',
                name: '<i style="font-family: FontAwesome; font-style: normal; font-weight: normal;" class="' +
                utils.get_pedigree_icon(indiv) + '"></i> ' + indiv.indiv_id,
                height: 300,
                minHeight: 300,
                autoHeight: false,
            }

            if (indiv.read_data_format == 'cram') {
                alignmentTrack.sourceType = 'pysam'
                alignmentTrack.url = "/project/" + indiv.project_id + "/igv-track/" + indiv.indiv_id
                alignmentTrack.alignmentFile = alignmentTrack.url
                alignmentTrack.referenceFile = alignmentTrack.url
            }

            tracks.push(alignmentTrack);
        }

        //initialize IGV.js browser
        if (options.genome == "hg38" || options.genome == "GRCh38") {
            if (!options.gencodeUrl) {
                options.gencodeVersion = "gencode GRCh38v27";
                options.gencodeUrl = 'https://storage.googleapis.com/seqr-reference-data/GRCh37/gencode/gencode.v27.annotation.sorted.gtf.gz';
            }
        } else {
            if (!options.genome) {
                options.genome = "hg19"
            }
            if (!options.gencodeUrl) {
                options.gencodeVersion = "gencode GRCh37/v27";
                options.gencodeUrl = 'https://storage.googleapis.com/seqr-reference-data/GRCh37/gencode/gencode.v27lift37.annotation.sorted.gtf.gz';
            }
        }

        tracks.push({
            url: options.gencodeUrl,
            name: options.gencodeVersion,
            //displayMode: "EXPANDED",
            displayMode: "SQUISHED",
        });

        this.options = {
            showCommandBar: true,
            genome: options.genome,
            locus: options.locus,
            showKaryo: false,
            tracks: tracks,
            showCenterGuide: true,
            showCursorTrackingGuide: true,
        };

        igv.createBrowser(this.el, this.options);
        igv.CoverageMap.threshold = 0.1;
        igv.browser.pixelPerBasepairThreshold = function () {
            return 28.0;  //allow zooming in further - default is currently 14.0
        };

    },

    jump_to_locus: function (locus) {
        //locus must be a string like : 'chr1:12345-54321'
        igv.browser.search(locus);
    }
});
