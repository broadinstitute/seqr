import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Grid, Icon, Popup } from 'semantic-ui-react'
import { NavLink } from 'react-router-dom'

import { CLINSIG_SEVERITY } from 'shared/utils/constants'
import VariantTags from './VariantTags'
import Annotations from './Annotations'
import Pathogenicity from './Pathogenicity'
import Predictions from './Predictions'
import Frequencies from './Frequencies'
import VariantGene from './VariantGene'
import VariantFamily from './VariantFamily'
import VariantIndividuals from './VariantIndividuals'


const VariantRow = styled(Grid.Row)`
  .column {
    margin-top: 1em !important;
    margin-bottom: 0 !important;
  }
  
  padding: 0;
  color: #999;
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

const VariantLinkContainer = styled.div`
  position: absolute;
  top: .5em;
  right: 1em;
`

const NO_DISPLAY = { display: 'none' }

const Variants = ({ variants, projectGuid }) =>
  <Grid divided="vertically" columns="equal">
    {variants.map(variant =>
      <VariantRow key={variant.variantId} severity={CLINSIG_SEVERITY[(variant.clinvar.clinsig || '').split('/')[0]]}>
        {projectGuid &&
          <VariantLinkContainer>
            <NavLink to={`/project/${projectGuid}/saved_variants/variant/${variant.variantId}`} activeStyle={NO_DISPLAY}>
              <Popup
                trigger={<Icon name="linkify" link />}
                content="Go to the page for this individual variant. Note: There is no additional information on this page, it is intended for sharing specific variants."
                position="right center"
                wide
              />
            </NavLink>
          </VariantLinkContainer>
        }
        <Grid.Column width={16}>
          <VariantFamily variant={variant} />
          <Pathogenicity variant={variant} />
        </Grid.Column>
        <Grid.Column width={16}>
          <VariantTags variant={variant} />
        </Grid.Column>
        <Grid.Column>
          {variant.genes.map(gene => <VariantGene key={gene.geneId} gene={gene} />)}
        </Grid.Column>
        <Grid.Column><Annotations variant={variant} /></Grid.Column>
        <Grid.Column><Predictions annotation={variant.annotation} /></Grid.Column>
        <Grid.Column><Frequencies variant={variant} /></Grid.Column>
        <Grid.Column width={16}>
          <VariantIndividuals variant={variant} />
        </Grid.Column>
      </VariantRow>,
    )}
  </Grid>

Variants.propTypes = {
  variants: PropTypes.array,
  projectGuid: PropTypes.string,
}

export default Variants
