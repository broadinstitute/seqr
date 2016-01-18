window.IgvView = Backbone.View.extend({

    className: 'igv-container',

    initialize: function(options) {
        this.individuals = options.individuals;

        //initialize IGV.js browser
        var tracks = [];
        tracks.push({
            url: '/static/igv/gencode.v19.sorted.bed',
            name: "gencode v19",
            displayMode: "EXPANDED",
        });

        for(var i = 0; i < this.individuals.length; i+=1) {
            var indiv = this.individuals[i];
            if(!indiv.has_bam_file_path) {
                continue;
            }
            tracks.push({
                url: "/project/"+indiv.project_id+"/igv-track/"+indiv.indiv_id,
                type: 'bam',
                indexed: true,
                alignmentShading: 'strand',
                name: '<i style="font-family: FontAwesome; font-style: normal; font-weight: normal;" class="'+
                            utils.get_pedigree_icon(indiv) + '"></i> ' + indiv.indiv_id,
                height: 300,
                minHeight: 300,
                autoHeight: false,
            });

        }

        this.options = {
            showCommandBar: true,
            genome: 'hg19',
            locus: this.locus,
            showKaryo: false,
            tracks: tracks,
        };

        igv.createBrowser(this.el, this.options);
        igv.CoverageMap.threshold=0.1;
        igv.browser.pixelPerBasepairThreshold = function() {
            return 28.0;  //allow zooming in further - default is currently 14.0
        };

    },

    jump_to_locus: function(locus) {
        //locus must be a string like : 'chr1:12345-54321'

        //console.log("Jumping to locus: ", locus);

        igv.browser.search(locus);
    }
});
