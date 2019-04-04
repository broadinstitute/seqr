import React from 'react'
import hash from 'object-hash'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getLocusListIsLoading } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { SaveSearchButton } from './SavedSearch'
import VariantSearchFormContent from './VariantSearchFormContent'
import { SEARCH_FORM_NAME } from '../constants'
import { saveHashedSearch } from '../reducers'
import { getIntitialSearch } from '../selectors'


const VariantSearchForm = ({ history, saveSearch, initialSearch, contentLoading }) => {
  const search = (searchParams) => {
    const searchHash = hash.MD5(searchParams)
    saveSearch(searchHash, searchParams)
    history.push(`/variant_search/results/${searchHash}`)
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
  saveSearch: saveHashedSearch,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)
