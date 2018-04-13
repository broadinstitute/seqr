/* eslint-disable react/no-array-index-key */

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

export const FitContentColumn = styled(Grid.Column)`
  max-width: fit-content;
  padding-right: 0 !important;
  margin-bottom: 0 !important;  
`

const CLINSIG_COLOR = {
  pathogenic: 'red',
  'risk factor': 'orange',
  'likely pathogenic': 'red',
  benign: 'green',
  'likely benign': 'green',
  protective: 'green',
}

const TaggedByPopup = ({ trigger, tag }) =>
  <Popup
    position="top center"
    size="tiny"
    trigger={trigger}
    header="Tagged by"
    content={<span>{tag.user || 'unknown user'}{tag.date_saved && <br />}{tag.date_saved}</span>}
  />

TaggedByPopup.propTypes = {
  trigger: PropTypes.node,
  tag: PropTypes.object,
}


const Variants = ({ variants }) =>
  <Grid divided="vertically" columns="equal">
    {variants.map(variant =>
      <Grid.Row key={variant.variantId} style={{ padding: 0, color: '#999', fontSize: '12px' }}>
        {variant.extras && variant.extras.clinvar_variant_id &&
          <FitContentColumn>
            <b>ClinVar:</b>
            {variant.extras.clinvar_clinsig.split('/').map(clinsig =>
              <a key={clinsig} target="_blank" href={`http://www.ncbi.nlm.nih.gov/clinvar/variation/${variant.extras.clinvar_variant_id}`}>
                <HorizontalSpacer width={5} />
                <Label color={CLINSIG_COLOR[clinsig] || 'grey'} size="small">{clinsig}</Label>
              </a>,
            )}
          </FitContentColumn>
          }
        <FitContentColumn>
          <b>Tags:</b>
          {variant.tags.map(tag =>
            <span key={tag.name}>
              <HorizontalSpacer width={5} />
              <TaggedByPopup
                tag={tag}
                trigger={<Label size="small" style={{ color: 'white', backgroundColor: tag.color }}>{tag.name}</Label>}
              />
              {tag.search_parameters &&
                <a href={tag.search_parameters} target="_blank">
                  <HorizontalSpacer width={5} />
                  <Icon name="search" title="Re-run search" />
                </a>
              }
            </span>,
          )}
          <HorizontalSpacer width={5} />
          <a role="button"><Icon link name="write" /></a>
          {/*TODO edit actually works*/}
        </FitContentColumn>
        {/*TODO functional tags*/}
        <FitContentColumn>
          <b>Notes:</b>
          <HorizontalSpacer width={5} />
          {/*TODO add actually works*/}
          <a role="button"><Icon link name="plus" /></a>
        </FitContentColumn>
        <Grid.Column stretched style={{ marginBottom: 0 }}>
          {variant.notes.map((note, i) =>
            <span key={i}>
              {/*TODO edit actually works*/}
              <a role="button"><Icon link name="write" /></a>
              {/*TODO delete actually works*/}
              <a role="button"><Icon link name="trash" /></a>
              <HorizontalSpacer width={5} />
              <TaggedByPopup tag={note} trigger={<span>{note.note}</span>} />
              <HorizontalSpacer width={5} />
              {/*TODO submit_to_clinvar in note model*/}
              {note.submit_to_clinvar && <Label color="red" size="small">For Clinvar</Label>}
              <br />
            </span>,
          )}
        </Grid.Column>
        <Grid.Column width={16} style={{ marginTop: '1rem', marginBottom: 0 }}><VariantFamily variant={variant} /></Grid.Column>
        <Grid.Column width={3}><VariantLocations variant={variant} /></Grid.Column>
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
