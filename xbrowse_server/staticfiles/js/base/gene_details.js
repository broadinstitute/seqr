window.GeneDetailsView = Backbone.View.extend({

    initialize: function() {
        this.gene = this.options.gene;
    },

    template: _.template($('#tpl-gene-modal-content').html()),

    render: function(width) {
        var that = this;
        $(this.el).html(this.template({
            gene: that.gene,
        }));
        this.drawExpressionDisplay(1100);
        return this;
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
        var min_exponent = -10;
        var max_exponent = 12;

        var x = d3.scale.linear().domain([min_exponent, max_exponent]).range([0, scatter_width]);
        var row_offset = function(i) { return i*row_height + 30 }

	// Define the div for the tooltip
	var tooltip_div = d3.select("body").append("div").attr("class", "d3-tooltip").style("opacity", 0);

        var xcoord = function(d) {
            var e = min_exponent;
            if (d>0) {
                e = Math.log(d)/Math.log(2); // convert to base 2
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
            .text("LOG 2 EXPRESSION")
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
            window.expr = this.gene.expression;
	    var gene_expression_data = vis.selectAll('circle[data-expression="' + slug + '"]').data(this.gene.expression[slug]);
            gene_expression_data.enter()
                .append('circle')
                .attr('data-expression', slug)
                .attr('r', 5)
                .attr('fill-opacity', .12)
                .attr('fill', function(d, j) { return colors(i); } )
                .attr('transform', function(d, j) { return "translate(" + xcoord(d) + "," + (row_offset(i) + 13) + ")"; })
		.on("mouseover", (function() { 
			var name = expression_names[i]; 
			var num_samples = gene_expression_data[0].length;
			return function(d) {
			    var e = Math.log(d)/Math.log(2); // convert to base 2
			    tooltip_div.transition()
				.duration(10)
				.style("opacity", 0.95);
			    tooltip_div.html("<b>"+name+"</b><br/>"+ num_samples + " samples <br/>" + e.toFixed(2) + " log<sub>2</sub>RPKM<br/>")
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


window.GeneModalView = Backbone.View.extend({

    initialize: function() {
        this.gene = {};
    },

    content_template: _.template($('#tpl-gene-modal-content').html()),

    template: _.template(
        $('#tpl-gene-modal').html()
    ),

    render: function(eventName) {

        var that = this;

        $(this.el).html(this.template({
            gene_id: this.options.gene_id,
        }));

        this.setLoading();

        $.get(URL_PREFIX + 'api/gene-info/' + this.options.gene_id, {},
            function(data) {
                if (data.found_gene == true) {
                    that.gene = data.gene;
                    that.setLoaded();
                } else {
                    that.gene = null;
                    that.setNotFound();
                }
            }
        );

        return this;
    },

    setLoading: function() {
        this.$('#modal-content-container').hide();
        this.$('#modal-loading').show();
    },

    setNotFound: function() {
        this.$('#modal-content-container').html("<em>Gene not found</em>");
        this.$('#modal-content-container').show();
        this.$('#modal-loading').hide();
    },

    setLoaded: function() {
        var that = this;
        var detailsView = new GeneDetailsView({gene: this.gene});

        this.$('#modal-content-container').html(detailsView.render($(that.el).width()).el);
        detailsView.resize();

        this.$('#modal-content-container').show();
        this.$('#modal-loading').hide();
    },

});
