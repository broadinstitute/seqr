$(document).ready(
		function() {
			var by_exon_template = _
					.template($('#tpl-coverage-by-exon').html());
			var coverage_cell_template = _.template($(
					'#tpl-single-exon-coverage').html());

			$('#coverage-by-exon-container').html(by_exon_template({
				indiv_ids : INDIV_IDS,
				coverages : COVERAGES,
				coding_regions : CODING_REGIONS,
				coverage_cell_template : coverage_cell_template,
			}));

			// var by_transcript_template =
			// _.template($('#tpl-coverage-by-transcript').html());
			// $('#coverage-by-transcript-container').html(by_transcript_template({
			// by_transcript: BY_TRANSCRIPT,
			// indiv_ids: INDIV_IDS,
			// coverage_cell_template: single_exon_template,
			// }));

			var by_individual_template = _.template($(
					'#tpl-coverage-by-individual').html());
			$('#coverage-by-individual-container').html(
					by_individual_template({
						coverages : COVERAGES,
						indiv_ids : INDIV_IDS,
						coverage_cell_template : coverage_cell_template,
					}));

			// var coding_exons_labels = [
			// 'Low Coverage
			// ('+Math.round(WHOLE_GENE_CODING.ratio_low_coverage*100)+'%)',
			// 'Poor Mapping
			// ('+Math.round(WHOLE_GENE_CODING.ratio_poor_mapping*100)+'%)',
			// 'Callable
			// ('+Math.round(WHOLE_GENE_CODING.ratio_callable*100)+'%)',
			// ];
			// var coding_exons_vals = [WHOLE_GENE.low_coverage,
			// WHOLE_GENE.poor_mapping, WHOLE_GENE.callable];
			// var coding_exons_pie = new RGraph.Pie('coding-exons-canvas',
			// coding_exons_vals)
			// .Set('key', coding_exons_labels)
			// .Set('key.position.x', 0)
			// .Set('radius', 60)
			// .Set('title', 'Coding Regions')
			// .Set('centery', 150)
			// .Draw();

			var whole_gene_labels = [
					'Low Coverage ('
							+ Math.round(WHOLE_GENE.ratio_low_coverage * 100)
							+ '%)',
					'Poor Mapping ('
							+ Math.round(WHOLE_GENE.ratio_poor_mapping * 100)
							+ '%)',
					'Callable (' + Math.round(WHOLE_GENE.ratio_callable * 100)
							+ '%)', ];
			var whole_gene_vals = [ WHOLE_GENE.low_coverage,
					WHOLE_GENE.poor_mapping, WHOLE_GENE.callable ];
			var all_exons_pie = new RGraph.Pie('all-exons-canvas',
					whole_gene_vals).Set('key', whole_gene_labels).Set(
					'chart.colors',
					[ 'rgba(255, 0, 0, 1.0)', 'rgba(230, 230, 230, 1.0)',
							'rgba(0, 255, 0, 1.0)' ]).Set('key.shadow', false)
					.Set('chart.radius', 75).Set('chart.centerx', 200).Set(
							'chart.centery', 85)
					.Set('chart.key.position.x', 10).Set(
							'chart.key.position.y', 10).Set('chart.shadow',
							false).Draw();

			$('.gopopover').popover({
				container : 'body',
				trigger : 'hover',
			});

		});