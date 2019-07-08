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
      dispatch(navigateSavedHashedSearch(
        {
          projectFamilies: ownProps.projectFamilies || [{ familyGuids: ownProps.familyGuids }],
          search: { locus: { rawItems: ownProps.geneId }, ...(ownProps.initialSearch || {}) },
        },
        resultsLink => window.open(resultsLink, '_blank')),
      )
    },
  }
}


export default connect(null, mapDispatchToProps)(SearchResultsLink)
