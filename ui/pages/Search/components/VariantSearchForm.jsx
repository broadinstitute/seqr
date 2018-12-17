import React from 'react'
import hash from 'object-hash'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProjectDetailsIsLoading } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import VariantSearchFormContent from './VariantSearchFormContent'
import { SEARCH_FORM_NAME } from '../constants'
import { loadProjectFamiliesContext, saveHashedSearch } from '../reducers'
import { getLoadedIntitialSearch } from '../selectors'


const VariantSearchForm = ({ match, history, saveSearch, initialSearch, load, loading }) => {
  const search = (searchParams) => {
    const searchHash = hash.MD5(searchParams)
    saveSearch(searchHash, searchParams)
    history.push(`/variant_search/${searchHash}`)
  }

  return (
    <DataLoader
      contentId={match.params}
      loading={loading}
      load={load}
      hideError
      // TODO should always be true once multi-project search is enabled
      content={initialSearch}
    >
      <ReduxFormWrapper
        initialValues={initialSearch}
        onSubmit={search}
        form={SEARCH_FORM_NAME}
        submitButtonText="Search"
        noModal
      >
        <VariantSearchFormContent />
      </ReduxFormWrapper>
    </DataLoader>
  )
}


VariantSearchForm.propTypes = {
  match: PropTypes.object,
  history: PropTypes.object,
  initialSearch: PropTypes.object,
  saveSearch: PropTypes.func,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getLoadedIntitialSearch(state, ownProps),
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProjectFamiliesContext,
  saveSearch: saveHashedSearch,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)
