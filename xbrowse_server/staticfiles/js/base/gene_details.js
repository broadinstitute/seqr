window.GeneDetailsView = Backbone.View.extend({

    initialize: function(options) {
        this.hbc = options.hbc || new HeadBallCoach();
        this.gene = options.gene;
	if(this.gene.function_desc) {
	    this.gene.function_desc = this.gene.function_desc.replace(/PubMed:(\d+)/g, 'PubMed: <a href="http://www.ncbi.nlm.nih.gov/pubmed/$1 " target="_blank">$1</a>');
	    this.gene.function_desc = this.gene.function_desc.replace(/ECO:(\d+)/g, 'ECO: <a href="http://ols.wordvis.com/q=ECO:$1 " target="_blank">$1</a>');
	}
	if(this.gene.disease_desc) {
	    this.gene.disease_desc = this.gene.disease_desc.replace(/PubMed:(\d+)/g, 'PubMed: <a href="http://www.ncbi.nlm.nih.gov/pubmed/$1 " target="_blank">$1</a>');
	    this.gene.disease_desc = this.gene.disease_desc.replace(/ECO:(\d+)/g, 'ECO: <a href="http://ols.wordvis.com/q=ECO:$1 " target="_blank">$1</a>');
	    this.gene.disease_desc = this.gene.disease_desc.replace(/;/g, '<br>');
	    this.gene.disease_desc = this.gene.disease_desc.replace(/DISEASE:(.*?)\[MIM:/g, '<b>$1</b>[MIM:');
	    this.gene.disease_desc = this.gene.disease_desc.replace(/\[MIM:(\d+)/g, '[MIM:<a href="http://www.omim.org/entry/$1" target="_blank">$1</a>');
	}
    },

    template: _.template($('#tpl-gene-modal-content').html()),

    events: {
        'click a.delete-gene-note': 'delete_gene_note',
        'click a.add-or-edit-gene-note': 'add_or_edit_gene_note',
    },

    render: function(width) {
        // TODO add disclaimer text
        var that = this;
        $(this.el).html(this.template({
            gene: that.gene,
        }));
        this.drawExpressionDisplay(1100);
        this.delegateEvents();
        return this;
    },

    add_or_edit_gene_note: function(event) {
        var note_index = null;
        var note_id = $(event.currentTarget).attr('data-target');
        if (note_id) {
            for (var i = 0; i < this.gene.notes.length; i += 1) {
                if (this.gene.notes[i].note_id == note_id) {
                    note_index = i;
                    break;
                }
            }
        }
        var that = this;
        this.hbc.add_or_edit_gene_note(this.gene.gene_id, this.gene.notes[note_index], function(data) {
            if (note_index != null) {
                // Remove the old version of the note
                that.gene.notes.splice(note_index, 1);
            }
            that.gene.notes.push(data.note);
            that.render();
        }, note_id);
    },

    delete_gene_note: function(event) {
        var that = this;
        this.hbc.delete_note($(event.currentTarget).attr('data-target'), 'gene', this.gene.notes, function(notes) {
            that.gene.notes = notes;
            that.render();
        });
    },

    resize: function() {
    },

    drawExpressionDisplay: function(width) {

        var that = this;

        if (this.gene.expression == null) {
            this.$('#expression_plot').hide();
            this.$('#no-gene-expression').show();
            return;
        } else {
            this.$('#expression_plot').show();
            this.$('#no-gene-expression').hide();
        }

        // rename to tissue_names
        var expression_names = [];
        var expression_slugs = [];
        for (var i=0; i<DICTIONARY.tissue_types.length; i++) {
            expression_slugs.push(DICTIONARY.tissue_types[i].slug);
            expression_names.push(DICTIONARY.tissue_types[i].name);
        }

        //var width = that.$('#expression_plot').width();

        var row_height = 25;
        var scatter_offset = 200;
        var scatter_horizontal_padding = 10;

        var scatter_width = width-scatter_offset-2*scatter_horizontal_padding;
        var min_exponent = -3;
        var max_exponent = 3.2;

        var x = d3.scale.linear().domain([min_exponent, max_exponent]).range([0, scatter_width]);
        var row_offset = function(i) { return i*row_height + 30 }

	// Define the div for the tooltip
	var tooltip_div = d3.select("body").append("div").attr("class", "d3-tooltip").style("opacity", 0);

        var xcoord = function(d) {
            var e = min_exponent;
            if (d>0) {
                e = Math.log(d)/Math.log(10); // convert to base 2
            }
            // don't allow outside bounds
            if (e < min_exponent) e = min_exponent;
            if (e > max_exponent) e = max_exponent;

            return scatter_offset + scatter_horizontal_padding + x(e);

        }

        var vis = d3.selectAll(that.$("#expression_plot"))
            .append("svg")
            .attr("width", width)
            .attr("height", row_height*expression_slugs.length + 50);

        var labels = vis.selectAll('text')
            .data(expression_names)
            .enter()
            .append('text')
            .attr("text-anchor", "end")
            .attr('x', scatter_offset-25) // 12 px margin between text and scatter
            .attr('y', function(d,i) { return row_offset(i) + 15 } )
            .style('font-weight', 'bold')
            .text(function(d) { return d; });

        var colors = d3.scale.category10();


        var axis = d3.svg.axis()
            .scale(x)
            .tickSize(0)
            .tickPadding(6)
            .orient("bottom");

        vis.append("g")
            .attr("class", "axis axis-label")
            .attr("transform", "translate(" + scatter_offset + "," + 3 + ")")
            .call(axis);

        vis.append("g")
            .append("text")
            .attr("class", "axis axis-title")
            .text("LOG 10 EXPRESSION")
            .attr("text-anchor", "end")
            .attr("transform", "translate(" + (scatter_offset - 25) + "," + 17 + ")");

        var colorLabels = vis.selectAll('rect.color-label')
            .data(expression_names)
            .enter()
            .append('rect')
            .attr('class', 'color-label')
            .attr('x', scatter_offset-15 )
            .attr('y', function(d,i) { return row_offset(i) + 4 } )
            .attr('width', 6)
            .attr('height', 16)
            .attr('fill', function(d, i) { return colors(i); } )
            .attr('fill-opacity', .7);

        for (var i=0; i<expression_slugs.length; i++) {
            var slug = expression_slugs[i];
            //window.expr = this.gene.expression;
	    var gene_rpkms_array = this.gene.expression[slug].filter(function(x) { return x > 0 });
	    var gene_expression_data = vis.selectAll('circle[data-expression="' + slug + '"]').data(gene_rpkms_array);
            gene_expression_data.enter()
                .append('circle')
                .attr('data-expression', slug)
                .attr('r', 5)
                .attr('fill-opacity', .12)
                .attr('fill', function(d, j) { return colors(i); } )
                .attr('transform', function(d, j) { return "translate(" + xcoord(d) + "," + (row_offset(i) + 13) + ")"; })
		.on("mouseover", (function() { 
			var name = expression_names[i]; 
			var num_samples = gene_rpkms_array.length;
			return function(d) {
			    var e = Math.log(d)/Math.log(10); // convert to base 2
			    tooltip_div.transition()
				.duration(10)
				.style("opacity", 0.95);
			    tooltip_div.html("<b>"+name+"</b><br/>"+ num_samples + " samples <br/>" + e.toFixed(2) + " log<sub>10</sub>RPKM<br/>")
				.style("left", (d3.event.pageX - 50) + "px")
				.style("top", (d3.event.pageY - 60) + "px");
			};
		    })())
		.on("mouseout", function(d) {
			tooltip_div.transition()
			    .duration(500)
			    .style("opacity", 0);
		    });                
        }
    }
});


window.GeneErrorView = Backbone.View.extend({

    render: function() {
        $(this.el).html("<em>Gene not found</em>");
        return this;
    },

});
