import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'

import VariantTags from './VariantTags'
import VariantLocations from './VariantLocations'
import Annotations from './Annotations'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGene, { GeneLabel } from './VariantGene'
import VariantFamily from './VariantFamily'

export const BreakWord = styled.span`
  word-break: break-all;
`


const Variants = ({ variants }) =>
  <Grid divided="vertically" columns="equal">
    {variants.map(variant =>
      <Grid.Row key={variant.variantId} style={{ padding: 0, color: '#999', fontSize: '12px' }}>
        <Grid.Column width={16} style={{ marginTop: '1rem', marginBottom: 0 }}>
          <VariantTags variant={variant} />
        </Grid.Column>
        <Grid.Column width={16} style={{ marginTop: '1rem', marginBottom: 0 }}>
          <VariantFamily variant={variant} />
        </Grid.Column>
        {variant.genes.length > 0 &&
          <Grid.Column style={{ marginTop: '1rem' }}>
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
