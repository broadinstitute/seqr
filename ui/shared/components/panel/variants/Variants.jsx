/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Label, Popup, Icon } from 'semantic-ui-react'

import VariantLocations from './VariantLocations'
import Annotations from './Annotations'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGene from './VariantGene'
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
                <Label color={CLINSIG_COLOR[clinsig] || 'grey'} size="small" horizontal>{clinsig}</Label>
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
                trigger={<Label size="small" style={{ color: 'white', backgroundColor: tag.color }} horizontal>{tag.name}</Label>}
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
              {note.submit_to_clinvar && <Label color="red" size="small" horizontal>For Clinvar</Label>}
              <br />
            </span>,
          )}
        </Grid.Column>
        <Grid.Column width={16} style={{ marginTop: '1rem', marginBottom: 0 }}><VariantFamily variant={variant} /></Grid.Column>
        {variant.extras && variant.extras.genes &&
          <Grid.Column>
            {Object.keys(variant.extras.genes).map(geneId =>
              <VariantGene key={geneId} geneId={geneId} gene={variant.extras.genes[geneId] || {}} variant={variant} />,
            )}
          </Grid.Column>
        }
        <Grid.Column style={{ marginTop: '1rem' }}><VariantLocations variant={variant} /></Grid.Column>
        <Grid.Column><Annotations variant={variant} /></Grid.Column>
        <Grid.Column><Predictions annotation={variant.annotation} /></Grid.Column>
        <Grid.Column><Frequencies variant={variant} /></Grid.Column>
      </Grid.Row>,
    )}
  </Grid>

Variants.propTypes = {
  variants: PropTypes.array,
}

export default Variants
