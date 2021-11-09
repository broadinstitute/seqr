import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadSearchedVariants } from 'redux/rootReducer'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { InlineToggle } from 'shared/components/form/Inputs'
import StateChangeForm from 'shared/components/form/StateChangeForm'
import VariantSearchResults, { DisplayVariants } from 'shared/components/panel/search/VariantSearchResults'

import { updateCompoundHetDisplay, loadSingleSearchedVariant, loadProjectFamiliesContext } from '../reducers'
import { getFlattenCompoundHet, getSearchContextIsLoading, getInhertanceFilterMode } from '../selectors'
import { ALL_RECESSIVE_INHERITANCE_FILTERS } from '../constants'

const COMPOUND_HET_TOGGLE_FIELDS = [{
  name: 'flattenCompoundHet',
  component: InlineToggle,
  label: 'Unpair',
  labelHelp: 'Display individual variants instead of pairs for compound heterozygous mutations.',
}]
// TODO field
const compoundHetToggle = (flattenCompoundHet, toggleUnpair) => geneId => (
  <span>
    <StateChangeForm
      updateField={toggleUnpair}
      initialValues={flattenCompoundHet}
      fields={[{ ...COMPOUND_HET_TOGGLE_FIELDS[0], name: geneId }]} // eslint-disable-line
    />
    <HorizontalSpacer width={10} />
  </span>
)

const BaseVariantSearchResults = React.memo((
  { inheritanceFilter, toggleUnpair, flattenCompoundHet, match, initialLoad, ...props },
) => {
  const resultProps = {
    loadVariants: loadSearchedVariants,
    flattenCompoundHet,
  }

  const { variantId } = match.params
  if (variantId) {
    resultProps.loadVariants = loadSingleSearchedVariant
    resultProps.contentComponent = DisplayVariants
  } else {
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
  contextLoading: getSearchContextIsLoading(state),
  inheritanceFilter: getInhertanceFilterMode(state, ownProps),
  flattenCompoundHet: getFlattenCompoundHet(state),
})

const mapDispatchToProps = dispatch => ({
  toggleUnpair: geneId => (updates) => {
    dispatch(updateCompoundHetDisplay({
      [geneId]: updates,
    }))
  },
  initialLoad: (params) => {
    dispatch(loadProjectFamiliesContext(params))
  },
})

export default connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearchResults)
