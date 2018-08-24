import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'

// TODO get rid of JSON encoding when using POST
const JSON_FILEDS = new Set(['freqs', 'qualityFilter', 'annotations'])
const parsedQueryParams = queryParams => Object.entries(queryParams).reduce(
  (acc, [key, val]) => ({ ...acc, [key]: JSON_FILEDS.has(key) ? JSON.parse(val) : val }), {},
)

const onSubmit = updateQueryParams => queryParams =>
  updateQueryParams(Object.entries(queryParams).reduce(
    (acc, [key, val]) => ({ ...acc, [key]: JSON_FILEDS.has(key) ? JSON.stringify(val) : val }), {},
  ))

const VariantSearch = ({ queryParams, updateQueryParams }) =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={16}>
        <ReduxFormWrapper
          initialValues={parsedQueryParams(queryParams)}
          onSubmit={onSubmit(updateQueryParams)}
          form="variantSearch"
          submitButtonText="Search"
          noModal
          renderChildren={VariantSearchForm}
        />
      </Grid.Column>
    </Grid.Row>
    <VariantSearchResults search={queryParams} />
  </Grid>

VariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
}

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
