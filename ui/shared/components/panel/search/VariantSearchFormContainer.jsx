import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { getSearchedVariantsErrorMessage, getSearchedVariantsIsLoading } from 'redux/selectors'
import FormWrapper from 'shared/components/form/FormWrapper'
import { toUniqueCsvString } from 'shared/utils/stringUtils'

const VariantSearchFormContainer = React.memo((
  { history, onSubmit, resultsPath, loading, variantsLoading, children, ...formProps },
) => (
  <FormWrapper onSubmit={onSubmit} loading={loading || variantsLoading} submitButtonText="Search" noModal {...formProps}>
    {children}
  </FormWrapper>
))

VariantSearchFormContainer.propTypes = {
  children: PropTypes.node,
  history: PropTypes.object.isRequired,
  onSubmit: PropTypes.func,
  resultsPath: PropTypes.string,
  loading: PropTypes.bool,
  variantsLoading: PropTypes.bool,
}

const mapStateToProps = state => ({
  variantsLoading: getSearchedVariantsIsLoading(state),
  submissionError: getSearchedVariantsErrorMessage(state),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: ({ search, ...searchParams }) => {
    let restructuredSearch = search
    if (search?.locus) {
      const { rawItems } = search?.locus || ''
      const formattedRawItems = (rawItems && typeof rawItems === 'object') ? toUniqueCsvString(Object.values(rawItems)) : rawItems
      restructuredSearch = { ...search, locus: { ...search.locus, rawItems: formattedRawItems } }
    }
    dispatch(navigateSavedHashedSearch(
      { ...searchParams, search: restructuredSearch }, ownProps.history.push, ownProps.resultsPath,
    ))
  },
})

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchFormContainer)
