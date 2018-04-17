/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Label, Popup, Icon } from 'semantic-ui-react'

import VariantLocations from './VariantLocations'
import Annotations from './Annotations'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGene, { GeneLabel } from './VariantGene'
import VariantFamily from './VariantFamily'
import { HorizontalSpacer } from '../../Spacers'

export const BreakWord = styled.span`
  word-break: break-all;
`

export const FitContentColumn = styled(Grid.Column)`
  max-width: fit-content;
  min-width: fit-content;
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

const taggedByPopupContent = tag =>
  <span>{tag.user || 'unknown user'}{tag.date_saved && <br />}{tag.date_saved}</span>

const reRunSearchLink = (tag) => {
  return tag.search_parameters ? (
    <a href={tag.search_parameters} target="_blank">
      <HorizontalSpacer width={5} />
      <Icon name="search" title="Re-run search" />
    </a>) : null
}

const EditableTags = ({ tags, popupContent, tagAnnotation }) =>
  <span>
    {tags.map(tag =>
      <span key={tag.name}>
        <HorizontalSpacer width={5} />
        <Popup
          position="top center"
          size="tiny"
          trigger={<Label size="small" style={{ color: 'white', backgroundColor: tag.color }} horizontal>{tag.name}</Label>}
          header="Tagged by"
          content={popupContent(tag)}
        />
        {tagAnnotation && tagAnnotation(tag)}
      </span>,
    )}
    <HorizontalSpacer width={5} />
    <a role="button"><Icon link name="write" /></a>
    {/*TODO edit actually works*/}
  </span>

EditableTags.propTypes = {
  tags: PropTypes.array,
  popupContent: PropTypes.func,
  tagAnnotation: PropTypes.func,
}


const Variants = ({ variants }) =>
  <Grid divided="vertically" columns="equal">
    {variants.map(variant =>
      <Grid.Row key={variant.variantId} style={{ padding: 0, color: '#999', fontSize: '12px' }}>
        {variant.clinvar.variantId &&
          <FitContentColumn>
            <b>ClinVar:</b>
            {variant.clinvar.clinsig.split('/').map(clinsig =>
              <a key={clinsig} target="_blank" href={`http://www.ncbi.nlm.nih.gov/clinvar/variation/${variant.clinvar.variantId}`}>
                <HorizontalSpacer width={5} />
                <Label color={CLINSIG_COLOR[clinsig] || 'grey'} size="small" horizontal>{clinsig}</Label>
              </a>,
            )}
          </FitContentColumn>
          }
        <FitContentColumn>
          <b>Tags:</b>
          <EditableTags tags={variant.tags} popupContent={taggedByPopupContent} tagAnnotation={reRunSearchLink} />
        </FitContentColumn>
        {variant.tags.some(tag => tag.category === 'CMG Discovery Tags') &&
          <FitContentColumn>
            <b>Fxnl Data:</b>
            <EditableTags tags={variant.functionalData} popupContent={taggedByPopupContent} tagAnnotation={reRunSearchLink} />
          </FitContentColumn>
        }
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
              <Popup
                position="top center"
                size="tiny"
                trigger={<span>{note.note}</span>}
                header="Written by"
                content={taggedByPopupContent(note)}
              />
              <HorizontalSpacer width={5} />
              {/*TODO submit_to_clinvar in note model*/}
              {note.submit_to_clinvar && <Label color="red" size="small" horizontal>For Clinvar</Label>}
              <br />
            </span>,
          )}
        </Grid.Column>
        <Grid.Column width={16} style={{ marginTop: '1rem', marginBottom: 0 }}>
          <VariantFamily variant={variant} />
        </Grid.Column>
        {variant.genes.length > 0 &&
          <Grid.Column>
            {variant.genes.map(gene => <VariantGene key={gene.geneId} gene={gene} />)}
            {variant.inDiseaseGeneDb && <GeneLabel color="orange" label="IN OMIM" />}
            {variant.diseaseGeneLists.map(geneListName =>
              <GeneLabel
                key={geneListName}
                label={`${geneListName.substring(0, 10)}${geneListName.length > 6 ? ' ..' : ''}`}
                color="teal"
                popupHeader="Gene List"
                popupContent={geneListName}
              />,
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
