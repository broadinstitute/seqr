import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadSearchedVariants } from 'redux/rootReducer'
import { InlineToggle } from 'shared/components/form/Inputs'
import { helpLabel, StyledForm } from 'shared/components/form/FormHelpers'
import VariantSearchResults from 'shared/components/panel/search/VariantSearchResults'

import { updateCompoundHetDisplay, loadSingleSearchedVariant, loadProjectFamiliesContext } from '../reducers'
import { getFlattenCompoundHet, getSearchContextIsLoading, getInhertanceFilterMode } from '../selectors'
import { ALL_RECESSIVE_INHERITANCE_FILTERS } from '../constants'

const compHetToggleLabel = helpLabel('Unpair', 'Display individual variants instead of pairs for compound heterozygous mutations')

const compoundHetToggle = (flattenCompoundHet, toggleUnpair) => geneId => (
  <StyledForm inline hasSubmitButton={false}>
    <InlineToggle
      name={geneId}
      value={flattenCompoundHet[geneId]}
      label={compHetToggleLabel}
      onChange={toggleUnpair(geneId)}
      padded
    />
  </StyledForm>
)

const BaseVariantSearchResults = React.memo((
  { inheritanceFilter, toggleUnpair, flattenCompoundHet, match, initialLoad, ...props },
) => {
  const resultProps = {}

  const { variantId } = match.params
  if (!variantId) {
    resultProps.initialLoad = initialLoad
  }

  if (ALL_RECESSIVE_INHERITANCE_FILTERS.includes(inheritanceFilter)) {
    const compoundHetToggleForm = compoundHetToggle(flattenCompoundHet, toggleUnpair)
    resultProps.additionalDisplayEdit = compoundHetToggleForm('all')
    resultProps.compoundHetToggle = compoundHetToggleForm
  }

  return <VariantSearchResults match={match} {...props} {...resultProps} />
})

BaseVariantSearchResults.propTypes = {
  match: PropTypes.object,
  contextLoading: PropTypes.bool,
  inheritanceFilter: PropTypes.string,
  flattenCompoundHet: PropTypes.bool,
  toggleUnpair: PropTypes.func,
  initialLoad: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  inheritanceFilter: getInhertanceFilterMode(state, ownProps),
  flattenCompoundHet: getFlattenCompoundHet(state),
})

const mapDispatchToProps = dispatch => ({
  toggleUnpair: geneId => (updates) => {
    dispatch(updateCompoundHetDisplay({ [geneId]: updates }))
  },
  initialLoad: (params) => {
    dispatch(loadProjectFamiliesContext(params))
  },
})

export default connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearchResults)
