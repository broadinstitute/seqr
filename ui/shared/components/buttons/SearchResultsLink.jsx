import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { VEP_GROUP_SV } from 'shared/utils/constants'
import { ButtonLink } from '../StyledComponents'

const SearchResultsLink = ({ buttonText = 'Gene Search', openSearchResults, padding }) =>
  <ButtonLink content={buttonText} onClick={openSearchResults} padding={padding} />

SearchResultsLink.propTypes = {
  buttonText: PropTypes.string,
  padding: PropTypes.string,
  openSearchResults: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    openSearchResults: () => {
      const search = {
        ...(ownProps.initialSearch || {}),
        locus: { rawItems: ownProps.location, rawVariantItems: ownProps.variantId, genomeVersion: ownProps.genomeVersion },
      }
      if (ownProps.svType) {
        search.annotations = { [VEP_GROUP_SV]: [ownProps.svType] }
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
