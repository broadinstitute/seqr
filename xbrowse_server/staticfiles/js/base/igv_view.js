window.IgvView = Backbone.View.extend({

    className: 'igv-container',

    initialize: function (options) {
        this.individuals = options.individuals;

        //initialize IGV.js browser
        var tracks = [];
        tracks.push({
          url: 'https://storage.googleapis.com/seqr-reference-data/GRCh37/gencode/gencode.v27lift37.annotation.sorted.gtf.gz',
          name: "gencode v27",
          //displayMode: "EXPANDED",
          displayMode: "SQUISHED",
        });

        for (var i = 0; i < this.individuals.length; i += 1) {
            var indiv = this.individuals[i];
            if (!indiv.read_data_is_available) {
                continue;
            }

            tracks.push({
                url: "/project/" + indiv.project_id + "/igv-track/" + indiv.indiv_id,
                type: 'bam',
                indexed: true,
                alignmentShading: 'strand',
                name: '<i style="font-family: FontAwesome; font-style: normal; font-weight: normal;" class="' + utils.get_pedigree_icon(indiv) + '"></i> ' + indiv.indiv_id,
                height: 300,
                minHeight: 300,
                autoHeight: false,
            });
        }

        this.options = {
          showCommandBar: true,
          genome: 'hg19',
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
