import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'

import VariantFamily from './VariantFamily'

const Variants = ({ variants }) =>
  <Grid divided="vertically">
    {variants.map(variant =>
      <Grid.Row key={variant.variantId} style={{ padding: 0, color: '#999', fontSize: '12px' }}>
        <Grid.Column width={16}><VariantFamily variant={variant} /></Grid.Column>
      </Grid.Row>,
    )}
  </Grid>

Variants.propTypes = {
  variants: PropTypes.array,
}

export default Variants
