import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'

import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'


const VariantSearch = ({ queryParams, updateQueryParams }) =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={16}>
        <VariantSearchForm queryParams={queryParams} updateQueryParams={updateQueryParams} />
      </Grid.Column>
    </Grid.Row>
    <VariantSearchResults queryParams={queryParams} updateQueryParams={updateQueryParams} />
  </Grid>

VariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
}

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
