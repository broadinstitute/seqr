import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { getLocusListIsLoading } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { SaveSearchButton } from './SavedSearch'
import VariantSearchFormContent from './VariantSearchFormContent'
import { SEARCH_FORM_NAME } from '../constants'
import { getIntitialSearch } from '../selectors'


const VariantSearchForm = ({ history, saveSearch, initialSearch, contentLoading }) => {

  const search = (searchParams) => {
    saveSearch(searchParams, history.push)
  }

  return (
    <div>
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
    </div>
  )
}


VariantSearchForm.propTypes = {
  history: PropTypes.object,
  initialSearch: PropTypes.object,
  saveSearch: PropTypes.func,
  contentLoading: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getIntitialSearch(state, ownProps),
  contentLoading: getLocusListIsLoading(state),
})

const mapDispatchToProps = {
  saveSearch: navigateSavedHashedSearch,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)
