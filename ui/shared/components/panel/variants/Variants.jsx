import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Label, Popup, Icon } from 'semantic-ui-react'

import VariantLocations from './VariantLocations'
import Annotations from './Annotations'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantFamily from './VariantFamily'
import { HorizontalSpacer } from '../../Spacers'

export const BreakWord = styled.span`
  word-break: break-all;
`

const CLINSIG_COLOR = {
  pathogenic: 'red',
  'risk factor': 'orange',
  'likely pathogenic': 'red',
  benign: 'green',
  'likely benign': 'green',
  protective: 'green',
}


const Variants = ({ variants }) =>
  <Grid divided="vertically">
    {variants.map(variant =>
      <Grid.Row key={variant.variantId} style={{ padding: 0, color: '#999', fontSize: '12px' }}>
        <Grid.Column width={16} style={{ marginBottom: 0 }}>
          {variant.extras && variant.extras.clinvar_variant_id &&
            <span>
              <b>ClinVar:</b>
              {variant.extras.clinvar_clinsig.split('/').map(clinsig =>
                <a key={clinsig}target="_blank" href={`http://www.ncbi.nlm.nih.gov/clinvar/variation/${variant.extras.clinvar_variant_id}`}>
                  <HorizontalSpacer width={5} />
                  <Label color={CLINSIG_COLOR[clinsig] || 'grey'} size="small">{clinsig}</Label>
                </a>,
              )}
              <HorizontalSpacer width={20} />
            </span>
          }
          <b>Tags:</b>
          <HorizontalSpacer width={10} />
          {variant.tags.map(tag =>
            <span>
              <Popup
                position="top center"
                trigger={<Label size="small" style={{ color: 'white', backgroundColor: tag.color }}>{tag.name}</Label>}
                header="Tagged by"
                content={<span>{tag.user || 'unknown user'}{tag.date_saved && <br />}{tag.date_saved}</span>}
              />
              {tag.search_parameters &&
                <a href={tag.search_parameters} target="_blank">
                  <HorizontalSpacer width={5} />
                  <Icon name="search" title="Re-run search" />
                </a>
              }
              <HorizontalSpacer width={5} />
            </span>,
          )}
          <a role="button"><Icon link name="write" /></a>
          {/*TODO edit actually works*/}
          {/*TODO functional tags*/}
        </Grid.Column>
        <Grid.Column width={16} style={{ marginBottom: 0 }}><VariantFamily variant={variant} /></Grid.Column>
        <Grid.Column width={3} style={{ marginTop: '1rem' }}><VariantLocations variant={variant} /></Grid.Column>
        <Grid.Column width={3}><Annotations variant={variant} /></Grid.Column>
        <Grid.Column width={3}><Predictions annotation={variant.annotation} /></Grid.Column>
        <Grid.Column width={3}><Frequencies variant={variant} /></Grid.Column>
      </Grid.Row>,
    )}
  </Grid>

Variants.propTypes = {
  variants: PropTypes.array,
}

export default Variants

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
