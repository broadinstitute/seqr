import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import hash from 'object-hash'

import { getFamiliesByGuid, getProjectDetailsIsLoading } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'
import { loadProjectFamiliesContext, loadSearchedVariants } from './reducers'
import { getCurrentSearchParams } from './selectors'


const BaseVariantSearch = ({ queryParams, updateQueryParams, searchParams, search, load, loading, familiesByGuid }) => {

  const { familyGuid, ...coreQueryParams } = queryParams

  const onSubmit = (updatedSearchParams) => {
    const searchHash = hash.MD5(updatedSearchParams)
    search(searchHash, updatedSearchParams)
    updateQueryParams({ ...coreQueryParams, search: searchHash })
  }

  // TODO initial project or analysisGroup
  let searchedProjectFamilies = []
  if (familyGuid) {
    searchedProjectFamilies = [{
      projectGuid: (familiesByGuid[familyGuid] || {}).projectGuid,
      familyGuids: [familyGuid],
    }]
  }
  const initialValues = { searchedProjectFamilies, ...(searchParams || coreQueryParams) }


  return (
    <DataLoader contentId={queryParams} loading={loading} load={load} content>
      <Grid>
        <Grid.Row>
          <Grid.Column width={16}>
            <ReduxFormWrapper
              initialValues={initialValues}
              onSubmit={onSubmit}
              form="variantSearch"
              submitButtonText="Search"
              noModal
            >
              <VariantSearchForm />
            </ReduxFormWrapper>
          </Grid.Column>
        </Grid.Row>
        <VariantSearchResults queryParams={coreQueryParams} updateQueryParams={updateQueryParams} />
      </Grid>
    </DataLoader>
  )
}

BaseVariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
  searchParams: PropTypes.object,
  search: PropTypes.func,
  loading: PropTypes.bool,
  load: PropTypes.func,
  familiesByGuid: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  searchParams: getCurrentSearchParams(state, ownProps),
  familiesByGuid: getFamiliesByGuid(state),
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProjectFamiliesContext,
  search: loadSearchedVariants,
}

const VariantSearch = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearch)

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
