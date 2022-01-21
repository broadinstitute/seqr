import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { navigateSavedHashedSearch } from 'redux/rootReducer'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { toUniqueCsvString } from 'shared/utils/stringUtils'

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
  onSubmit: ({ search, ...searchParams }) => {
    let restructuredSearchParams = searchParams
    if (search?.locus) {
      const { rawItems } = search?.locus || ''
      const formattedRawItems = (rawItems && typeof rawItems === 'object') ? toUniqueCsvString(Object.values(rawItems)) : rawItems
      restructuredSearchParams = {
        ...searchParams,
        search: { ...search, locus: { ...search.locus, rawItems: formattedRawItems } },
      }
    }
    dispatch(navigateSavedHashedSearch(restructuredSearchParams, ownProps.history.push, ownProps.resultsPath))
  },
})

export default connect(null, mapDispatchToProps)(VariantSearchFormContainer)
