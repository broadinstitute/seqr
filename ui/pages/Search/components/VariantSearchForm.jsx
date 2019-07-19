import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { getLocusListIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { SaveSearchButton } from './SavedSearch'
import VariantSearchFormContent from './VariantSearchFormContent'
import { SEARCH_FORM_NAME } from '../constants'
import { getIntitialSearch, getMultiProjectSearchContextIsLoading } from '../selectors'
import { loadProjectFamiliesContext } from '../reducers'


const VariantSearchForm = ({ match, history, saveSearch, load, initialSearch, loading, contentLoading }) => {

  const search = (searchParams) => {
    saveSearch(searchParams, history.push)
  }

  return (
    <DataLoader
      contentId={match.params}
      loading={loading}
      load={load}
      content={initialSearch}
      hideError
    >
      <ReduxFormWrapper
        initialValues={initialSearch}
        onSubmit={search}
        form={SEARCH_FORM_NAME}
        submitButtonText="Search"
        loading={contentLoading}
        noModal
      >
        <VariantSearchFormContent />
      </ReduxFormWrapper>
      <SaveSearchButton />
    </DataLoader>
  )
}


VariantSearchForm.propTypes = {
  match: PropTypes.object,
  history: PropTypes.object,
  initialSearch: PropTypes.object,
  saveSearch: PropTypes.func,
  load: PropTypes.func,
  loading: PropTypes.bool,
  contentLoading: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getIntitialSearch(state, ownProps),
  contentLoading: getLocusListIsLoading(state),
  loading: getMultiProjectSearchContextIsLoading(state),
})

const mapDispatchToProps = {
  saveSearch: navigateSavedHashedSearch,
  load: loadProjectFamiliesContext,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)
