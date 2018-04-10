import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'

const Variant = ({ variant }) =>
  <Grid.Row>
    {JSON.stringify(variant)}
  </Grid.Row>

Variant.propTypes = {
  variant: PropTypes.object,
}

export default Variant
