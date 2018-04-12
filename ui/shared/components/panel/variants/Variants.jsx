import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'

import VariantLocations from './VariantLocations'
import Annotations from './Annotations'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantFamily from './VariantFamily'

export const BreakWord = styled.span`
  word-break: break-all;
`

const Variants = ({ variants }) =>
  <Grid divided="vertically">
    {variants.map(variant =>
      <Grid.Row key={variant.variantId} style={{ padding: 0, color: '#999', fontSize: '12px' }}>
        <Grid.Column width={3}><VariantLocations variant={variant} /></Grid.Column>
        <Grid.Column width={3}><Annotations variant={variant} /></Grid.Column>
        <Grid.Column width={3}><Predictions annotation={variant.annotation} /></Grid.Column>
        <Grid.Column width={3}><Frequencies variant={variant} /></Grid.Column>
        <Grid.Column width={16} style={{ marginTop: 0 }}><VariantFamily variant={variant} /></Grid.Column>
      </Grid.Row>,
    )}
  </Grid>

Variants.propTypes = {
  variants: PropTypes.array,
}

export default Variants

// <div class="basicvariant">
//         <div class="highlight-msg">
//             <% console.log(variant); %>
//             <% if(variant.extras && variant.extras.clinvar_variant_id) { %>
//                 <div>
//                     This variant is <a target="_blank" href="http://www.ncbi.nlm.nih.gov/clinvar/variation/<%= variant.extras.clinvar_variant_id %>">in ClinVar</a> as
//                     <i style="font-weight:500">
//                         <% _.each(variant.extras.clinvar_clinsig.split(";"),
//                             function(clinsig) {
//                                 var color = utils.getClinvarClinsigColor(clinsig);
//                             %>
//                                 <i style="color:<%= color %>"><%= clinsig %></i>
//                             <% });
//                         %>
//                     </i>
//                 </div>
//             <% } %>
//             <% if (variant.extras && variant.extras.family_tags && variant.extras.family_tags.length > 0) { %>
//                 <div class="tags">
//                     <div class="greytext" style="vertical-align:top; margin-right:50px"><b>Tags: </b></div><span style="display:inline-block">
//                     <% _.each(variant.extras.family_tags, function(tag) { %>
//                         <% if(show_tag_details) { %>
//                             <span class="label" style="background-color:<%= tag.color %>; margin-left:10px;"><%= tag.tag %></span>
//                             <i>
//                                 tagged by
//                                 <% if(tag.user) { %>
//                                     <%= tag.user.display_name %>
//                                 <% } else { %>
//                                     unknown user
//                                 <% } %>
//                                 <% if(tag.date_saved) { %> (<%= tag.date_saved %>) <% } %>
//                             </i>
//                             <% if(tag.search_url) { %>
//                                 <a style="margin-left:10px" href="<%= tag.search_url %>">
//                                     <i class="fa fa-search" aria-hidden="true"></i>
//                                 </a>
//                                 <a href="<%= tag.search_url %>">re-run variant search</a>
//                 <% } %>
//                 <br />
//                  <% } else { %>
//                         <span class="label" style="background-color:<%= tag.color %>;"><%= tag.tag %></span>
//                     <% } %>
//               <% }); %>
//               </span>
//                 </div>
//             <% } %>
//             <% if (allow_functional && variant.extras.family_functional_data.length > 0) { %>
//                 <div class="tags functional-data">
//                     <div class="greytext" style="vertical-align:top; margin-right:50px"><b>Fxnl: </b></div><span style="display:inline-block">
//                     <% _.each(variant.extras.family_functional_data, function(tag) { %>
//                         <% if(show_tag_details) { %>
//                             <span class="label" style="background-color:<%= tag.tag_config.color %>; margin-left:10px;"><%= tag.tag %></span>
//                             <% if(tag.metadata) { %>
//                                 <b>&nbsp<%= tag.tag_config.metadata_title %>: <%= tag.metadata %>&nbsp</b>
//                             <% } %>
//                             <i>
//                                 tagged by
//                                 <% if(tag.user) { %>
//                                     <%= tag.user.display_name %>
//                                 <% } else { %>
//                                     unknown user
//                                 <% } %>
//                                 <% if(tag.date_saved) { %> (<%= tag.date_saved %>) <% } %>
//                             </i>
//                             <% if(tag.search_url) { %>
//                                 <a style="margin-left:10px" href="<%= tag.search_url %>">
//                                     <i class="fa fa-search" aria-hidden="true"></i>
//                                 </a>
//                                 <a href="<%= tag.search_url %>">re-run variant search</a>
//                 <% } %>
//                 <br />
//                       <% } else { %>
//                           <span class="label" style="background-color:<%= tag.tag_config.color %>;"><%= tag.tag %></span>
//                       <% } %>
//               <% }); %>
//               </span>
//                 </div>
//             <% } %>
//             <%  if (variant.extras && variant.extras.family_notes && variant.extras.family_notes.length > 0) { %>
//                 <div class="notes">
//                     <div class="greytext"><b>Notes: </b></div>
//                     <span style="display:inline-block">
//                         <% for(var i = variant.extras.family_notes.length - 1; i >= 0; i--) {
//                             var family_note = variant.extras.family_notes[i];
//                             %>
//                             <%= family_note.note %>
//                             <i>by
//                                 <% if(family_note.user) { %>
//                                     <%= family_note.user.display_name %>
//                                 <% } else { %>
//                                     unknown user
//                                 <% } %>
//                                 <% if(family_note.submit_to_clinvar) { %>
//                                     <span style="color:red"> for clinvar </span>
//                                 <% } %>
//                                 <% if(family_note.date_saved) { %>
//                                     (<%= family_note.date_saved %>)
//                                 <% } %>
//                             </i>
//         "click a.edit-variant-note": "edit_variant_note",
//                             <a class="edit-variant-note" data-target="<%= family_note.note_id %>"><i class="fa fa-pencil" aria-hidden="true"></i></a>
//         "click a.delete-variant-note": "delete_variant_note",
//                             <a class="delete-variant-note" data-target="<%= family_note.note_id %>"><i class="fa fa-trash-o"  aria-hidden="true"></i></a>
//                             <br />
//                         <% } %>
//                     </span>
//                 </div>
//
//             <% } %>
//         </div>

//
//         <div class="cell icons" style="display:none;">
//             <% if (variant.extras.disease_genes && variant.extras.disease_genes.length > 0 ) { %>
//                 <i class="fa fa-warning icon-popover"
//                     title="Gene List"
//                     data-content="<% _.each(variant.extras.disease_genes, function (a) { %><%= a %><% }); %>"></i>
//             <% } %>
//             <% if (variant.extras.in_disease_gene_db) { %>
//                 <i class="fa fa-plus icon-popover"
//                     title="Present in Disease Database"
//                     data-content="This variant is in a gene that has been linked to a disease phenotype.
//                     Click the gene for more info. "></i>
//             <% } %>
//             <% if (variant.extras.family_notes && variant.extras.family_notes.length > 0 ) { %>
//                 <i class="fa fa-bookmark search-flag-icon"
//                    data-xpos="<%= variant.xpos %>"
//                    data-ref="<%= variant.ref %>"
//                    data-alt="<%= variant.alt %>"></i>
//             <% } %>
//         </div>
//
//         <% if (show_gene) {  %>
//             <div class="cell genes">
//                 <% _.each(variant.extras.genes, function(gene, gene_id) { %>
//                     <div class="gene-cell">
//  "click a.gene-link": "gene_info",
//                         <a class="gene-link" data-gene_id="<%= gene_id %>"><%= gene.symbol || variant.extras.gene_names[gene_id] %></a><br/>
//                         <sub>
//                             <a href="http://www.gtexportal.org/home/gene/<%= gene.symbol %>" target="_blank">GTEx</a><br />
//                             <a href="http://gnomad-beta.broadinstitute.org/gene/<%= gene.symbol %>" target="_blank">gnomAD</a><br />
//                             <% if(show_gene_search_link && project_id) { %>
//                                 <a href="/project/<%= project_id %>/gene/<%= gene_id %>" target="_blank">Gene Search</a><br/>
//                             <% } %>
//                         </sub>
//                         <div class="highlights">
//                             <% if (gene.missense_constraint && gene.missense_constraint_rank[0] < 1000) { %>
//                                 <span class="label label-default" style='display:inline'>MISSENSE CONSTR
//                                     <i class="icon-question-sign icon-popover"
//                                        title="Missense Constraint"
//                                        data-placement="right"
//                                        data-content="This gene ranks <%= gene.missense_constraint_rank[0] %> most constrained out of <%= gene.missense_constraint_rank[1] %> genes under study in terms of missense constraint (z-score: <%= gene.missense_constraint.toPrecision(4) %>). Missense contraint is a measure of the degree to which the number of missense variants found in this gene in ExAC v0.3 is higher or lower than expected according to the statistical model described in [K. Samocha 2014]. In general this metric is most useful for genes that act via a dominant mechanism, and where a large proportion of the protein is heavily functionally constrained.">
//                                     </i>
//                                 </span>
//                                 <br />
//                             <% } %>
//                             <% if (gene.lof_constraint && gene.lof_constraint_rank[0] < 1000) { %>
//                                 <span class="label label-default">
//                                     LOF CONSTR
//                                     <i class="icon-question-sign icon-popover"
//                                        title="Loss of Function Constraint"
//                                        data-placement="right"
//                                        data-content="This gene ranks as <%= gene.lof_constraint_rank[0] %> most intolerant of LoF mutations out of <%= gene.lof_constraint_rank[1] %> genes under study. This metric is based on the amount of expected variation observed in the ExAC data and is a measure of how likely the gene is to be intolerant of loss-of-function mutations."></i>
//                                 </span><br/>
//                             <% } %>
//                         </div>
//                     </div>
//                 <% }); %>
//                 <% if (variant.extras.in_disease_gene_db) { %>
//                 <span class="label label-default">IN OMIM</span><br/>
//                 <% } %>
//                 <% if (variant.extras.disease_genes && variant.extras.disease_genes.length > 0 ) { %>
//                     <% _.each(variant.extras.disease_genes, function (gene_list_name) { %>
//                         <span class="label label-danger icon-popover"
//                               title="Gene List"
//                               data-content="<%= gene_list_name %>">
//                             GENE LIST: <%= gene_list_name.substring(0,6) %> <%= gene_list_name.length > 6 ? '..' : '' %>
//                         </span><br/>
//                     <% }); %>
//                 <% } %>
//             </div>
//         <% } %>
//


//                         <% if(genotype && genotype.extras && genotype.extras.cnvs)  {
//                             var cnvs = genotype.extras.cnvs;
//                         %>
//                             <span class="label label-danger gotooltip"
//                                     data-placement="top"
//                                     title="Copy Number: <%= cnvs['cn'] %><br>LRR median: <%= cnvs['LRR_median'] %><br>LRR stdev: <%= cnvs['LRR_sd'] %><br>SNPs supporting call: <%= cnvs['snps'] %><br>Size: <%= cnvs['size'] %><br>Found in: <% print(parseInt(cnvs['freq'])-1) %> other samples<br>Type: <%= cnvs['type'] %><br>Array: <%= cnvs['array'].replace(/_/g, ' ') %><br>Caller: <%= cnvs['caller'] %><br>">
//                                 CNV: <%= cnvs['cn'] > 2 ? 'Duplication' : 'Deletion' %>
//                             </span><br>
//                         <% } %>

//         <% if (actions.length > 0) { %>
//             <div class="cell actions" style="text-align:right">
//                 <% _.each(actions, function(action) { %>
//                      "click a.action": "action",
//                     <a class="btn btn-primary btn-xs action" data-action="<%= action.action %>"> <%= action.name %></a><br/>
//                 <% }); %>
//             </div>
//         <% } %>
//     </div>
