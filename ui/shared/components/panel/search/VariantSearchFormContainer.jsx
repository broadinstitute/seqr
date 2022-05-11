import PropTypes from 'prop-types'
import React from 'react'
import { connect } from 'react-redux'
import createDecorator from 'final-form-calculate'
import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { getSearchedVariantsErrorMessage, getSearchedVariantsIsLoading } from 'redux/selectors'
import FormWrapper from 'shared/components/form/FormWrapper'
import { toUniqueCsvString } from 'shared/utils/stringUtils'
import { LOCUS_LIST_ITEMS_FIELD } from 'shared/utils/constants'

import { LOCUS_FIELD_NAME, PANEL_APP_FIELD_NAME } from './constants'

const DECORATORS = [
  createDecorator({
    field: `search.${LOCUS_FIELD_NAME}.${PANEL_APP_FIELD_NAME}`,
    updates: {
      [`search.${LOCUS_FIELD_NAME}.${LOCUS_LIST_ITEMS_FIELD.name}`]: locusValue => (
        locusValue && toUniqueCsvString(Object.values(locusValue))
      ),
    },
  }),
]

const VariantSearchFormContainer = React.memo((
  { history, onSubmit, resultsPath, loading, variantsLoading, children, ...formProps },
) => (
  <FormWrapper
    onSubmit={onSubmit}
    loading={loading || variantsLoading}
    submitButtonText="Search"
    noModal
    decorators={DECORATORS}
    {...formProps}
  >
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
  onSubmit: values => dispatch(navigateSavedHashedSearch(
    values, ownProps.history.push, ownProps.resultsPath,
  )),
})

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchFormContainer)
