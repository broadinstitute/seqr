import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import hash from 'object-hash'

import { getFamiliesByGuid, getAnalysisGroupsByGuid, getProjectDetailsIsLoading } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'
import { loadProjectFamiliesContext, loadSearchedVariants } from './reducers'
import { getCurrentSearchParams } from './selectors'


const BaseVariantSearch = ({ queryParams, updateQueryParams, searchParams, search, load, loading, familiesByGuid, analysisGroupByGuid }) => {

  const { projectGuid, familyGuid, analysisGroupGuid, ...coreQueryParams } = queryParams

  const onSubmit = (updatedSearchParams) => {
    const searchHash = hash.MD5(updatedSearchParams)
    search(searchHash, updatedSearchParams)
    updateQueryParams({ ...coreQueryParams, search: searchHash })
  }

  // TODO initial project or analysisGroup
  let searchedProjectFamilies = []
  if (projectGuid) {
    searchedProjectFamilies = [{
      projectGuid,
      familyGuids: Object.values(familiesByGuid).filter(
        family => family.projectGuid === projectGuid).map(family => family.familyGuid),
    }]
  }
  else if (familyGuid) {
    searchedProjectFamilies = [{
      projectGuid: (familiesByGuid[familyGuid] || {}).projectGuid,
      familyGuids: [familyGuid],
    }]
  }
  else if (analysisGroupGuid) {
    searchedProjectFamilies = [{
      projectGuid: (analysisGroupByGuid[analysisGroupGuid] || {}).projectGuid,
      familyGuids: (analysisGroupByGuid[analysisGroupGuid] || {}).familyGuids,
    }]
  }
  const initialValues = { searchedProjectFamilies, ...(searchParams || coreQueryParams) }

  return (
    <DataLoader
      contentId={queryParams}
      loading={loading}
      load={load}
      // TODO should always be true once multi-project search is enabled
      content={coreQueryParams.search || projectGuid || familyGuid || analysisGroupGuid}
    >
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
  analysisGroupByGuid: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  searchParams: getCurrentSearchParams(state, ownProps),
  familiesByGuid: getFamiliesByGuid(state),
  analysisGroupByGuid: getAnalysisGroupsByGuid(state),
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProjectFamiliesContext,
  search: loadSearchedVariants,
}

const VariantSearch = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearch)

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
