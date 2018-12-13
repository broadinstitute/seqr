import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import hash from 'object-hash'

import { getProjectDetailsIsLoading } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import VariantSearchFormContent from './VariantSearchFormContent'
import { loadProjectFamiliesContext, loadSearchedVariants } from '../reducers'
import { getCoreQueryParams, getIntitialSearch } from '../selectors'


const VariantSearchForm = ({ initialSearch, queryParams, coreQueryParams, updateQueryParams, search, load, loading }) => {

  const onSubmit = (updatedSearchParams) => {
    const searchHash = hash.MD5(updatedSearchParams)
    search(searchHash, updatedSearchParams)
    updateQueryParams({ ...coreQueryParams, search: searchHash })
  }


  return (
    <DataLoader
      contentId={queryParams}
      loading={loading}
      load={load}
      // TODO should always be true once multi-project search is enabled
      content={initialSearch}
    >
      <ReduxFormWrapper
        initialValues={initialSearch}
        onSubmit={onSubmit}
        form="variantSearch"
        submitButtonText="Search"
        noModal
      >
        <VariantSearchFormContent />
      </ReduxFormWrapper>
    </DataLoader>
  )
}

VariantSearchForm.propTypes = {
  initialSearch: PropTypes.object,
  queryParams: PropTypes.object,
  coreQueryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
  search: PropTypes.func,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getIntitialSearch(state, ownProps),
  coreQueryParams: getCoreQueryParams(state, ownProps),
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProjectFamiliesContext,
  search: loadSearchedVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)
