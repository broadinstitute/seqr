import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { ButtonLink } from '../StyledComponents'

const SearchResultsLink = ({ buttonText = 'Gene Search', openSearchResults }) =>
  <ButtonLink content={buttonText} onClick={openSearchResults} />

SearchResultsLink.propTypes = {
  buttonText: PropTypes.string,
  openSearchResults: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    openSearchResults: () => {
      const search = {
        locus: { rawItems: ownProps.geneId, rawVariantItems: ownProps.variantId },
        ...(ownProps.initialSearch || {}),
      }
      const projectFamilies = ownProps.familyGuids ? [{ familyGuids: ownProps.familyGuids }] : ownProps.projectFamilies
      dispatch(navigateSavedHashedSearch(
        { allProjectFamilies: !projectFamilies, projectFamilies, search },
        resultsLink => window.open(resultsLink, '_blank')),
      )
    },
  }
}


export default connect(null, mapDispatchToProps)(SearchResultsLink)
