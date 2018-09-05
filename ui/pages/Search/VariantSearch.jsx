import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'

import { loadProject } from 'redux/rootReducer'
import { getProjectDetailsIsLoading, getProjectsByGuid } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'
import { loadSearchedVariants } from './reducers'


// TODO get rid of JSON encoding when using POST
const JSON_FILEDS = new Set(['freqs', 'qualityFilter', 'annotations', 'locus', 'inheritance'])
const parsedQueryParams = queryParams => Object.entries(queryParams).reduce(
  (acc, [key, val]) => ({ ...acc, [key]: JSON_FILEDS.has(key) ? JSON.parse(val) : val }), {},
)

const onSubmit = (updateQueryParams, search) => (queryParams) => {
  const searchParams = {
    search: true,
    ...Object.entries(queryParams).reduce(
      (acc, [key, val]) => ({ ...acc, [key]: JSON_FILEDS.has(key) ? JSON.stringify(val) : val }), {},
    ),
  }
  search(searchParams)
  updateQueryParams(searchParams)
}

const BaseVariantSearch = ({ queryParams, updateQueryParams, project, loading, load, search }) =>
  <DataLoader contentId={queryParams.projectGuid} content={project} loading={loading} load={load}>
    <Grid>
      <Grid.Row>
        <Grid.Column width={16}>
          <ReduxFormWrapper
            initialValues={parsedQueryParams(queryParams)}
            onSubmit={onSubmit(updateQueryParams, search)}
            form="variantSearch"
            submitButtonText="Search"
            noModal
            renderChildren={VariantSearchForm}
          />
        </Grid.Column>
      </Grid.Row>
      <VariantSearchResults search={queryParams} />
    </Grid>
  </DataLoader>

BaseVariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
  project: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  search: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.queryParams.projectGuid],
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProject,
  search: loadSearchedVariants,
}

const VariantSearch = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearch)

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
