import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProjectDetailsIsLoading } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import VariantSearchFormContent from './VariantSearchFormContent'
import { loadProjectFamiliesContext, searchVariants } from '../reducers'
import { getLoadedIntitialSearch } from '../selectors'


const VariantSearchForm = ({ initialSearch, queryParams, search, load, loading }) =>
  <DataLoader
    contentId={queryParams}
    loading={loading}
    load={load}
    hideError
    // TODO should always be true once multi-project search is enabled
    content={initialSearch}
  >
    <ReduxFormWrapper
      initialValues={initialSearch}
      onSubmit={search}
      form="variantSearch"
      submitButtonText="Search"
      noModal
    >
      <VariantSearchFormContent />
    </ReduxFormWrapper>
  </DataLoader>

VariantSearchForm.propTypes = {
  initialSearch: PropTypes.object,
  queryParams: PropTypes.object,
  search: PropTypes.func,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getLoadedIntitialSearch(state, ownProps),
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    load: (context) => {
      dispatch(loadProjectFamiliesContext(context))
    },
    search: (updates) => {
      dispatch(searchVariants({
        search: updates,
        displayUpdates: { page: 1 },
        updateQueryParams: ownProps.updateQueryParams,
      }))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)
