import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Label } from 'semantic-ui-react'

import { CLINSIG_SEVERITY } from 'shared/utils/constants'
import { HorizontalSpacer } from '../../Spacers'
import VariantTags from './VariantTags'
import VariantLocations from './VariantLocations'
import Annotations from './Annotations'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGene from './VariantGene'
import VariantFamily from './VariantFamily'

const VariantRow = styled(Grid.Row)`
  .column {
    margin-top: 1em !important;
    margin-bottom: 0 !important;
  }
  
  padding: 0;
  color: #999;
  font-size: 12px;
  background-color: ${({ severity }) => {
    if (severity > 0) {
      return '#eaa8a857'
    } else if (severity === 0) {
      return '#f5d55c57'
    } else if (severity < 0) {
      return '#21a92624'
    }
    return 'inherit'
  }}
`

const CLINSIG_COLOR = {
  1: 'red',
  0: 'orange',
  [-1]: 'green',
}

const Variants = ({ variants }) =>
  <Grid divided="vertically" columns="equal">
    {variants.map(variant =>
      <VariantRow key={variant.variantId} severity={CLINSIG_SEVERITY[(variant.clinvar.clinsig || '').split('/')[0]]}>
        <Grid.Column width={16}>
          <VariantTags variant={variant} />
        </Grid.Column>
        <Grid.Column width={4}>
          {variant.clinvar.variantId &&
            <span>
              <b>ClinVar:</b>
              {variant.clinvar.clinsig.split('/').map(clinsig =>
                <a key={clinsig} target="_blank" href={`http://www.ncbi.nlm.nih.gov/clinvar/variation/${variant.clinvar.variantId}`}>
                  <HorizontalSpacer width={5} />
                  <Label color={CLINSIG_COLOR[CLINSIG_SEVERITY[clinsig]] || 'grey'} size="small" horizontal>{clinsig.replace(/_/g, ' ')}</Label>
                </a>,
              )}
            </span>
          }
        </Grid.Column>
        <Grid.Column width={12} textAlign="right">
          <VariantFamily variant={variant} />
        </Grid.Column>
        {variant.genes.length > 0 &&
          <Grid.Column>
            {variant.genes.map(gene => <VariantGene key={gene.geneId} gene={gene} />)}
          </Grid.Column>
        }
        <Grid.Column><VariantLocations variant={variant} /></Grid.Column>
        <Grid.Column><Annotations variant={variant} /></Grid.Column>
        <Grid.Column><Predictions annotation={variant.annotation} /></Grid.Column>
        <Grid.Column><Frequencies variant={variant} /></Grid.Column>
      </VariantRow>,
    )}
  </Grid>

Variants.propTypes = {
  variants: PropTypes.array,
}

export default Variants
