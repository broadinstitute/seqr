import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'

const VariantSearchFormContainer = React.memo(({ history, onSubmit, resultsPath, children, ...formProps }) => (
  <ReduxFormWrapper onSubmit={onSubmit} submitButtonText="Search" noModal {...formProps}>
    {children}
  </ReduxFormWrapper>
))

VariantSearchFormContainer.propTypes = {
  children: PropTypes.node,
  history: PropTypes.object.isRequired,
  onSubmit: PropTypes.func,
  resultsPath: PropTypes.string,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: (searchParams) => {
    dispatch(navigateSavedHashedSearch(searchParams, ownProps.history.push, ownProps.resultsPath))
  },
})

export default connect(null, mapDispatchToProps)(VariantSearchFormContainer)
