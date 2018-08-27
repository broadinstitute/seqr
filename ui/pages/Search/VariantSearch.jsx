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


// TODO get rid of JSON encoding when using POST
const JSON_FILEDS = new Set(['freqs', 'qualityFilter', 'annotations'])
const parsedQueryParams = queryParams => Object.entries(queryParams).reduce(
  (acc, [key, val]) => ({ ...acc, [key]: JSON_FILEDS.has(key) ? JSON.parse(val) : val }), {},
)

const onSubmit = updateQueryParams => queryParams =>
  updateQueryParams(Object.entries(queryParams).reduce(
    (acc, [key, val]) => ({ ...acc, [key]: JSON_FILEDS.has(key) ? JSON.stringify(val) : val }), {},
  ))

const BaseVariantSearch = ({ queryParams, updateQueryParams, project, loading, load }) =>
  <DataLoader contentId={queryParams.projectGuid} content={project} loading={loading} load={load}>
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
  </DataLoader>

BaseVariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
  project: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.queryParams.projectGuid],
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProject,
}

const VariantSearch = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearch)

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
