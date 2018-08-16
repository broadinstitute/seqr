import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'

import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchResults from './VariantSearchResults'

const VariantSearch = ({ queryParams }) =>
  <Grid>
    <VariantSearchResults search={queryParams} />
  </Grid>

VariantSearch.propTypes = {
  queryParams: PropTypes.object,
}

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
