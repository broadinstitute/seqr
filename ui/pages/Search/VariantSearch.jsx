import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import hash from 'object-hash'

import { loadProject } from 'redux/rootReducer'
import { getProjectDetailsIsLoading, getProjectsByGuid } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'
import { loadSearchedVariants } from './reducers'
import { getSearchesByHash } from './selectors'


const BaseVariantSearch = ({ queryParams, updateQueryParams, searchParams, project, loading, load, search }) => {

  const onSubmit = (updatedSearchParams) => {
    const searchHash = hash.MD5(updatedSearchParams)
    search(searchHash, updatedSearchParams)
    updateQueryParams({ ...queryParams, search: searchHash })
  }

  return (
    <DataLoader contentId={(searchParams || queryParams).projectGuid} content={project} loading={loading} load={load}>
      <Grid>
        <Grid.Row>
          <Grid.Column width={16}>
            <ReduxFormWrapper
              initialValues={searchParams || queryParams}
              onSubmit={onSubmit}
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
  )
}

BaseVariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
  searchParams: PropTypes.object,
  project: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  search: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.queryParams.projectGuid],
  searchParams: getSearchesByHash(state)[ownProps.queryParams.search],
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProject,
  search: loadSearchedVariants,
}

const VariantSearch = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearch)

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
