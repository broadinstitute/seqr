import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'

const VariantSearchFormContainer = React.memo(({ history, saveSearch, resultsPath, children, ...formProps }) => {

  const search = (searchParams) => {
    saveSearch(searchParams, history.push, resultsPath)
  }

  return (
    <ReduxFormWrapper
      onSubmit={search}
      submitButtonText="Search"
      noModal
      {...formProps}
    >
      {children}
    </ReduxFormWrapper>
  )
})


VariantSearchFormContainer.propTypes = {
  children: PropTypes.node,
  history: PropTypes.object.isRequired,
  saveSearch: PropTypes.func,
  resultsPath: PropTypes.string,
}

const mapDispatchToProps = {
  saveSearch: navigateSavedHashedSearch,
}

export default connect(null, mapDispatchToProps)(VariantSearchFormContainer)
