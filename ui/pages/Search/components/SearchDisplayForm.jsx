import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { VARIANT_SEARCH_SORT_FIELD, VARIANT_PAGINATION_FIELD } from 'shared/utils/constants'
import FormWrapper from 'shared/components/form/FormWrapper'
import { loadSearchedVariants, updateSearchSort } from '../reducers'
import {
  getTotalVariantsCount,
  getVariantSearchDisplay,
} from '../selectors'

const FIELDS = [
  VARIANT_SEARCH_SORT_FIELD,
]

const SearchDisplayForm = React.memo(({
  variantSearchDisplay, onSubmit, totalVariantsCount, formLocation, paginationOnly,
}) => {
  const { recordsPerPage } = variantSearchDisplay
  const paginationFields = (totalVariantsCount || 0) > recordsPerPage ?
    [{ ...VARIANT_PAGINATION_FIELD, totalPages: Math.ceil(totalVariantsCount / recordsPerPage) }] : []
  const fields = paginationOnly ? paginationFields : [...FIELDS, ...paginationFields]

  return (
    <FormWrapper
      onSubmit={onSubmit}
      modalName={`editSearchedVariantsDisplay${formLocation || ''}`}
      initialValues={variantSearchDisplay}
      closeOnSuccess={false}
      submitOnChange
      inline
      fields={fields}
    />
  )
})

SearchDisplayForm.propTypes = {
  formLocation: PropTypes.string,
  paginationOnly: PropTypes.bool,
  onSubmit: PropTypes.func,
  variantSearchDisplay: PropTypes.object,
  totalVariantsCount: PropTypes.number,
}

const mapStateToProps = (state, ownProps) => ({
  variantSearchDisplay: getVariantSearchDisplay(state),
  totalVariantsCount: getTotalVariantsCount(state, ownProps),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: updates => (
    ownProps.searchOnSubmit ? dispatch(loadSearchedVariants(ownProps.match.params, {
      displayUpdates: updates,
      ...ownProps,
    })) : dispatch(updateSearchSort(updates))
  ),
})

export default connect(mapStateToProps, mapDispatchToProps)(SearchDisplayForm)
