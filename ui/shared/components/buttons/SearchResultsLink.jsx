import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { ButtonLink } from '../StyledComponents'

const SearchResultsLink = ({ openSearchResults }) =>
  <ButtonLink content="Gene Search" onClick={openSearchResults} />

SearchResultsLink.propTypes = {
  openSearchResults: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    openSearchResults: () => {
      dispatch(navigateSavedHashedSearch(
        { projectFamilies: [{ familyGuids: ownProps.familyGuids }], search: { locus: { rawItems: ownProps.geneId } } },
        resultsLink => window.open(resultsLink, '_blank')),
      )
    },
  }
}


export default connect(null, mapDispatchToProps)(SearchResultsLink)
