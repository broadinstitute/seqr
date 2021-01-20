import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadSearchedVariants } from 'redux/rootReducer'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { InlineToggle } from 'shared/components/form/Inputs'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
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

const BaseVariantSearchResults = React.memo(({ inheritanceFilter, toggleUnpair, flattenCompoundHet, match, initialLoad, ...props }) => {
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
    const compoundHetDisplay = { flattenCompoundHet }
    resultProps.additionalDisplayEdit = (
      <span>
        <ReduxFormWrapper
          onSubmit={toggleUnpair}
          form="toggleUnpairCompoundHet"
          initialValues={compoundHetDisplay}
          closeOnSuccess={false}
          submitOnChange
          inline
          fields={COMPOUND_HET_TOGGLE_FIELDS}
        />
        <HorizontalSpacer width={10} />
      </span>
    )
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

const mapDispatchToProps = (dispatch) => {
  return {
    toggleUnpair: (updates) => {
      dispatch(updateCompoundHetDisplay({
        updates,
      }))
    },
    initialLoad: (params) => {
      dispatch(loadProjectFamiliesContext(params))
    },
  }
}


export default connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearchResults)
