var Breakpoints = Backbone.Model.extend({

    initialize: function() {
        console.log("initializing model");
        this.listenTo(this, 'change:minSampleObs', this.updateTable);
        this.listenTo(this, 'change:maxSampleCount', this.updateTable);
    },

    updateTable: function() {
        console.log('Updating table ...');

        // It's irritating if the text in search box disappears when adjusting other filters
        if($('#breakpoint-table_filter input')[0]) {
            this.set('searchText',$('#breakpoint-table_filter input')[0].value);
        }

        $.ajax({
            url:'breakpoints?obs='+this.get('minSampleObs')+'&samples='+this.get('maxSampleCount'), dataType:'json'
        }).done(function(result) {
            console.log("received " + result['breakpoints'].length + " breakpoints in response.");
            breakpoints.set('metadatas',result['metadatas']);
            breakpoints.set('breakpoints',result['breakpoints']);
        })
    },

    defaults: {
        breakpoints: [],
        metadatas:{},
        minSampleObs: 3,
        maxSampleCount: 10,
        searchText: ''
    }

});


var BP_TYPES = ['noise','deletion','insertion','microduplication',
                'duplication','inversion','complex sv','sv','contamination',
                'adapter','gcextreme',
                'chimeric read','multimapping','badref',
                'common','unknown'];

var DATA_COLUMNS = {
        'xpos' : 0,
        'Contig' : 1,
        'Position' : 2,
        'Partner' : 6,
        'Samples' : 4,
        'Sample Obs' : 3,
        'Individual' : 7,
        'Genes' : 8
}

var removeChrRegex = /^chr/;

// https://iwww.broadinstitute.org/igvdata/seq/picard_aggregation/C1657/PROMIS191034061/v2/PROMIS191034061.bam

function igv_url_for_sample(sample) {
    var base='http://localhost:60151/';
    if(BAM_FILES[sample]) {
        return base + 'load?file='+encodeURIComponent(BAM_FILES[sample]) + '&';
    }
    else {
        return base + 'goto?';
    }
}

var TABLE_COLUMNS = [
   { title: 'Position', data: DATA_COLUMNS.Position, render: function(data,type,row) {
       var sizeInfo = '';
       var partnerInfo = ''
       if(row[DATA_COLUMNS.Partner]) {
           var chr = row[DATA_COLUMNS.Contig].replace(removeChrRegex,'');
           var pos = row[DATA_COLUMNS.Position];

           var partnerChrSplit = row[DATA_COLUMNS.Partner].split(':');
           var partnerChr = partnerChrSplit[0].replace(removeChrRegex,'');

           if(chr == partnerChr)  {
               var partnerPos = parseInt(partnerChrSplit[1],10);
               console.log('partnerPos = ' + partnerPos);
               var eventSize = Math.abs(partnerPos-pos);
               if(eventSize > 1000) {
                   sizeInfo = ' <span class=largeEvent>(' + 
                   '<a href="' + igv_url_for_sample(row[DATA_COLUMNS.Individual]) + 'locus='+chr+ ':' + (pos-600) +'-'+(partnerPos+600)+ '" target=igv>' +
                                eventSize +  'bp' + '</a>)</span>';
               }
               else {
                   sizeInfo = ' (' + eventSize + 'bp)';
               }
           }

           partnerInfo = ' -&gt; ' + row[DATA_COLUMNS.Partner] + sizeInfo;
       }

       return row[DATA_COLUMNS.Contig] + ':' + row[DATA_COLUMNS.Position] + partnerInfo
   }},
   { title: 'Individual', data: DATA_COLUMNS.Individual },
   { title: 'Samples', data: DATA_COLUMNS.Samples },
   { title: 'Sample Obs', data: DATA_COLUMNS['Sample Obs'] },
   { title: 'Genes', data: DATA_COLUMNS.Genes, render: function(data,type,row) {
           return row[DATA_COLUMNS.Genes].map(function(g) {
               var url = 'http://www.genecards.org/cgi-bin/carddisp.pl?gene='+encodeURIComponent(g.gene)+'&search='+g.gene+'#diseases'
               var distClass = "far";
               if(g.cds_dist<0) {
                   distClass="none";
               }
               else
               if(g.cds_dist==0) {
                   distClass="inside"
               }
               else
               if(g.cds_dist<50) {
                   distClass="adjacent"
               }               
               else
               if(g.cds_dist<500) {
                   distClass="close"
               }
               var geneLists = '';
               if(GENE_LISTS[g.gene]) {
                   geneLists = GENE_LISTS[g.gene].map(function(gl) {
                       return '(<span class=geneListTag>' + gl + '</span>)'
                   }).join(' ');
               }
               return '<a href="' + url + '" target=genecards class=genedist'+distClass+'>' + g.gene + '</a> ' + geneLists;
           }).join(", ");
       }
   },
   { title: 'IGV', data: 1, render: function(data,type,row) {
           return '<a href="'+igv_url_for_sample(row[DATA_COLUMNS.Individual]) 
                             + 'locus='+row[DATA_COLUMNS.Contig] + ':' + 
                  (row[DATA_COLUMNS.Position]-300) +'-'+(row[DATA_COLUMNS.Position]+300)+ '" target=igv>IGV</a>';
       }
   },
   { title: 'Type', data: 1, render: function(data,type,row) {
           var metadata = breakpoints.get('metadatas')[row[0]];
           if(metadata) {
               return metadata.type;
           }
           else {
               return '';
           }
       }
   }
]

var TYPE_COLUMN = TABLE_COLUMNS.findIndex(function(col) {
    return col.title == 'Type';
});

var IGV_COLUMN = TABLE_COLUMNS.findIndex(function(col) {
    return col.title == 'IGV';
});

var INDIVIDUAL_COLUMN = TABLE_COLUMNS.findIndex(function(col) {
    return col.title == 'Individual';
});

var GENES_COLUMN = TABLE_COLUMNS.findIndex(function(col) {
    return col.title == 'Genes';
});

var BreakpointTableView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc;
        var me = this;
        this.listenTo(breakpoints, 'change', this.render);
        this.highlightedRow = null;
    },

    template: _.template($('#tpl-breakpoint-table').html()),

    events: {
        'change #sample_obs' : function() { 
            var obs = parseInt($('#sample_obs').val(),10);
            console.log('Changing min sample obs to ' + obs); 
            breakpoints.set('minSampleObs',obs)
        },
        'change #max_sample_count' : function() { 
            var maxSampleCount = parseInt($('#max_sample_count').val(),10);
            console.log('Changing max sample count to ' + maxSampleCount); 
            breakpoints.set('maxSampleCount',maxSampleCount)
        } 
    },

    render: function() {
        console.log("Rendering breakpoints");
        $(this.el).html(this.template({
            gene_lists: this.gene_lists,
            minSampleObs: breakpoints.get('minSampleObs'),
            maxSampleCount: breakpoints.get('maxSampleCount')
        }));
//        this.$('#select-variants-container').html(this.select_variants_view.render().el);
//        this.$('#select-multiple-genes-container').html(this.select_multiple_genes_container.render().el);
        
        var me = this;
        var breakpointCount = breakpoints.get('breakpoints').length;
        var breakpointTable = null;
        if(breakpointCount > 0) {
            console.log('Displaying ' + breakpointCount + ' breakpoints')
            breakpointTable = $('#breakpoint-table').DataTable( {
                data: breakpoints.get('breakpoints'),
                createdRow: function(row,data,dataIndex) { me.createBreakpointRow(row,data,dataIndex) },
                columns: TABLE_COLUMNS
            } );
        }
        else {
            $('#breakpoints-table').html('Data is still loading ...');
        }

        var searchText = breakpoints.get('searchText');
        if(breakpointTable && searchText) {
            console.log("setting search text to " + searchText);
            breakpointTable.search(searchText).draw();
            $('#breakpoint-table_filter input')[0].value = searchText;
        }

        return this;
    },
    
    /**
     * Adorn a row in the table with extra features
     */
    createBreakpointRow : function(row, data, dataIndex ) {
    //    console.log("create row");
        var tds = row.getElementsByTagName('td');
        var me = this;
        $(tds[IGV_COLUMN]).find('a').click(function(e) { e.stopPropagation(); me.highlightRow(row); });
        $(tds[GENES_COLUMN]).find('a').click(function(e) { e.stopPropagation(); me.highlightRow(row); });

        var typeTd = $(tds[TYPE_COLUMN]);
        var breakpoint_id = data[DATA_COLUMNS.xpos];
        var individual_id = data[DATA_COLUMNS.Individual]
        typeTd.click(function() {
            if(typeTd.hasClass('editingType')) {

            }
            else {
                me.highlightRow(row);
                var sel = typeTd.html('<select id=' + breakpoint_id + '_type ' + '><option>Select</option>' + 
                    BP_TYPES.map(function(bp_type) { return '<option value="'+bp_type +'">' + bp_type + '</option>'}).join('\n')
                )
                typeTd.addClass('editingType');
                typeTd.find('select').change(function() {
                    var bpType = this.options[this.selectedIndex].value;
                    data[TYPE_COLUMN] = bpType;
                    breakpoints.get('metadatas')[data[DATA_COLUMNS.xpos]] = bpType;
                    typeTd.html(bpType);
                    typeTd.removeClass('editingType');
                    $.post('../../breakpoint/' + breakpoint_id, { 'indiv_id' : individual_id, 'type' : bpType }, function(result) {
                        console.log('Breakpoint updated');
                    });
                });

                console.log('Created select: ' + sel)
            }
        })
    },

    highlightRow: function(tr) {
        console.log('adding highlight to ' + tr);
        if(this.highlightedRow)
            $(this.highlightedRow).removeClass('highlight');
        $(tr).addClass('highlight');
        this.highlightedRow = tr;
    }
});

var breakpoints = new Breakpoints();

var BreakpointSearchHBC = HeadBallCoach.extend({

    initialize: function(options) {
        this.gene_lists = options.gene_lists;
        this.family = options.family;
        breakpoints.updateTable();
        this.breakpoint_table = new BreakpointTableView({
            hbc: this,
            gene_lists: this.gene_lists,
        });
    },
    
    bind_to_dom: function() {
        $('#form-container').html(this.breakpoint_table.render().el);
    },
});

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$(document).ready(function() {

    var hbc = new BreakpointSearchHBC({
        project_options: PROJECT_OPTIONS,
        gene_lists: GENE_LISTS,
        family: new Family(FAMILY),
    });

    // should be gettable from cookie, but not working?
    var csrf_token = $('#csrf input')[0].value;
    console.log("CSRF token = " + csrf_token);

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                console.log("Setting csrf token");
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
            else {
                console.log("Not setting csrf token");
            }
        }
    });

    hbc.bind_to_dom();
    Backbone.history.start();
    window.hbc = hbc;
});

